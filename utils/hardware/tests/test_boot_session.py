import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import boot_session as boot


class BootSessionTests(unittest.TestCase):
    def test_warm_power_guard_accepts_observed_ldo_and_preserves_unrelated_bits(self):
        safety = {0x58024804: 0xe000, 0x5802480c: 0x05000042,
                  0x58024818: 0xe000, 0x52002000: 0x35}
        boot.validate_warm_power(safety)
        vos3 = safety | {0x58024804: 0x6000, 0x58024818: 0x6000, 0x52002000: 0x37}
        boot.validate_warm_power(vos3)
        for address, value in [(0x5802480c, 0x05000046), (0x5802480c, 0x05000041),
                               (0x58024804, 0xc000), (0x58024818, 0xa000),
                               (0x52002000, 0x31), (0x52002000, 0x38)]:
            with self.assertRaises(ValueError): boot.validate_warm_power(safety | {address: value})

    def test_voltage_recovery_requires_hsi_and_waits_for_actual_original_voltage(self):
        saved = {0x58024804: 0x6000, 0x5802480c: 0x05000042,
                 0x58024818: 0x6000, 0x52002000: 0x37}
        mem = saved | {0x58024804: 0xe000, 0x58024818: 0xe000,
                       0x58024400: 5, 0x58024410: 0}
        writes = []
        def write(a, v):
            writes.append((a, v)); mem[a] = v
            if a == 0x58024818: mem[0x58024804] = v
        boot.restore_power(mem.__getitem__, write, saved)
        self.assertEqual({a: mem[a] for a in saved}, saved)
        self.assertEqual(writes, [(0x58024818, 0x6000)])
        for address, value in [(0x58024410, 0x1b), (0x58024400, 0x3030005),
                               (0x5802480c, 0x05000041), (0x52002000, 0x36)]:
            mem[address] = value
            with self.assertRaises(RuntimeError): boot.restore_power(mem.__getitem__, write, saved)
            mem[address] = saved.get(address, 5 if address == 0x58024400 else 0)
        mem[0x58024804] = 0xe000
        with self.assertRaises(RuntimeError): boot.restore_power(mem.__getitem__, lambda a,v: None, saved, budget=2)

    def test_mailbox_requires_two_fault_free_advancing_snapshots(self):
        words = [0x4e445631, 8, 3, 0, 0x411fc271, 0x20036450,
                 0x03030005, 0x1b, 0x48, 0, 0, 10, 100, 0, 0, 0, 0, 0, 0, 15] + [0]*12
        first = boot.decode(struct.pack('<32I', *words))
        words[11:13] = [20, 200]
        second = boot.decode(struct.pack('<32I', *words))
        self.assertTrue(boot.is_live(second, first))
        self.assertFalse(boot.is_live(first, first))
        for field, value in [('version', 5), ('cfsr', 1), ('state', 5),
                             ('error', 256), ('power_status', 7), ('rcc_cfgr', 0),
                             ('ram_words', 512), ('cpuid', 0), ('mpu_ctrl', 1)]:
            altered = dict(second, **{field: value})
            self.assertFalse(boot.is_live(altered, first), field)
        words[1] = 5
        with self.assertRaises(ValueError): boot.decode(struct.pack('<32I', *words))

    def test_qspi_result_requires_success_and_exact_backup_prefix(self):
        header = bytes(range(64))
        data = struct.pack('<2I', 0, 0xef4018) + header
        self.assertEqual(boot.decode_qspi(data, header)['jedec_id'], '0xef4018')
        for bad in [struct.pack('<2I', 1, 0xef4018)+header,
                    struct.pack('<2I', 0, 0xffffff)+header, data[:-1], data[:-1]+b'X']:
            with self.assertRaises(ValueError): boot.decode_qspi(bad, header)

    def test_recovery_stops_faulted_qspi_and_restores_only_pg6_latch(self):
        mem = {boot.AHB3: 0x1000, boot.AHB4: 0x81, boot.RST: 0,
               boot.GODR: 0x8001, boot.QCR: 0, boot.QDCR: 0, boot.QCCR: 0, boot.QSR: 0}
        writes = []
        def read(a): return mem[a]
        def write(a, v):
            writes.append((a, v))
            if a == boot.GBSRR:
                mem[boot.GODR] = (mem[boot.GODR] | (v & 0xffff)) & ~(v >> 16)
            else: mem[a] = v
            if a == boot.RST and v & 0x4000:
                for r in (boot.QCR, boot.QDCR, boot.QCCR, boot.QSR): mem[r] = 0
        saved = boot.capture(read, write)
        self.assertEqual(mem[boot.AHB4], 0x81)
        mem.update({boot.AHB3: 0x5000, boot.AHB4: 0xe1, boot.GODR: 0x8043,
                    boot.QCR: 1, boot.QDCR: 0x170300, boot.QCCR: 0x5002503, boot.QSR: 0x20})
        boot.restore(read, write, saved)
        self.assertEqual(mem[boot.AHB3], 0x1000)
        self.assertEqual(mem[boot.GODR], 0x8003)  # retain unrelated changed bit 1
        self.assertEqual(mem[boot.AHB4], 0xe1)  # caller restores GPIO configuration next
        self.assertTrue(any(a == boot.RST and v & 0x4000 for a, v in writes))
        self.assertFalse(any(a in (boot.QCCR, boot.QCR) for a, _ in writes))

    def test_capture_refuses_active_qspi_and_failed_cleanup_forbids_resume(self):
        for active in (boot.AHB3, boot.RST):
            mem = {boot.AHB3: 0, boot.AHB4: 0x81, boot.RST: 0, boot.GODR: 0}
            mem[active] = 0x4000
            writes = []
            with self.assertRaises(RuntimeError): boot.capture(mem.__getitem__, lambda a,v: writes.append((a,v)))
            self.assertEqual(writes, [])
        mem = {boot.AHB3: 0, boot.AHB4: 0x81, boot.RST: 0, boot.GODR: 0}
        def stuck_write(a, v):
            if v != 0x81: mem[a] = v
        with self.assertRaises(boot.CaptureRecoveryError): boot.capture(mem.__getitem__, stuck_write)
        saved = {boot.AHB3: 0, boot.RST: 0, boot.GODR: 0}
        mem[boot.AHB4] = 0x81
        with self.assertRaises(RuntimeError): boot.restore(mem.__getitem__, lambda a,v: None, saved)


if __name__ == '__main__': unittest.main()

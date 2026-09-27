"""Run the real power driver with MMIO at the hardware boundary replaced.

Catches unrelated-pin damage, a low output glitch during mode changes, a missing
clock readback, incorrect active-low input, and reporting latch high as pin high.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class Tx15PowerTests(unittest.TestCase):
    def test_init_preserves_other_pins_and_preloads_high_before_output(self):
        native = Path(tempfile.gettempdir()) / "new-deviation-ucrt64/bin"
        compiler = os.environ.get("PROBE_HOST_CC", str(native / "gcc.exe"))
        with tempfile.TemporaryDirectory(prefix="tx15-power-") as tmp:
            source = Path(tmp) / "power_test.c"
            source.write_text(r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
static uint32_t a[8], h[8], clocks;
static int clock_readback;
static uint32_t rd(uint32_t address) {
    if (address == 0x580244e0u) { clock_readback = 1; return clocks; }
    assert((clocks & 0x81u) == 0x81u && clock_readback);
    if (address >= 0x58020000u && address < 0x58020020u) return a[(address-0x58020000u)/4];
    assert(address >= 0x58021c00u && address < 0x58021c20u);
    return h[(address-0x58021c00u)/4];
}
static void wr(uint32_t address, uint32_t value) {
    if (address == 0x580244e0u) { clocks=value; clock_readback=0; return; }
    assert((clocks & 0x81u) == 0x81u && clock_readback);
    if (address == 0x58021c18u) {
        assert(value == 0x1000u); /* no reset bits or unrelated output */
        h[5] |= value;
    } else if (address >= 0x58021c00u && address <= 0x58021c0cu) {
        if (address == 0x58021c00u && ((value >> 24) & 3u) == 1u)
            assert(h[5] & 0x1000u); /* latch must be high before output mode */
        h[(address-0x58021c00u)/4]=value;
    } else {
        assert(address == 0x58020000u || address == 0x5802000cu);
        a[(address-0x58020000u)/4]=value;
    }
}
#define TX15_READ32(address) rd(address)
#define TX15_WRITE32(address, value) wr(address, value)
#include "hardware/tx15/board/power.c"
int main(void) {
    const uint32_t patterns[] = {0, 0xaaaaaaaau, 0xffffffffu};
    for (unsigned p=0; p<3; ++p) {
        uint32_t old_a[8], old_h[8];
        for (unsigned i=0; i<8; ++i) a[i]=h[i]=patterns[p];
        h[5] &= ~0x1000u;
        memcpy(old_a,a,sizeof(a)); memcpy(old_h,h,sizeof(h));
        clocks=0x1100067eu; clock_readback=0;
        tx15_power_init();
        assert(clocks == 0x110006ffu);
        assert(h[0] == ((old_h[0] & ~0x03000000u) | 0x01000000u));
        assert(h[1] == (old_h[1] & ~0x1000u));
        assert(h[2] == (old_h[2] & ~0x03000000u));
        assert(h[3] == (old_h[3] & ~0x03000000u));
        assert(h[5] == (old_h[5] | 0x1000u));
        assert(a[0] == (old_a[0] & ~0x300u));
        assert(a[3] == ((old_a[3] & ~0x300u) | 0x100u));
        assert(a[1] == old_a[1] && a[2] == old_a[2] && a[5] == old_a[5]);
        h[4]=0x1000u; a[4]=0x10u;
        assert(tx15_power_status() == 0x0fu);
        a[4]=0;
        assert(tx15_power_status() == 0x1fu);
        h[4]=0;
        assert((tx15_power_status() & 4u) == 0); /* actual pad, not just ODR */
        h[4]=0x1000u; a[4]=0x10u;
        uint32_t mode=h[0]; h[0] &= ~0x03000000u;
        assert((tx15_power_status() & 1u) == 0); h[0]=mode;
        h[1] |= 0x1000u;
        assert((tx15_power_status() & 1u) == 0); h[1] &= ~0x1000u;
        h[5] &= ~0x1000u;
        assert((tx15_power_status() & 2u) == 0); h[5] |= 0x1000u;
        a[0] |= 0x100u;
        assert((tx15_power_status() & 8u) == 0); a[0] &= ~0x300u;
        a[3] &= ~0x300u;
        assert((tx15_power_status() & 8u) == 0); a[3] |= 0x100u;
        clocks &= ~1u;
        assert(tx15_power_status() == 0); clocks |= 1u;
        clocks &= ~0x80u;
        assert(tx15_power_status() == 0); /* do not read unclocked GPIO */
    }
    return 0;
}
''', encoding="ascii")
            exe = Path(tmp) / "power_test.exe"
            env = os.environ.copy()
            env["PATH"] = str(native) + os.pathsep + env["PATH"]
            result = subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                                     "-isystem", str(native.parent / "include"), "-I.",
                                     str(source), "-o", str(exe)],
                                    cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

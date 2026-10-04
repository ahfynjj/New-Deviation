import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import display_diagnostics as d

class DisplayDiagnosticTests(unittest.TestCase):
    def test_backlight_trial_preserves_other_pins_and_restores_timer_clock(self):
        regs={d.DHCSR:1<<17,d.APB2:0x100,d.RST2:0,d.AMODE:0xabdc7cff,
              d.AAFRH:0x000aa000,d.CR:0x33030005,d.CFGR:0x1b,d.D1:0x48,d.D2:0x440,
              d.PLLSEL:0x00c000c2,d.PLLCFG:0x01010808,d.PLLDIV:0x23f}
        regs.update({a:0 for a in d.TIMER_REGS})
        original=dict(regs);writes=[]
        def write(a,v):
            writes.append((a,v));regs[a]=v
            if a==d.RST2 and v&1:
                for t in d.TIMER_REGS:regs[t]=0
        trial=d.BacklightTrial(regs.__getitem__,write)
        trial.enter()
        self.assertEqual((regs[d.AMODE]>>20)&3,2)
        self.assertEqual((regs[d.AAFRH]>>8)&15,1)
        self.assertEqual(regs[d.TIM1+0x28],639)
        self.assertEqual(regs[d.TIM1+0x2c],100)
        self.assertEqual(regs[d.TIM1+0x3c],13)
        self.assertEqual(regs[d.TIM1+0x20],0x100)
        self.assertEqual(regs[d.TIM1+0x44],0x8000)
        self.assertEqual(regs[d.AMODE]&~(3<<20),original[d.AMODE]&~(3<<20))
        trial.exit()
        self.assertTrue(trial.restored)
        for a in (d.APB2,d.RST2,d.AMODE,d.AAFRH)+d.TIMER_REGS:
            self.assertEqual(regs[a],original[a])
        self.assertTrue(all(a in d.BACKLIGHT_WRITES for a,v in writes))
        regs[d.APB2]|=1
        with self.assertRaises(RuntimeError):d.BacklightTrial(regs.__getitem__,write).enter()

    def test_failed_overlay_recovery_keeps_cpu_halted(self):
        from unittest.mock import Mock
        regs=self.registers();regs[d.DHCSR]=0;clock=[0.0];writes=[]
        overlay=Mock();overlay.exit.side_effect=RuntimeError('Recovery failed')
        with self.assertRaises(RuntimeError):
            d.observe(regs.__getitem__,lambda a,v:writes.append((a,v)),lambda:None,
                      lambda n:clock.__setitem__(0,clock[0]+n),lambda:clock[0],
                      durations=(1,1,1),overlay=overlay)
        self.assertEqual(writes,[(d.DHCSR,0xa05f0003)])

    def test_overlay_touches_only_eight_framebuffer_rows_and_restores_readback(self):
        from unittest.mock import Mock
        ap=Mock();ap.read32.side_effect=lambda a:(1<<17) if a==d.DHCSR else d.OVERLAY_START
        class Dp:
            def __init__(self):self.address=0;self.memory=bytearray(b'Z'*7680);self.writes=[]
            def read_ap(self,a):return 0x12
            def write_ap(self,a,v):self.address=v
            def write_ap_multiple(self,a,values):
                raw=struct.pack('<%dI'%len(values),*values);off=self.address-d.OVERLAY_START
                self.assert_range(off,len(raw));self.writes.append((self.address,len(raw)))
                self.memory[off:off+len(raw)]=raw
            def assert_range(self,off,n):
                if not 0<=off or off+n>7680:raise AssertionError('Outside overlay')
            def read_ap_multiple(self,a,n):
                off=self.address-d.OVERLAY_START;self.assert_range(off,n*4)
                return struct.unpack('<%dI'%n,self.memory[off:off+n*4])
            def flush(self):pass
        dp=Dp();overlay=d.FrameOverlay(ap,dp)
        overlay.enter();self.assertEqual(dp.memory,b'\0\xf8'*3840)
        overlay.exit();self.assertEqual(dp.memory,b'Z'*7680)
        self.assertTrue(all(a>=d.OVERLAY_START and a+n<=d.OVERLAY_START+7680 for a,n in dp.writes))
        ap.read32.side_effect=lambda a:0
        with self.assertRaises(RuntimeError):overlay.enter()

    def test_slow_sample_never_requests_negative_sleep(self):
        regs=self.registers();regs[d.DHCSR]=0;clock=[0.0]
        def read(a):
            if a==d.CPSR:clock[0]+=2
            return regs[a]
        def sleep(n):self.assertGreaterEqual(n,0);clock[0]+=n
        d.observe(read,lambda *_:None,lambda:None,sleep,lambda:clock[0],durations=(1,1,1))

    def test_pause_is_bounded_and_only_debug_run_state_is_written(self):
        regs=self.registers();regs[d.DHCSR]=0;clock=[0.0];writes=[]
        def write(a,v):writes.append((a,v))
        rows=d.observe(regs.__getitem__,write,lambda:None,lambda n:clock.__setitem__(0,clock[0]+n),
                       lambda:clock[0],durations=(1,1,1))
        self.assertEqual([r['phase'] for r in rows],['running','paused','resumed'])
        self.assertEqual(writes,[(d.DHCSR,0xa05f0003),(d.DHCSR,0xa05f0001)])
        self.assertEqual(clock[0],3)

    def test_sample_failure_during_pause_still_resumes_same_cpu_context(self):
        regs=self.registers();regs[d.DHCSR]=0;clock=[0.0];writes=[]
        def write(a,v):
            writes.append((a,v))
            if v==0xa05f0003:regs[d.APB3]=0
        with self.assertRaises(ValueError):
            d.observe(regs.__getitem__,write,lambda:None,lambda n:clock.__setitem__(0,clock[0]+n),
                      lambda:clock[0],durations=(1,1,1))
        self.assertEqual(writes[-1],(d.DHCSR,0xa05f0001))

    def registers(self):
        return {d.AHB4:1,d.APB3:8,d.AMODE:1<<20,d.AODR:1<<10,d.AIDR:1<<10,
                d.ISR:0x9,d.CPSR:(73<<16)|244,d.CDSR:3,d.GCR:0x10012221,
                d.TWCR:0x018101f5,d.FB:0xd0000000,d.PITCH:(640<<16)|647,d.LINES:480}

    def test_read_only_snapshot_retains_flags_and_backlight_levels(self):
        regs=self.registers();accesses=[]
        def read(a):accesses.append(a);return regs[a]
        r=d.sample(read)
        self.assertEqual(r['position'],[73,244])
        self.assertTrue(r['backlight_output_high']);self.assertTrue(r['backlight_input_high'])
        self.assertEqual(r['backlight_mode'],1)
        self.assertFalse(r['fifo_underrun']);self.assertFalse(r['transfer_error'])
        self.assertAlmostEqual(r['nominal_refresh_hz'],10666666.6667/(386*502),places=5)
        self.assertNotIn(0x5000103c,accesses) # never read/write interrupt-clear register
        regs[d.ISR]=0x6;regs[d.AIDR]=0
        r=d.sample(regs.__getitem__)
        self.assertTrue(r['fifo_underrun']);self.assertTrue(r['transfer_error'])
        self.assertFalse(r['backlight_input_high'])

    def test_unclocked_reads_refused_and_summary_does_not_claim_absence_of_flicker(self):
        regs=self.registers();regs[d.APB3]=0
        with self.assertRaises(ValueError):d.sample(regs.__getitem__)
        rows=[{'phase':'running','sample':dict(position=[1,2],backlight_output_high=True,
            backlight_input_high=True,backlight_mode=1,fifo_underrun=False,transfer_error=False)},
              {'phase':'paused','sample':dict(position=[3,4],backlight_output_high=True,
            backlight_input_high=True,backlight_mode=1,fifo_underrun=True,transfer_error=False)}]
        r=d.summarize(rows)
        self.assertTrue(r['scan_position_changed']);self.assertTrue(r['sampled_backlight_high'])
        self.assertTrue(r['fifo_underrun_latched']);self.assertFalse(r['transfer_error_latched'])
        self.assertTrue(r['visual_confirmation_required'])
        self.assertFalse(d.summarize([])['sampled_backlight_high'])

if __name__=='__main__':unittest.main()

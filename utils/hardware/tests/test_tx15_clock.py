"""Exercise the native clock driver against delayed/failing RCC hardware."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class Tx15ClockTests(unittest.TestCase):
    def test_switch_order_timeouts_and_reset_guards(self):
        self.assertTrue((ROOT / 'hardware/tx15/board/clock.c').exists())
        native = Path(tempfile.gettempdir()) / 'new-deviation-ucrt64/bin'
        with tempfile.TemporaryDirectory(prefix='tx15-clock-') as tmp:
            source = Path(tmp) / 'clock_test.c'
            source.write_text(r'''
#include <assert.h>
#include <stdint.h>
static uint32_t cr, cfgr, d1;
static unsigned reads, writes, ready_reads, switch_reads;
static int fail_ready, fail_switch;
static uint32_t rd(uint32_t a) {
    assert(++reads < 1000); /* all failure paths must be bounded */
    if (a == 0x58024400u) {
        if ((cr & 0x10000u) && !fail_ready && ++ready_reads >= 3) cr |= 0x20000u;
        return cr;
    }
    if (a == 0x58024410u) {
        if ((cfgr & 7u) == 2 && !fail_switch && ++switch_reads >= 3)
            cfgr = (cfgr & ~0x38u) | 0x10u;
        return cfgr;
    }
    assert(a == 0x58024418u); return d1;
}
static void wr(uint32_t a, uint32_t v) {
    ++writes;
    if (a == 0x58024400u) {
        assert((v ^ cr) == 0x10000u); /* only enable HSE; keep HSI */
        cr=v; return;
    }
    assert(a == 0x58024410u && (cr & 0x20000u));
    assert(((v ^ cfgr) & ~7u) == 0 && (v & 7u) == 2);
    cfgr=v;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#include "hardware/tx15/board/clock.c"
static void reset(void) {
    cr=0x4025; cfgr=0x8000; d1=0;
    reads=writes=ready_reads=switch_reads=0; fail_ready=fail_switch=0;
}
int main(void) {
    reset(); assert(tx15_clock_hse_init(8) == TX15_CLOCK_OK);
    assert(cr == 0x34025 && cfgr == 0x8012 && writes == 2);
    assert(TX15_CORE_HZ == 48000000u);
    reset(); fail_ready=1;
    assert(tx15_clock_hse_init(8) == TX15_CLOCK_HSE_TIMEOUT);
    assert(writes == 1 && (cfgr & 0x3f) == 0 && (cr & 5) == 5);
    reset(); fail_switch=1;
    assert(tx15_clock_hse_init(8) == TX15_CLOCK_SWITCH_TIMEOUT);
    assert(writes == 2 && (cr & 5) == 5);
    const uint32_t bad_cr[] = {0x4021, 0x402d, 0x14025, 0x24025, 0x44025,
                               0x84025, 0x1004025, 0x4004025, 0x10004025};
    for (unsigned i=0; i<sizeof(bad_cr)/sizeof(*bad_cr); ++i) {
        reset(); cr=bad_cr[i]; assert(tx15_clock_hse_init(8) == TX15_CLOCK_BAD_STATE);
        assert(writes == 0);
    }
    reset(); cfgr |= 8; assert(tx15_clock_hse_init(8) == TX15_CLOCK_BAD_STATE); assert(!writes);
    reset(); d1=8; assert(tx15_clock_hse_init(8) == TX15_CLOCK_BAD_STATE); assert(!writes);
    reset(); assert(tx15_clock_hse_init(0) == TX15_CLOCK_BAD_STATE); assert(!writes);
}
''', encoding='ascii')
            env = os.environ.copy()
            env['PATH'] = str(native) + os.pathsep + env['PATH']
            exe = Path(tmp) / 'clock_test.exe'
            result = subprocess.run([os.environ.get('PROBE_HOST_CC', str(native / 'gcc.exe')),
                '-std=c11', '-Wall', '-Wextra', '-Werror', '-isystem', str(native.parent / 'include'),
                '-I.', str(source), '-o', str(exe)], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

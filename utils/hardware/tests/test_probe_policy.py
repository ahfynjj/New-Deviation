"""Exercise the exact C precondition policy used by the real MCU image."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class ProbePolicyTests(unittest.TestCase):
    def test_rejects_wrong_clock_core_cache_and_mpu(self):
        native = Path(tempfile.gettempdir()) / "new-deviation-ucrt64/bin"
        compiler = os.environ.get("PROBE_HOST_CC", str(native / "gcc.exe"))
        with tempfile.TemporaryDirectory(prefix="tx15-probe-policy-") as tmp:
            source = Path(tmp) / "policy.c"
            source.write_text('''#include <assert.h>
#include "probe.h"
int main(void) {
    struct probe_report good = {0}, r;
    good.cpuid = 0x411fc271u; good.device_id = 0x20036450u; good.rcc_cr = 5;
    assert(probe_environment_error(&good) == 0);
    r = good; r.cpuid = 0x410fc241u;
    assert(probe_environment_error(&r) == BAD_CORE);
    r = good; r.device_id = 0x413;
    assert(probe_environment_error(&r) == BAD_DEVICE);
    r = good; r.rcc_cr |= 8;
    assert(probe_environment_error(&r) == BAD_CLOCK);
    r = good; r.rcc_cr &= ~4u;
    assert(probe_environment_error(&r) == BAD_CLOCK);
    r = good; r.rcc_cfgr = 0x1b;
    assert(probe_environment_error(&r) == BAD_CLOCK);
    r = good; r.rcc_d1cfgr = 0x800;
    assert(probe_environment_error(&r) == BAD_CLOCK);
    r = good; r.rcc_d1cfgr = 8;
    assert(probe_environment_error(&r) == BAD_CLOCK);
    r = good; r.scb_ccr = 1u << 16;
    assert(probe_environment_error(&r) == BAD_CPU_STATE);
    r = good; r.scb_ccr = 1u << 17;
    assert(probe_environment_error(&r) == BAD_CPU_STATE);
    r = good; r.mpu_ctrl = 1;
    assert(probe_environment_error(&r) == BAD_CPU_STATE);
    return 0;
}
''', encoding="ascii")
            exe = Path(tmp) / "policy.exe"
            env = os.environ.copy()
            env["PATH"] = str(native) + os.pathsep + env["PATH"]
            result = subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                                     "-isystem", str(native.parent / "include"),
                                     "-Ihardware/tx15/ram_probe", str(source), "-o", str(exe)],
                                    cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

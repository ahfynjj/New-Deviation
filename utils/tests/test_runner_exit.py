#!/usr/bin/env python3
"""Compile the real generated CuTest runner and verify its process exit status.

Run from a POSIX build shell: python3 utils/tests/test_runner_exit.py
The destructor shim invalidates the failure count deterministically, as a
released/reused suite allocation may do. All test execution uses real CuTest.
"""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CUTEST = ROOT / "src/target/tx/other/test"


class RunnerExitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="deviation-runner-")
        cls.work = Path(cls.scratch.name)
        (cls.work / "tests").mkdir()
        fixture = cls.work / "tests/fixture.c"
        fixture.write_text('''#include <stdlib.h>
#include "CuTest.h"

void TestFixture(CuTest *tc)
{
    CuAssertTrue(tc, getenv("RUNNER_FORCE_FAILURE") == NULL);
}

/* Keep the allocation valid so a post-destruction read has a deterministic
 * value, rather than relying on a particular allocator's use-after-free. */
void regression_delete(CuSuite *suite)
{
    suite->failCount = 0;
}
''')
        generated = subprocess.run(
            ["sh", str(CUTEST / "make-tests.sh")], cwd=cls.work,
            check=True, capture_output=True, text=True)
        runner = cls.work / "runner.c"
        runner.write_text(generated.stdout)
        cc = os.environ.get("CC", "gcc")
        subprocess.run([
            cc, "-I", str(CUTEST), '-DFILESYSTEM_DIR="."',
            "-DCuSuiteDelete=regression_delete", "-c", str(runner),
            "-o", str(cls.work / "runner.o")], check=True)
        cls.exe = cls.work / "runner.exe"
        subprocess.run([
            cc, "-I", str(CUTEST), str(cls.work / "runner.o"),
            str(CUTEST / "CuTest.c"), str(fixture), "-lm",
            "-o", str(cls.exe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def run_fixture(self, fail):
        env = os.environ.copy()
        env.pop("RUNNER_FORCE_FAILURE", None)
        if fail:
            env["RUNNER_FORCE_FAILURE"] = "1"
        return subprocess.run([str(self.exe)], cwd=self.work, env=env,
                              capture_output=True, text=True)

    def test_passing_suite_exits_zero(self):
        result = self.run_fixture(False)
        self.assertIn("OK (1 test)", result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_failing_suite_exits_one_after_cleanup(self):
        result = self.run_fixture(True)
        self.assertIn("!!!FAILURES!!!", result.stdout)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

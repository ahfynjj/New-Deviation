#!/usr/bin/env python3
"""Exercise the linter against real temporary Git repositories."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "run_linter.py"
spec = importlib.util.spec_from_file_location("deviation_linter", SCRIPT)
linter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linter)


class LinterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="deviation-lint-")
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.env = os.environ.copy()
        for name in ("TRAVIS", "TRAVIS_PULL_REQUEST", "GITHUB_TOKEN", "DEVIATION_LINT_BASE"):
            self.env.pop(name, None)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, env=self.env,
                              check=True, capture_output=True, text=True)

    def init_repo(self, branch):
        self.git("init", "-b", branch)
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        sample = self.repo / "sample.c"
        sample.write_text("// fixture\nint sample = 1;\n// end\n")
        self.git("add", "sample.c")
        self.git("commit", "-m", "baseline")
        self.git("switch", "-c", "work")
        sample.write_text("// fixture\nint sample = 2;  \n// end\n")

    def run_linter(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--diff", "--skip-github", *args],
                              cwd=self.repo, env=self.env, capture_output=True, text=True)

    def test_main_branch_reports_violation(self):
        self.init_repo("main")
        result = self.run_linter()
        self.assertIn("whitespace/end_of_line", result.stdout)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_master_branch_reports_violation(self):
        self.init_repo("master")
        result = self.run_linter()
        self.assertIn("whitespace/end_of_line", result.stdout)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_no_fail_preserves_diagnostics(self):
        self.init_repo("main")
        result = self.run_linter("--no-fail")
        self.assertIn("whitespace/end_of_line", result.stdout)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_base(self):
        self.init_repo("baseline")
        self.env["DEVIATION_LINT_BASE"] = "baseline"
        result = self.run_linter()
        self.assertIn("whitespace/end_of_line", result.stdout)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_single_line_hunk(self):
        diff = ["diff --git a/sample.c b/sample.c", "@@ -1 +1 @@", "-old", "+new"]
        self.assertEqual(linter.get_changed_lines_from_diff(diff), {"sample.c": {1: 1}})

    def test_missing_python_module_fails(self):
        self.init_repo("master")
        self.env["PYTHONPATH"] = str(self.repo / "missing-packages")
        result = self.run_linter()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("cpplint", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "check_string_size.py"
spec = importlib.util.spec_from_file_location("check_string_size", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class LanguageTargetTests(unittest.TestCase):
    def test_host_only_target_has_language(self):
        previous = os.getcwd()
        with tempfile.TemporaryDirectory(prefix="deviation-language-") as tmp:
            target = Path(tmp) / "target/tx/radiomaster/emu_tx15"
            target.mkdir(parents=True)
            (target / "Makefile.inc").write_text("LANGUAGE := devo8\n")
            try:
                os.chdir(tmp)
                self.assertEqual(checker.get_language("tx15"), "devo8")
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()

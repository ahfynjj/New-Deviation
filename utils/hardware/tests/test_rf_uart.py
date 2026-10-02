"""Native USART6 discovery driver tests using a register model."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[3]

class RfUartTests(unittest.TestCase):
    def test_register_order_interrupts_and_bounds(self):
        gcc = Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp)/'rf.exe'
            env = dict(os.environ, PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
            p = subprocess.run([str(gcc), '-std=c99', '-Wall', '-Wextra', '-Werror',
                '-I', str(ROOT.parent/'tools/msys64/ucrt64/include'), '-I', str(ROOT),
                str(ROOT/'utils/hardware/tests/rf_uart_test.c'), '-o', str(exe)],
                capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
            self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
            subprocess.run([str(exe)], check=True, timeout=10, env=env)

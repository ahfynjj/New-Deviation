"""Real MMIO setup must preserve PH12/PLL1/PLL3 and fail on missing clocks."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]


class USBBoardTests(unittest.TestCase):
    def test_clock_timeouts_gpio_and_rng_error(self):
        source=ROOT/'hardware/tx15/usb_update/usb_hw.c'
        self.assertTrue(source.exists(),'USB hardware initializer is missing')
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'hw.exe'
            run=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                str(ROOT/'utils/hardware/tests/usb_board_test.c'),'-o',str(exe)],env=env,
                capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(run.returncode,0,run.stderr)
            run=subprocess.run([str(exe)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

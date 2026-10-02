"""Run the portable native CRSF router; no radio or simulator involved."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class CrsfLinkTests(unittest.TestCase):
    def test_frames_routing_and_backpressure(self):
        gcc = Path(tempfile.gettempdir()) / 'new-deviation-ucrt64/bin/gcc.exe'
        with tempfile.TemporaryDirectory(prefix='crsf-link-') as tmp:
            exe = Path(tmp) / 'test.exe'
            env = dict(os.environ, PATH=str(gcc.parent) + os.pathsep + os.environ.get('PATH', ''))
            cmd = [str(gcc), '-std=c99', '-Wall', '-Wextra', '-Werror',
                   '-I', str(ROOT.parent/'tools/msys64/ucrt64/include'),
                   '-I', str(ROOT/'src/protocol/transport'),
                   str(ROOT/'utils/hardware/tests/crsf_link_test.c'),
                   str(ROOT/'src/protocol/transport/crsf_link.c'), '-o', str(exe)]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            subprocess.run([str(exe)], check=True, timeout=10, env=env)

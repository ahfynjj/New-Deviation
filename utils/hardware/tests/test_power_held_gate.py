import sys
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import flash_install as f

class GateTests(unittest.TestCase):
    def test_no_terminal_refuses_before_probe_open(self):
        with patch.object(f.sys.stdin,'isatty',return_value=False),patch.object(f.install_kit,'read'),patch.object(f,'open_probe') as opener:
            with self.assertRaises(SystemExit):f.main(['--arm','--rehearse'])
        opener.assert_not_called()
    def test_exact_explicit_confirmation_required(self):
        with patch.object(f.sys.stdin,'isatty',return_value=True):
            for answer in ('','yes','held'):
                with patch('builtins.input',return_value=answer),self.assertRaises(ValueError):f.power_held_gate(1)
            with patch('builtins.input',return_value='HELD'):f.power_held_gate(1)
    def test_eof_cannot_release_gate(self):
        with patch.object(f.sys.stdin,'isatty',return_value=True),patch('builtins.input',side_effect=EOFError()):
            with self.assertRaises(RuntimeError):f.power_held_gate(1)

if __name__=='__main__':unittest.main()

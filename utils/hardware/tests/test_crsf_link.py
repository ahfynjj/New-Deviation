"""Run the portable native CRSF router; no radio or simulator involved."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]


class CrsfLinkTests(unittest.TestCase):
    def test_tool_write_readback(self):
        self.run_c('crsf_tools_test.c', ['crsf_tools.c'])
    def test_lua_rf_session(self):
        self.run_c('rf_lua_test.c', ['crsf_link.c','crsf_stream.c','crsf_tools.c'],
                   ['src/target/tx/radiomaster/tx15/rf_lua.c'], ['-DTX15_ELRS_LUA=1'])
    def test_lua_rf_write_session(self):
        self.run_c('rf_lua_test.c', ['crsf_link.c','crsf_stream.c','crsf_tools.c'],
                   ['src/target/tx/radiomaster/tx15/rf_lua.c'], ['-DTX15_ELRS_LUA=1','-DTX15_ELRS_WRITE=1'])
    def test_parameter_session(self):
        self.run_c('rf_discovery_test.c', ['crsf_link.c','crsf_stream.c','crsf_params.c'],
                   ['src/target/tx/radiomaster/tx15/rf.c'], ['-DTX15_ELRS_PARAMETERS=1'])
    def test_parameter_chunks(self):
        self.run_c('crsf_params_test.c', ['crsf_params.c'])

    def test_readonly_discovery(self):
        self.run_c('rf_discovery_test.c', ['crsf_link.c','crsf_stream.c'],
                   ['src/target/tx/radiomaster/tx15/rf.c'])

    def test_stream_and_device_info(self):
        self.run_c('crsf_stream_test.c', ['crsf_link.c','crsf_stream.c'])

    def test_frames_routing_and_backpressure(self):
        self.run_c('crsf_link_test.c', ['crsf_link.c'])

    def run_c(self, test, sources, extra=(), flags=()):
        gcc = Path(tempfile.gettempdir()) / 'new-deviation-ucrt64/bin/gcc.exe'
        with tempfile.TemporaryDirectory(prefix='crsf-link-') as tmp:
            exe = Path(tmp) / 'test.exe'
            env = dict(os.environ, PATH=str(gcc.parent) + os.pathsep + os.environ.get('PATH', ''))
            cmd = [str(gcc), '-std=c99', '-Wall', '-Wextra', '-Werror', *flags,
                   '-I', str(ROOT.parent/'tools/msys64/ucrt64/include'),
                   '-I', str(ROOT/'src/protocol/transport'),
                   '-I', str(ROOT/'src'), '-I', str(ROOT),
                   str(ROOT/'utils/hardware/tests'/test),
                   *[str(ROOT/'src/protocol/transport'/s) for s in sources],
                   *[str(ROOT/s) for s in extra], '-o', str(exe)]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            subprocess.run([str(exe)], check=True, timeout=10, env=env)

"""Exercise actual Lua and official ELRS script APIs; no simulator or board."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
LUA = ROOT / 'src/lua/vendor/lua-5.2.4/src'


class LuaRuntimeTests(unittest.TestCase):
    def test_limits_and_official_script(self):
        gcc = Path(tempfile.gettempdir()) / 'new-deviation-ucrt64/bin/gcc.exe'
        env = dict(os.environ, PATH=str(gcc.parent) + os.pathsep + os.environ.get('PATH', ''))
        with tempfile.TemporaryDirectory(prefix='deviation-lua-') as tmp:
            exe = Path(tmp) / 'test.exe'
            sources = [p for p in LUA.glob('*.c') if p.name not in
                       ('lua.c', 'luac.c', 'linit.c', 'liolib.c', 'loslib.c', 'loadlib.c', 'ldblib.c', 'lcorolib.c')]
            cmd = [str(gcc), '-std=c99', '-O2', '-Wall', '-Wextra', '-DLUA_ANSI',
                   '-I', str(ROOT.parent/'tools/msys64/ucrt64/include'),
                   '-I', str(next((ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32').glob('*/include'))), '-I', str(LUA),
                   '-I', str(ROOT/'src'), str(ROOT/'utils/hardware/tests/lua_runtime_test.c'),
                   str(ROOT/'src/lua/runner.c'), str(ROOT/'src/lua/arena.c'),
                   str(ROOT/'src/protocol/transport/crsf_link.c'), str(ROOT/'src/protocol/transport/crsf_tools.c'), *map(str, sources),
                   '-o', str(exe)]
            built = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            subprocess.run([str(exe), str(ROOT/'src/lua/scripts/elrs.lua')], env=env, check=True, timeout=20)
            if os.environ.get('TX15_LUA_CAPTURE'):
                import json, struct
                capture = json.loads(Path(os.environ['TX15_LUA_CAPTURE']).read_text())
                fields = capture['ram_run']['rf_parameters']
                fixture = Path(tmp)/'parameters.bin'
                fixture.write_bytes(bytes([len(fields)]) + b''.join(
                    struct.pack('<H',len(bytes.fromhex(f['raw_hex']))) + bytes.fromhex(f['raw_hex']) for f in fields))
                subprocess.run([str(exe), str(ROOT/'src/lua/scripts/elrs.lua'),str(fixture)],env=env,check=True,timeout=20)

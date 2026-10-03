import os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app_image import parse
from boot_image import unpack

class StandaloneAppTests(unittest.TestCase):
    def test_contract_modes_reject_each_others_entry_and_require_complete_cold_boot(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            for standalone in (False,True):
                exe=Path(tmp)/f'contract-{standalone}.exe'
                args=[str(gcc),'-std=c99','-Wall','-Wextra','-Werror','-I',str(ROOT),
                    '-I',str(ROOT.parent/'tools/msys64/ucrt64/include')]
                if standalone:args.append('-DTX15_STANDALONE=1')
                r=subprocess.run([*args,str(ROOT/'utils/hardware/tests/app_boot_contract_test.c'),
                    str(ROOT/'src/target/tx/radiomaster/tx15/boot_contract.c'),str(ROOT/'hardware/tx15/boot/handoff.c'),
                    '-o',str(exe)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
                self.assertEqual(r.returncode,0,r.stdout+r.stderr)
                subprocess.run([str(exe)],check=True,env=env)

    def test_standalone_arm_build_and_rf_opt_ins_refused(self):
        env={k:v for k,v in os.environ.items() if k not in ('TX15_STANDALONE','TX15_ELRS_LUA',
             'TX15_ELRS_RC','TX15_ELRS_WRITE','TX15_ELRS_DISCOVERY','TX15_ELRS_PARAMETERS')}
        env['TX15_STANDALONE']='1'
        r=subprocess.run([sys.executable,str(ROOT/'utils/build-tx15-app.py')],cwd=ROOT,env=env,
                         capture_output=True,text=True,encoding='utf8',errors='replace')
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        out=ROOT/'local/tx15-hardware/app-standalone'
        entry,segments=parse((out/'tx15-app.elf').read_bytes())
        other,stored=unpack((out/'tx15-app.nd15').read_bytes())
        self.assertEqual((entry,segments),(other,stored))
        env['TX15_ELRS_LUA']='1'
        r=subprocess.run([sys.executable,str(ROOT/'utils/build-tx15-app.py')],cwd=ROOT,env=env,
                         capture_output=True,text=True,encoding='utf8',errors='replace')
        self.assertNotEqual(r.returncode,0)
        self.assertIn('Standalone first-boot build keeps RF disabled',r.stderr)

if __name__=='__main__':unittest.main()

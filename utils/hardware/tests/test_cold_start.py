"""Cold-start power/Flash/RCC sequencing at the real driver's MMIO boundary."""
import os, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class ColdStartTests(unittest.TestCase):
    def test_supply_prelude_is_stackless_and_before_first_ram_write(self):
        support=ROOT.parent/'tools/arm8/bin'
        gcc=Path(tempfile.gettempdir())/'new-deviation-arm8/bin/arm-none-eabi-gcc.exe'
        with tempfile.TemporaryDirectory() as tmp:
            obj=Path(tmp)/'early.o';startup=Path(tmp)/'startup.o'
            for source,target in [('hardware/tx15/boot/early_supply.S',obj),('hardware/tx15/ram_probe/startup.S',startup)]:
                result=subprocess.run([str(gcc),'-mcpu=cortex-m7','-mthumb','-DTX15_BOOT_EARLY_SUPPLY=1',
                    '-c',str(ROOT/source),'-o',str(target)],capture_output=True,text=True,encoding='utf8',errors='replace')
                self.assertEqual(result.returncode,0,result.stderr)
            text=subprocess.check_output([str(support/'arm-none-eabi-objdump.exe'),'-dr',str(obj)],text=True,encoding='utf8',errors='replace')
            self.assertNotRegex(text,r'\b(push|pop|bl|blx|sp)\b')
            self.assertIn('5802480c',text);self.assertIn('58024804',text)
            startup_text=subprocess.check_output([str(support/'arm-none-eabi-objdump.exe'),'-dr',str(startup)],text=True,encoding='utf8',errors='replace')
            self.assertLess(startup_text.index('tx15_boot_supply_early'),startup_text.index('strd'))

    def test_reset_supply_voltage_latency_and_failures(self):
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'cold-start.exe'
            result=subprocess.run([str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),'-I',str(ROOT),
                str(ROOT/'utils/hardware/tests/cold_start_test.c'),'-o',str(exe)],
                env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            result=subprocess.run([str(exe)],env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

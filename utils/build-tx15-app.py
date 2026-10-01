"""Cross-compile original Deviation GUI/pages for native TX15 (no emulator).
Builds a RAM-only ELF; hardware acceptance is a separate step.
"""
import os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'local/tx15-hardware/app'; out.mkdir(parents=True,exist_ok=True)
arm=Path(os.environ['TEMP'])/'new-deviation-arm8/bin'
flags=['-isystem',str(root.parent/'tools/arm8/lib/gcc/arm-none-eabi/8.2.1/include'),
 '-isystem',str(root.parent/'tools/arm8/lib/gcc/arm-none-eabi/8.2.1/include-fixed'),
 '-isystem',str(root.parent/'tools/arm8/arm-none-eabi/include'),'-mcpu=cortex-m7','-mthumb','-mfloat-abi=soft','-std=gnu99','-Os','-g',
 '-ffunction-sections','-fdata-sections','-ffreestanding','-fno-common',
 '-Wall','-Wextra','-Werror=implicit-function-declaration','-Werror=undef',
 '-DBUILD_TYPE=0','-DSTATUS_SCREEN','-DHGVERSION="New Deviation TX15 RAM"']
for d in ('src','src/target/tx/radiomaster/tx15','src/target/drivers/filesystems',
 'src/gui/320x240x16','src/pages/320x240x16'):
 flags+=['-I',str(root/d)]
sources=[]
for pattern in ('src/gui/*.c','src/screen/*.c','src/screen/320x240x16/*.c',
 'src/pages/320x240x16/*.c','src/pages/320x240x16/advanced/*.c',
 'src/config/*.c','src/misc/*.c','src/target/tx/radiomaster/tx15/*.c'):
 sources+=sorted(root.glob(pattern))
sources=[s for s in sources if s.name not in ('datalog_page.c','scanner_page.c','fgets.c')]
sources += [root/'src'/n for n in ('buttons.c','mixer.c','curves.c','inputs.c','mixer_standard.c','remap_channels.c','timer.c','telemetry.c','autodimmer.c')]
from tx15_resources import generate
sources.append(generate(root,out))
sources += [root/'hardware/tx15/board'/n for n in ('display.c','inputs.c','input_filter.c')]
sources.append(root/'hardware/tx15/app/startup.S')
objects=[]
with (out/'compile.log').open('w',encoding='utf-8') as log:
 for src in sources:
  obj=out/('_'.join(src.relative_to(root).parts)+'.o')
  r=subprocess.run([str(arm/'arm-none-eabi-gcc.exe'),*flags,'-c',str(src),'-o',str(obj)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace")
  log.write(r.stdout)
  if r.returncode:
   print(src.relative_to(root)); print(r.stdout); sys.exit(r.returncode)
  objects.append(str(obj))
archive=out/'deviation-native-pages.a'
# Recreate to avoid retaining stale members after a source list changes.
if archive.exists(): archive.unlink()
subprocess.run([str(root.parent/'tools/arm8/bin/arm-none-eabi-ar.exe'),'rcs',str(archive),*objects],check=True)
print(f'Compiled {len(objects)} ARM objects -> {archive}')
# Produce a relocatable integration object without inventing peripheral stubs.
combined=out/'deviation-native-pages.o'
ld=root.parent/'tools/arm8/bin/arm-none-eabi-ld.exe'
subprocess.run([str(ld),'-r','--whole-archive',str(archive),'--no-whole-archive','-o',str(combined)],check=True)
nm=root.parent/'tools/arm8/bin/arm-none-eabi-nm.exe'
missing=subprocess.check_output([str(nm),'-u',str(combined)],text=True)
(out/'unresolved.txt').write_text(missing)
print('Unresolved runtime interfaces written to',out/'unresolved.txt')


elf=out/'tx15-app.elf'
lib=root.parent/'tools/arm8/arm-none-eabi/lib/thumb/v7e-m/nofp'
gcc_lib=root.parent/'tools/arm8/lib/gcc/arm-none-eabi/8.2.1/thumb/v7e-m/nofp/libgcc.a'
command=[str(ld),'--gc-sections','-T',str(root/'hardware/tx15/app/app.ld'),
 '-Map='+str(out/'tx15-app.map'),'-o',str(elf),'--start-group',*objects,
 str(lib/'libc.a'),str(lib/'libm.a'),str(gcc_lib),'--end-group']
r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
(out/'link.log').write_text(r.stdout,encoding='utf-8')
if r.returncode:
 print(r.stdout[-16000:]);sys.exit(r.returncode)
from hardware.app_image import parse
entry,segments=parse(elf.read_bytes())
print('Linked and checked RAM load map:',elf,'entry',hex(entry))
print('No device accessed; hardware acceptance remains pending.')

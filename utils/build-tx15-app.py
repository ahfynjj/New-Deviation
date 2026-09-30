"""Cross-compile original Deviation GUI/pages for native TX15 (no emulator).
This integration archive is NOT a loadable image. Runtime/link stage follows.
"""
import os, subprocess, sys
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
sources=[s for s in sources if s.name not in ('telemtest_page.c','telemconfig_page.c','datalog_page.c','scanner_page.c','fgets.c')]
sources += [root/'src'/n for n in ('buttons.c','mixer.c','curves.c')]
from tx15_resources import generate
sources.append(generate(root,out))
objects=[]
with (out/'compile.log').open('w') as log:
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
print('Compile integration only; not linked or loadable; no device accessed.')

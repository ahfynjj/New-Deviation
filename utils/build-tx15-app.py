"""Cross-compile original Deviation GUI/pages for native TX15 (no emulator).
Builds a RAM-executed ELF. Opt-in standalone mode requires the native cold loader.
"""
import hashlib,json,os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
from pathlib import Path
root=Path(__file__).resolve().parents[1]
standalone=os.environ.get('TX15_STANDALONE')=='1'
product=os.environ.get('TX15_ELRS_PRODUCT')=='1'
if product and any(os.environ.get(n)!='1' for n in ('TX15_ELRS_RC','TX15_ELRS_LUA','TX15_ELRS_WRITE')):
 raise ValueError('ELRS product build requires RC, Lua and parameter writes')
if standalone and not product and any(os.environ.get(n)=='1' for n in ('TX15_ELRS_LUA','TX15_ELRS_RC',
 'TX15_ELRS_WRITE','TX15_ELRS_DISCOVERY','TX15_ELRS_PARAMETERS')):
 raise ValueError('Standalone first-boot build keeps RF disabled; validate cold boot before adding RF modes')
out=root/'local/tx15-hardware'/('app-standalone' if standalone else 'app'); out.mkdir(parents=True,exist_ok=True)
arm=Path(os.environ['TEMP'])/'new-deviation-arm8/bin'
if os.environ.get('TX15_ELRS_RC')=='1' and os.environ.get('TX15_ELRS_LUA')!='1':
 raise ValueError('RC bench requires the shared Lua RF session build')
if os.environ.get('TX15_ELRS_WRITE')=='1' and os.environ.get('TX15_ELRS_LUA')!='1':
 raise ValueError('Selection writes require the Lua tool build')
if os.environ.get('TX15_ELRS_LUA') == '1' and any(os.environ.get(n)=='1' for n in ('TX15_ELRS_DISCOVERY','TX15_ELRS_PARAMETERS')):
 raise ValueError('Lua and diagnostic RF modes cannot run together')
flags=['-isystem',str(root.parent/'tools/arm8/lib/gcc/arm-none-eabi/8.2.1/include'),
 '-isystem',str(root.parent/'tools/arm8/lib/gcc/arm-none-eabi/8.2.1/include-fixed'),
 '-isystem',str(root.parent/'tools/arm8/arm-none-eabi/include'),'-mcpu=cortex-m7','-mthumb','-mfloat-abi=soft','-std=gnu99','-Os','-g',
 '-ffunction-sections','-fdata-sections','-ffreestanding','-fno-common',
 '-Wall','-Wextra','-Werror=implicit-function-declaration','-Werror=undef',
 '-DTX15_INPUT_TRACE=1','-DBUILD_TYPE=0','-DSTATUS_SCREEN',
 '-DHGVERSION="New Deviation TX15"' if standalone else '-DHGVERSION="New Deviation TX15 RAM"']
if product:flags.append('-DTX15_ELRS_PRODUCT=1')
if os.environ.get('TX15_PERSISTENCE')=='1':flags.append('-DTX15_PERSISTENCE=1')
if standalone:flags.append('-DTX15_STANDALONE=1')
if os.environ.get('TX15_ELRS_DISCOVERY') == '1':
 flags.append('-DTX15_ELRS_DISCOVERY=1')
if os.environ.get('TX15_ELRS_PARAMETERS') == '1':
 flags+=['-DTX15_ELRS_DISCOVERY=1','-DTX15_ELRS_PARAMETERS=1']
if os.environ.get('TX15_ELRS_LUA') == '1':
 flags+=['-DTX15_ELRS_LUA=1','-DLUA_ANSI','-I',str(root/'src/lua/vendor/lua-5.2.4/src')]
 if os.environ.get('TX15_ELRS_WRITE')=='1': flags.append('-DTX15_ELRS_WRITE=1')
 if os.environ.get('TX15_ELRS_RC')=='1': flags.append('-DTX15_ELRS_RC=1')
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
# Portable CRSF core is used by the opt-in discovery build. Default builds
# leave module power off and linker GC removes unused discovery code.
sources.append(root/'src/protocol/transport/crsf_link.c')
sources.append(root/'src/protocol/transport/crsf_stream.c')
sources.append(root/'src/protocol/transport/crsf_params.c')
sources.append(root/'src/protocol/transport/crsf_tools.c')
sources.append(root/'src/protocol/transport/crsf_rc.c')
if os.environ.get('TX15_ELRS_LUA') == '1':
 sources += [root/'src/lua/runner.c',root/'src/lua/arena.c']
 sources += [p for p in (root/'src/lua/vendor/lua-5.2.4/src').glob('*.c') if p.name not in
             ('lua.c','luac.c','linit.c','liolib.c','loslib.c','loadlib.c','ldblib.c','lcorolib.c')]
from tx15_resources import generate
sources.append(generate(root,out))
sources += [root/'hardware/tx15/board'/n for n in ('display.c','inputs.c','input_filter.c','analog.c','battery.c','rf_uart.c','controls.c','control_decode.c','settings_store.c','settings_nor.c','rf_external.c')]
sources.append(root/'hardware/tx15/app/startup.S')
if standalone:
 sources += [root/'hardware/tx15/boot'/n for n in ('handoff.c','power_button.c')]
 sources.append(root/'hardware/tx15/board/power.c')
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
from hardware.boot_image import pack
payload=out/'tx15-app.nd15'
payload.write_bytes(pack(elf.read_bytes()))
if len(payload.read_bytes())>0xf0000:raise ValueError('Application overlaps native settings region')
(out/'build.json').write_text(json.dumps({'schema':1,
 'mode':'standalone-elrs-candidate' if standalone and product else ('standalone-first-boot-rf-off' if standalone else 'ram-bench'),
 'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),
 'payload_sha256':hashlib.sha256(payload.read_bytes()).hexdigest(),
 'rf_enabled':any(os.environ.get(n)=='1' for n in ('TX15_ELRS_LUA','TX15_ELRS_DISCOVERY','TX15_ELRS_RC')),
 'persistent_settings':os.environ.get('TX15_PERSISTENCE')=='1'},indent=2),encoding='utf8')
print('Checked native boot payload:',payload,'(requires cold-start loader; not directly flashable)')
print('No device accessed; hardware acceptance remains pending.')

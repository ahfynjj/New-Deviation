"""Build RAM-only cold-start/QSPI observation bench. Never connects or flashes."""
import subprocess, tempfile
from pathlib import Path
from hardware.check_ram_elf import check
root=Path(__file__).resolve().parents[1]
arm=Path(tempfile.gettempdir())/'new-deviation-arm8/bin'
support=root.parent/'tools/arm8'
out=root/'local/tx15-hardware/boot-bench'
out.mkdir(parents=True,exist_ok=True)
flags=['-DTX15_BOOT_EARLY_SUPPLY=1','-isystem',str(support/'lib/gcc/arm-none-eabi/8.2.1/include'),
    '-isystem',str(support/'lib/gcc/arm-none-eabi/8.2.1/include-fixed'),
    '-isystem',str(support/'arm-none-eabi/include'),'-mcpu=cortex-m7','-mthumb',
    '-mfloat-abi=soft','-std=c11','-Os','-g3','-ffreestanding','-fno-builtin',
    '-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror']
sources=['hardware/tx15/ram_probe/startup.S','hardware/tx15/board/power.c',
    'hardware/tx15/board/clock.c','hardware/tx15/board/pll.c',
    'hardware/tx15/boot/early_supply.S','hardware/tx15/boot/cold_start.c',
    'hardware/tx15/boot/qspi.c','hardware/tx15/boot/bench.c']
objects=[]
for src in sources:
    obj=out/(Path(src).stem+'.o')
    subprocess.run([str(arm/'arm-none-eabi-gcc.exe'),*flags,'-c',str(root/src),'-o',str(obj)],check=True)
    objects.append(str(obj))
elf=out/'boot-bench.elf'
subprocess.run([str(support/'bin/arm-none-eabi-ld.exe'),'--gc-sections',
    '-T',str(root/'hardware/tx15/ram_probe/ram.ld'),'-Map='+str(out/'boot-bench.map'),
    '-o',str(elf),*objects],check=True)
print('Checked RAM layout:',check(elf.read_bytes()))
subprocess.run([str(support/'bin/arm-none-eabi-objcopy.exe'),'-O','binary',str(elf),str(out/'boot-bench.bin')],check=True)
subprocess.run([str(support/'bin/arm-none-eabi-size.exe'),str(elf)],check=True)
print('RAM bench ready:',elf,'; no target connection, Flash write or cold-boot acceptance.')

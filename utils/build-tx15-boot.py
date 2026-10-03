"""Build native internal-Flash loader; no device connection or programming."""
import subprocess,tempfile
from pathlib import Path
from hardware.boot_elf import parse
root=Path(__file__).resolve().parents[1]
arm=Path(tempfile.gettempdir())/'new-deviation-arm8/bin'
support=root.parent/'tools/arm8';out=root/'local/tx15-hardware/boot';out.mkdir(parents=True,exist_ok=True)
flags=['-isystem',str(support/'lib/gcc/arm-none-eabi/8.2.1/include'),
    '-isystem',str(support/'lib/gcc/arm-none-eabi/8.2.1/include-fixed'),'-isystem',str(support/'arm-none-eabi/include'),
    '-mcpu=cortex-m7','-mthumb','-mfloat-abi=soft','-std=c11','-Os','-g3',
    '-ffreestanding','-fno-builtin','-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror']
sources=[root/'hardware/tx15/boot'/n for n in ('startup.S','early_supply.S','cold_start.c','qspi.c','image.c','loader.c','handoff.c','main.c')]
sources+=[root/'hardware/tx15/board'/n for n in ('power.c','clock.c','pll.c','sdram.c','display.c')]
objects=[]
for src in sources:
    obj=out/(src.stem+'.o');subprocess.run([str(arm/'arm-none-eabi-gcc.exe'),*flags,'-c',str(src),'-o',str(obj)],check=True);objects.append(str(obj))
elf=out/'tx15-boot.elf'
subprocess.run([str(support/'bin/arm-none-eabi-ld.exe'),'--gc-sections','-T',str(root/'hardware/tx15/boot/boot.ld'),
    '-Map='+str(out/'tx15-boot.map'),'-o',str(elf),*objects],check=True)
print('Checked internal Flash load map:',parse(elf.read_bytes()))
subprocess.run([str(support/'bin/arm-none-eabi-objcopy.exe'),'-O','binary',str(elf),str(out/'tx15-boot.bin')],check=True)
subprocess.run([str(support/'bin/arm-none-eabi-size.exe'),str(elf)],check=True)
print('Native loader built; Flash installation, recovery and true POR acceptance remain pending.')

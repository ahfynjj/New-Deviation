"""Build native internal-Flash loader; no device connection or programming."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
from hardware.boot_elf import parse
root=Path(__file__).resolve().parents[1]
arm=Path(tempfile.gettempdir())/'new-deviation-arm8/bin'
args=argparse.ArgumentParser(description=__doc__)
args.add_argument('--ram-chain',action='store_true',help='RAM loader with host-fed SDRAM source; no Flash writes')
options=args.parse_args()
support=root.parent/'tools/arm8';out=root/'local/tx15-hardware'/('boot-chain' if options.ram_chain else 'boot');out.mkdir(parents=True,exist_ok=True)
flags=['-isystem',str(support/'lib/gcc/arm-none-eabi/8.2.1/include'),
    '-isystem',str(support/'lib/gcc/arm-none-eabi/8.2.1/include-fixed'),'-isystem',str(support/'arm-none-eabi/include'),
    '-mcpu=cortex-m7','-mthumb','-mfloat-abi=soft','-std=c11','-Os','-g3',
    '-ffreestanding','-fno-builtin','-ffunction-sections','-fdata-sections','-Wall','-Wextra','-Werror']
if options.ram_chain: flags+=['-DTX15_RAM_CHAIN=1']
sources=[root/'hardware/tx15/boot'/n for n in ('startup.S','early_supply.S','cold_start.c','qspi.c','image.c','loader.c','handoff.c','main.c')]
sources+=[root/'hardware/tx15/board'/n for n in ('power.c','clock.c','pll.c','sdram.c','display.c')]
objects=[]
for src in sources:
    obj=out/(src.stem+'.o');subprocess.run([str(arm/'arm-none-eabi-gcc.exe'),*flags,'-c',str(src),'-o',str(obj)],check=True);objects.append(str(obj))
name='boot-chain' if options.ram_chain else 'tx15-boot'
elf=out/(name+'.elf');binary=out/(name+'.bin')
script='chain.ld' if options.ram_chain else 'boot.ld'
subprocess.run([str(support/'bin/arm-none-eabi-ld.exe'),'--gc-sections','-T',str(root/'hardware/tx15/boot'/script),
    '-Map='+str(out/(name+'.map')),'-o',str(elf),*objects],check=True)
if options.ram_chain:
    from hardware.check_ram_elf import check
    print('Checked RAM load map:',check(elf.read_bytes()))
else: print('Checked internal Flash load map:',parse(elf.read_bytes()))
subprocess.run([str(support/'bin/arm-none-eabi-objcopy.exe'),'-O','binary',str(elf),str(binary)],check=True)
subprocess.run([str(support/'bin/arm-none-eabi-size.exe'),str(elf)],check=True)
if options.ram_chain:
    symbols=subprocess.check_output([str(support/'bin/arm-none-eabi-nm.exe'),str(elf)],text=True)
    control=int(next(l.split()[0] for l in symbols.splitlines() if l.endswith(' chain_control')),16)
    (out/'build.json').write_text(json.dumps(dict(schema=1,mode='ram-chain-no-flash',control=control,
        elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),bin_sha256=hashlib.sha256(binary.read_bytes()).hexdigest()),indent=2)+'\n')
print('Native loader built; Flash installation, recovery and true POR acceptance remain pending.')

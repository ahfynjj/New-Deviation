"""Build the isolated read-only RAM CDC probe. Never opens a device."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from hardware.check_ram_elf import check

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe',action='store_true',required=True)
    parser.add_argument('--out',type=Path,default=ROOT/'local/tx15-hardware/usb-probe')
    args=parser.parse_args();out=args.out.resolve()
    legacy=[ROOT/'local/tx15-hardware'/p for p in ('boot','boot-chain','app','app-standalone')]
    if any(out==p or p in out.parents for p in legacy): parser.error('Refusing a legacy output directory')
    out.mkdir(parents=True,exist_ok=True)
    vendor=ROOT/'third_party/usb'
    sources_manifest=json.loads((vendor/'sources.json').read_text())
    for name,digest in sources_manifest['files'].items():
        if hashlib.sha256((vendor/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Pinned USB source changed: '+name)
    usb=ROOT/'hardware/tx15/usb_update';tiny=vendor/'tinyusb/src'
    support=ROOT.parent/'tools/arm8';arm=Path(tempfile.gettempdir())/'new-deviation-arm8/bin'
    flags=['-mcpu=cortex-m7','-mthumb','-mfloat-abi=soft','-std=gnu11','-Os','-g3',
           '-ffreestanding','-fno-builtin','-ffunction-sections','-fdata-sections','-Wall','-Wextra',
           '-Werror=implicit-function-declaration','-Werror=undef','-DSTM32H750xx']
    for p in (support/'lib/gcc/arm-none-eabi/8.2.1/include',support/'lib/gcc/arm-none-eabi/8.2.1/include-fixed',
              support/'arm-none-eabi/include',vendor/'cmsis',vendor/'stm32h7',tiny): flags+=['-isystem',str(p)]
    flags+=['-I',str(usb)]
    sources=[usb/p for p in ('startup.S','usb_hw.c','usb_board.c','usb_descriptors.c','probe_main.c',
                            'package.c','protocol.c','receiver.c')]
    sources+=[ROOT/'hardware/tx15/boot'/p for p in ('early_supply.S','image.c')]
    sources+=[ROOT/'hardware/tx15/board/power.c']
    sources+=[tiny/p for p in ('tusb.c','common/tusb_fifo.c','device/usbd.c','device/usbd_control.c',
              'class/cdc/cdc_device.c','portable/synopsys/dwc2/dcd_dwc2.c','portable/synopsys/dwc2/dwc2_common.c')]
    objects=[]
    with (out/'compile.log').open('w',encoding='utf8') as log:
        for src in sources:
            obj=out/('_'.join(src.relative_to(ROOT).parts)+'.o')
            r=subprocess.run([str(arm/'arm-none-eabi-gcc.exe'),*flags,'-c',str(src),'-o',str(obj)],
                             capture_output=True,text=True,encoding='utf8',errors='replace')
            log.write(r.stdout+r.stderr)
            if r.returncode: raise RuntimeError(r.stdout+r.stderr)
            objects.append(str(obj))
    elf=out/'tx15-usb-probe.elf';binary=out/'tx15-usb-probe.bin'
    libc=support/'arm-none-eabi/lib/thumb/v7e-m/nofp/libc.a'
    libgcc=support/'lib/gcc/arm-none-eabi/8.2.1/thumb/v7e-m/nofp/libgcc.a'
    subprocess.run([str(support/'bin/arm-none-eabi-ld.exe'),'--gc-sections','-T',
        str(ROOT/'hardware/tx15/boot/chain.ld'),'-Map='+str(out/'tx15-usb-probe.map'),
        '-o',str(elf),*objects,'--start-group',str(libc),str(libgcc),'--end-group'],check=True)
    layout=check(elf.read_bytes())
    subprocess.run([str(support/'bin/arm-none-eabi-objcopy.exe'),'-O','binary',str(elf),str(binary)],check=True)
    subprocess.run([str(support/'bin/arm-none-eabi-size.exe'),str(elf)],check=True)
    report=dict(schema=1,mode='usb-readonly-ram-probe',entry=int(layout['entry'],16),
                elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),
                bin_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                flash_mutation_linked=False,layout=layout,sources=sources_manifest['projects'])
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report));print('Built only. USB enumeration and transmission remain untested.')


if __name__=='__main__': main()

"""Isolated resident USB candidate build; never opens a hardware device."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from hardware.boot_elf import parse,binary

ROOT=Path(__file__).resolve().parents[2]

def build(destination=None):
    out=(destination or ROOT/'local/tx15-hardware/boot-usb').resolve()
    for name in ('boot','boot-chain','app','app-standalone','usb-probe','usb-probe-sdram'):
        legacy=ROOT/'local/tx15-hardware'/name
        if out==legacy or out in legacy.parents or legacy in out.parents:
            raise ValueError('Refusing a legacy output directory')
    out.mkdir(parents=True,exist_ok=True)
    vendor=ROOT/'third_party/usb'
    manifest=json.loads((vendor/'sources.json').read_text())
    for name,digest in manifest['files'].items():
        if hashlib.sha256((vendor/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Pinned USB source changed: '+name)
    usb=ROOT/'hardware/tx15/usb_update';boot=ROOT/'hardware/tx15/boot'
    board=ROOT/'hardware/tx15/board';tiny=vendor/'tinyusb/src'
    support=ROOT.parent/'tools/arm8';arm=Path(tempfile.gettempdir())/'new-deviation-arm8/bin'
    flags=['-mcpu=cortex-m7','-mthumb','-mfloat-abi=soft','-std=gnu11','-Os','-g3',
           '-ffreestanding','-fno-builtin','-ffunction-sections','-fdata-sections','-Wall','-Wextra',
           '-Werror=implicit-function-declaration','-Werror=undef','-DSTM32H750xx','-DTX15_USB_UPDATE=1']
    for p in (support/'lib/gcc/arm-none-eabi/8.2.1/include',support/'lib/gcc/arm-none-eabi/8.2.1/include-fixed',
              support/'arm-none-eabi/include',vendor/'cmsis',vendor/'stm32h7',tiny):
        flags+=['-isystem',str(p)]
    flags+=['-I',str(usb)]
    sources=[boot/p for p in ('startup.S','early_supply.S','cold_start.c','qspi.c','image.c','loader.c',
                             'handoff.c','main.c','update_mode.c','update_main.c')]
    sources+=[board/p for p in ('power.c','clock.c','pll.c','sdram.c','display.c')]
    sources+=[usb/p for p in ('usb_hw.c','usb_board.c','usb_descriptors.c','package.c','protocol.c',
                            'receiver.c','transaction.c','runtime.c','nor_geometry.c','nor.c','screen.c')]
    sources+=[tiny/p for p in ('tusb.c','common/tusb_fifo.c','device/usbd.c','device/usbd_control.c',
              'class/cdc/cdc_device.c','portable/synopsys/dwc2/dcd_dwc2.c','portable/synopsys/dwc2/dwc2_common.c')]
    objects=[]
    with (out/'compile.log').open('w',encoding='utf8') as log:
        for src in sources:
            obj=out/('_'.join(src.relative_to(ROOT).parts)+'.o')
            r=subprocess.run([str(arm/'arm-none-eabi-gcc.exe'),*flags,'-c',str(src),'-o',str(obj)],
                             capture_output=True,text=True,encoding='utf8',errors='replace')
            log.write(r.stdout+r.stderr)
            if r.returncode:raise RuntimeError(r.stdout+r.stderr)
            objects.append(str(obj))
    elf=out/'tx15-boot-usb.elf';raw=out/'tx15-boot-usb.bin'
    libc=support/'arm-none-eabi/lib/thumb/v7e-m/nofp/libc.a'
    libgcc=support/'lib/gcc/arm-none-eabi/8.2.1/thumb/v7e-m/nofp/libgcc.a'
    subprocess.run([str(support/'bin/arm-none-eabi-ld.exe'),'--gc-sections','-T',str(boot/'boot.ld'),
        '-Map='+str(out/'tx15-boot-usb.map'),'-o',str(elf),*objects,
        '--start-group',str(libc),str(libgcc),'--end-group'],check=True)
    layout=parse(elf.read_bytes())
    subprocess.run([str(support/'bin/arm-none-eabi-objcopy.exe'),'-O','binary',str(elf),str(raw)],check=True)
    if raw.read_bytes()!=binary(elf.read_bytes()):raise ValueError('Boot ELF/raw binary mismatch')
    subprocess.run([str(support/'bin/arm-none-eabi-size.exe'),str(elf)],check=True)
    report=dict(schema=1,mode='resident-usb-update-candidate',boot_api=1,settings_abi=1,
        elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),bin_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
        layout=layout,sources=manifest['projects'],hardware_installation_verified=False)
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report));print('Built only. Resident boot, USB NOR writes and power-cycle acceptance pending.')

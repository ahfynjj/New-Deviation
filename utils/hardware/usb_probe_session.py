"""Explicitly armed, RAM-only USB probe; every exit leaves the CPU halted.

First runs the already-reviewed read-only RAM initializer, then launches the
separately approved USB candidate. No old PC restoration and no Flash backend.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import time
from types import SimpleNamespace
import install_entry
import install_kit
from check_ram_elf import check
from recovery_context import RecoveryContext, DHCSR
ROOT=Path(__file__).resolve().parents[2]


def candidate(folder):
    folder=Path(folder);meta=json.loads((folder/'build.json').read_text(encoding='utf8'))
    elf=(folder/'tx15-usb-probe.elf').read_bytes();binary=(folder/'tx15-usb-probe.bin').read_bytes()
    layout=check(elf)
    if (meta.get('schema')!=1 or meta.get('mode')!='usb-readonly-ram-probe'
        or meta.get('flash_mutation_linked') is not False
        or meta.get('elf_sha256')!=hashlib.sha256(elf).hexdigest()
        or meta.get('bin_sha256')!=hashlib.sha256(binary).hexdigest()
        or meta.get('entry')!=int(layout['entry'],16) or meta.get('layout')!=layout
        or not 704<=len(binary)<=0xe000 or len(binary)%8):
        raise ValueError('USB RAM candidate metadata/layout/hash differs')
    # Independently recreate the raw load image; a matching metadata hash alone
    # cannot pair an unrelated BIN with a valid ELF.
    phoff=struct.unpack_from('<I',elf,28)[0];phnum=struct.unpack_from('<H',elf,44)[0]
    rebuilt=bytearray(len(binary))
    end=0
    for i in range(phnum):
        typ,off,va,pa,fs,ms,flags,align=struct.unpack_from('<8I',elf,phoff+i*32)
        if typ==1 and fs:
            index=pa-0x24000000
            if index<0 or index+fs>len(binary):raise ValueError('BIN storage differs from ELF')
            rebuilt[index:index+fs]=elf[off:off+fs];end=max(end,index+fs)
    if end!=len(binary) or bytes(rebuilt)!=binary:raise ValueError('BIN bytes differ from ELF')
    return SimpleNamespace(reader=binary,entry=meta['entry'],manifest=meta)


def launch(context,binary,entry):
    if not all(context.report.get(k) for k in ('uid_verified','power_hold_verified','halted_in_thread')):
        raise RuntimeError('USB upload requires verified reset entry, UID and held supply')
    if context.io.read32(DHCSR)&0xa0000!=0x20000 or context.io.read32(0xe000ed04)&511:
        raise RuntimeError('USB upload requires confirmed thread-mode halt')
    context.image_bytes=len(binary)
    for off in range(0,len(binary),4):context._write(0x24000000+off,struct.unpack_from('<I',binary,off)[0])
    if context._bytes(0x24000000,len(binary))!=binary:raise RuntimeError('USB RAM candidate readback failed')
    for off in range(0,128,4):context._write(0x2400e000+off,0)
    if context._bytes(0x2400e000,128)!=bytes(128):raise RuntimeError('USB mailbox clear failed')
    context._core(20,1);context._core(16,0x1000000);context._core(17,0x24010000)
    context._core(18,0x24010000);context._core(15,entry)
    context._write(DHCSR,0xa05f0001)
    context._wait(lambda:context.io.read32(0x2400e000)==0x55534231 and context.io.read32(0x2400e008) in (3,8),15)
    if context.io.read32(0x2400e008)!=3:raise RuntimeError('USB RAM initialization failed')
    first=context.io.read32(0x2400e010);time.sleep(.05)
    if not 0<(context.io.read32(0x2400e010)-first)&0xffffffff<1000:raise RuntimeError('USB tick did not advance')
    context.report['usb_ram_readback_verified']=True


def run(folder,*,armed=False,expected_sha=None,held=None,opener=None,baseline_folder=None,seconds=60):
    usb=candidate(folder)
    report=dict(offline=not armed,bin_sha256=usb.manifest['bin_sha256'],flash_mutation_commands=0)
    if not armed:return report
    if expected_sha!=usb.manifest['bin_sha256'] or not callable(held) or not 1<=seconds<=180:
        raise ValueError('Exact USB candidate SHA and explicit held-power gate required')
    baseline=install_kit.read(baseline_folder or ROOT/'local/tx15-hardware/install/kit')
    if opener is None:
        from flash_install import open_probe
        opener=lambda:open_probe(500000)
    with install_entry.lease(Path(tempfile.gettempdir()),'new-deviation-tx15-pwlink2.lock'):
        context=RecoveryContext(opener(),ready_gate=held)
        try:
            context.enter(baseline)
            launch(context,usb.reader,usb.entry)
            print('USB RAM PROBE RUNNING: release POWER; connect TX15 data USB. No Flash writes.',flush=True)
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                if context.io.read32(0x2400e008)!=3:raise RuntimeError('USB probe faulted')
                time.sleep(.2)
            report.update(mailbox=list(struct.unpack('<32I',context._bytes(0x2400e000,128))))
        finally:
            install_entry.finish_context(context)
            report.update(context=context.report)
    print('HALTED. Disconnect probe USB and battery for 5 seconds, then boot normally.',flush=True)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',type=Path,default=ROOT/'local/tx15-hardware/usb-probe')
    p.add_argument('--arm',action='store_true');p.add_argument('--candidate-sha')
    p.add_argument('--baseline-kit',type=Path);p.add_argument('--seconds',type=int,default=60)
    args=p.parse_args()
    if args.arm and not sys.stdin.isatty():p.error('RAM test requires an interactive held-power confirmation')
    from flash_install import power_held_gate
    report=run(args.candidate,armed=args.arm,expected_sha=args.candidate_sha,
               held=(lambda:power_held_gate(300)) if args.arm else None,
               baseline_folder=args.baseline_kit,seconds=args.seconds)
    logs=ROOT/'local/hardware-session';logs.mkdir(parents=True,exist_ok=True)
    if args.arm:(logs/'usb-probe-last.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()

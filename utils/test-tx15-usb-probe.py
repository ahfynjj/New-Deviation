"""Read-only RAM probe acceptance. Refuses non-probe/writable devices."""
import argparse
import json
from pathlib import Path
import time
import struct
from usb_update.protocol import Frame,FrameCodec,Opcode,DeviceInfo,DeviceStatus,encode
from usb_update.package import unpack


def open_cdc_port(serial,device,timeout=3):
    """Windows may publish COM identity before its device path is ready."""
    deadline=time.monotonic()+timeout
    while True:
        try:
            return serial.Serial(device,115200,timeout=.1,write_timeout=3)
        except serial.SerialException:
            if time.monotonic()>=deadline:raise
            time.sleep(.1)


def exchange(port,codec,frame,timeout=5):
    data=encode(frame);offset=0
    deadline=time.monotonic()+timeout
    while offset<len(data):
        if time.monotonic()>deadline:raise TimeoutError('USB write timeout')
        offset+=port.write(data[offset:])
    while time.monotonic()<deadline:
        for response in codec.feed(port.read(2048)):
            if response.kind==frame.kind|0x80 and response.sequence==frame.sequence:
                return response
    raise TimeoutError('USB reply timeout')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--uid',required=True);p.add_argument('--package',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True);p.add_argument('--wait',type=int,default=60)
    args=p.parse_args();uid=bytes.fromhex(args.uid)
    raw=args.package.read_bytes();package=unpack(raw)
    import serial
    from serial.tools.list_ports import comports
    deadline=time.monotonic()+args.wait;selected=None
    print('Waiting for New Deviation TX15 Updater USB CDC...',flush=True)
    while time.monotonic()<deadline:
        devices=[v for v in comports() if v.vid==0xcafe and v.pid==0x4015
                 and (v.serial_number or '').lower()==args.uid.lower()]
        if len(devices)==1:selected=devices[0];break
        time.sleep(.25)
    if selected is None:raise RuntimeError('Reviewed TX15 USB identity was not enumerated')
    with open_cdc_port(serial,selected.device) as port:
        codec=FrameCodec();hello=exchange(port,codec,Frame(1,0,0,0))
        info=DeviceInfo.from_frame(hello)
        if info.uid!=uid or not info.read_only or info.flags!=1:
            raise RuntimeError('Not the exact read-only RAM probe; no transfer performed')
        print('HELLO verified:',selected.device,info.uid.hex(),'read_only=True',flush=True)
        session=info.session;seq=1
        def send(kind,payload=b'',offset=0):
            nonlocal seq
            response=exchange(port,codec,Frame(kind,session,seq,offset,payload))
            seq+=1
            if response.session!=session:raise RuntimeError('USB session changed during acceptance')
            return DeviceStatus.from_payload(response.payload)
        if send(2,raw[:128]).error:raise RuntimeError('BEGIN rejected')
        for offset in range(0,len(package.image),1024):
            status=send(3,package.image[offset:offset+1024],offset)
            if status.error:raise RuntimeError('DATA rejected')
            if offset%65536==0:print('RAM received',status.received,'/',status.total,flush=True)
        status=send(4)
        if status.state!=3 or status.error:raise RuntimeError('Complete RAM package did not reach READY')
        # HELLO confirmed read_only before this negative COMMIT test. The RAM
        # binary contains no NOR writer, and must return READ_ONLY (8).
        rejected=send(7,uid+struct.pack('<2I',len(package.image),package.image_crc))
        if rejected.error!=8 or rejected.state!=3:raise RuntimeError('Read-only COMMIT was not rejected')
        report=dict(schema=1,mode='usb-readonly-ram-acceptance',port=selected.device,
                    uid=uid.hex(),session=session,image_bytes=len(package.image),
                    ready_verified=True,commit_rejected_read_only=True,
                    clock_sync_observed='inspect SWD mailbox separately',flash_mutation_commands=0)
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        print(json.dumps(report),flush=True)


if __name__=='__main__':main()

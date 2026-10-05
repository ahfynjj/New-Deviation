"""TX15 first install/recovery. Default is an offline checklist, never writes.

--rehearse uses only pinned RAM code and read-only Flash access; all hardware
outcomes stay halted. --install/--recover require exact device-bound approval.
Do not execute a write command until the human approves its concrete checklist.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import struct
import tempfile
import queue
import threading
import sys
import install_kit
import install_entry
from recovery_context import RecoveryContext,UID_BASE

ROOT=Path(__file__).resolve().parents[2]
PROBE_UID='B8EFB57613B198CA10834F0545435DBB'

def power_held_gate(seconds):
    if not sys.stdin.isatty():raise RuntimeError('Interactive terminal required for power-held confirmation')
    responses=queue.Queue()
    def receive():
        try:responses.put(input('POWER HELD? type HELD and press Enter: '))
        except BaseException as exc:responses.put(exc)
    threading.Thread(target=receive,daemon=True).start()
    try:answer=responses.get(timeout=seconds)
    except queue.Empty:raise TimeoutError('No power-held confirmation; no RAM/Flash load')
    if isinstance(answer,BaseException):raise RuntimeError('Power-held input unavailable') from answer
    if answer.strip()!='HELD':raise ValueError('Expected exact HELD confirmation; no RAM/Flash load')

def open_probe(frequency=50000):
    from pyocd.core.helpers import ConnectHelper
    s=ConnectHelper.session_with_chosen_probe(unique_id=PROBE_UID,blocking=False,auto_open=False,
        options={'target_override':'cortex_m','frequency':frequency,'connect_mode':'attach',
                 'auto_unlock':False,'no_config':True,'resume_on_disconnect':False})
    if s is None:raise RuntimeError('PWLINK2 unavailable')
    try:s.open(init_board=False)
    except BaseException:
        s.close();raise
    return s

def identify():
    from pyocd.probe.debug_probe import DebugProbe
    from pyocd.coresight.minimal_mem_ap import MinimalMemAP
    with install_entry.lease(Path(tempfile.gettempdir()),'new-deviation-tx15-pwlink2.lock'):
        s=open_probe()
        try:
            dp=s.target.dp;dp.connect(DebugProbe.Protocol.SWD)
            ap=MinimalMemAP(dp);ap.init()
            if ap.read32(0x5c001000)&0xfff!=0x450 or ap.read32(0x1ff1e880)&0xffff!=128:raise RuntimeError('Unexpected MCU')
            uid=b''.join(struct.pack('<I',ap.read32(UID_BASE+i)) for i in (0,4,8)).hex()
            if not install_kit.uid_valid(uid):raise RuntimeError('Invalid MCU UID')
            return dict(schema=1,device_uid=uid,mode='non-halting-read-only-uid',flash_mutation_commands=0)
        finally:s.close()

def main(argv=None,kit_reader=install_kit.read):
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_mutually_exclusive_group()
    for mode in ('identify','prepare','rehearse','install','recover'):modes.add_argument('--'+mode,action='store_true')
    parser.add_argument('--kit',type=Path,default=ROOT/'local/tx15-hardware/install/kit')
    parser.add_argument('--device-uid')
    parser.add_argument('--approval')
    parser.add_argument('--arm',action='store_true')
    parser.add_argument('--press-window',type=int,default=300)
    parser.add_argument('--swd-frequency',type=int,choices=(50000,500000),default=50000)
    args=parser.parse_args(argv)
    if not 60<=args.press_window<=600:parser.error('Press window must be 60..600 seconds')
    if args.identify:
        if args.arm or args.approval:parser.error('Identify is read-only, no approval/arm needed')
        try:info=identify()
        except Exception as exc:
            print('Read-only UID unavailable: '+type(exc).__name__+': '+str(exc));return 1
        folder=ROOT/'local/tx15-hardware/install';folder.mkdir(parents=True,exist_ok=True)
        (folder/'device-identity.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf8')
        print(json.dumps(info,indent=2));return 0
    if args.prepare:
        if args.approval or args.arm:parser.error('Prepare opens no device')
        install_kit.prepare(ROOT,args.kit,args.device_uid)
    kit=kit_reader(args.kit)
    if not (args.rehearse or args.install or args.recover):
        checklist=install_kit.checklist(kit)
        (kit.folder/'checklist.json').write_text(json.dumps(checklist,indent=2)+'\n',encoding='utf8')
        print(json.dumps(checklist,indent=2));return 0
    if not args.arm:parser.error('Hardware operation requires --arm')
    if not sys.stdin.isatty():parser.error('Hardware entry needs an interactive terminal; no reset attempted')
    if args.rehearse and args.approval:parser.error('Rehearsal cannot accept write approval')
    holder=[]
    def opener():
        context=RecoveryContext(open_probe(args.swd_frequency),wait=args.press_window,ready_gate=lambda:power_held_gate(args.press_window))
        holder.append(context);return context
    result={'utc':datetime.now(timezone.utc).isoformat(),'swd_frequency_hz':args.swd_frequency,'mode':'rehearse' if args.rehearse else 'install' if args.install else 'recover'}
    try:
        if args.rehearse:report=install_entry.rehearse(kit,opener)
        else:report=install_entry.authorized_run(kit,result['mode'],args.approval,opener)
        result.update(status='verified-halted',report=report)
        print('VERIFIED; CPU KEPT HALTED. Disconnect debugger USB, disconnect radio battery for 5 seconds, reconnect and power on.',flush=True)
        return 0
    except BaseException as exc:
        result.update(status='failed-no-resume',error=type(exc).__name__+': '+str(exc))
        print(result['error'],flush=True)
        print('NO AUTOMATIC RESET/RESUME. If a write intent exists, recover before attempting normal boot.',flush=True)
        return 1
    finally:
        if holder:result['report']=holder[0].report
        folder=ROOT/'local/hardware-session';folder.mkdir(parents=True,exist_ok=True)
        path=folder/('flash-entry-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
        path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
        print('Saved',path,flush=True)

if __name__=='__main__':raise SystemExit(main())

"""One-time resident USB boot install. Default offline; capture is read-only.

Install/recover reuse the bounded SWD transaction with a new approval domain.
The installed application is frozen unchanged; no pending feature app is used.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile
import boot_elf,boot_image,elrs_update,install_kit,install_entry,native_update,status_update
from flash_transaction import Transaction,sha

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_BASELINE=ROOT/'local/tx15-hardware/install/calibration-kit'
DEFAULT_KIT=ROOT/'local/tx15-hardware/install/usb-boot-kit'
EXTRA=('boot.elf','boot-build.json','baseline-installed.json','capture.json')

class USBInstallKit(install_kit.Kit):
    def approval(self,action):
        if action not in ('install','recover'):raise ValueError('Unknown action')
        return sha(('tx15-usb-boot-update-v1:'+action+':'+self.plan.seal+':'+self.uid).encode())

def candidate(root):
    folder=Path(root)/'local/tx15-hardware/boot-usb'
    elf=(folder/'tx15-boot-usb.elf').read_bytes();raw=(folder/'tx15-boot-usb.bin').read_bytes()
    metadata=(folder/'build.json').read_bytes();validate_boot(elf,raw,json.loads(metadata))
    return elf,raw,metadata

def validate_boot(elf,raw,metadata):
    layout=boot_elf.parse(elf)
    if raw!=boot_elf.binary(elf) or metadata.get('schema')!=1 \
        or metadata.get('mode')!='resident-usb-update-candidate' \
        or metadata.get('boot_api')!=1 or metadata.get('settings_abi')!=1 \
        or metadata.get('hardware_installation_verified') is not False \
        or metadata.get('elf_sha256')!=sha(elf) or metadata.get('bin_sha256')!=sha(raw) \
        or metadata.get('layout')!=layout:raise ValueError('Invalid isolated USB boot candidate')

def prepare(root,folder,baseline_folder,internal,external):
    b,journal=status_update.baseline(root,baseline_folder)
    status_update.verify_old(b,internal,external)
    elf,raw,metadata=candidate(root)
    boot=raw+b'\xff'*((-len(raw))%32)
    # Preserve the installed payload exactly, including its frozen page padding.
    payload=b.plan.payload
    if len(payload)>0xf0000 or external[:len(payload)]!=payload:
        raise ValueError('Installed application differs from baseline')
    capture=dict(schema=1,device_uid=b.uid,internal_sha256=sha(internal),external_sha256=sha(external),
                 settings_sha256=sha(external[0xf0000:]),flash_mutation_commands=0)
    files=dict(zip(install_kit.FILES,(boot,payload,internal,external,
        (b.folder/'reader.elf').read_bytes(),b.reader)))
    files.update({'boot.elf':elf,'boot-build.json':metadata,'baseline-installed.json':journal.read_bytes(),
                  'capture.json':(json.dumps(capture,sort_keys=True)+'\n').encode()})
    plan=Transaction(boot,payload,internal,external)
    if plan.erase_bytes>0xf0000:raise ValueError('SWD install would overlap model/calibration region')
    folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir()
    shutil.copytree(b.folder,folder/'baseline-kit',ignore=shutil.ignore_patterns(
        'active.json','transaction-*','session.lock','checklist.json'))
    for name,data in files.items():(folder/name).write_bytes(data)
    manifest=dict(schema=1,kind='resident-usb-boot-from-native',board=b.manifest['board'],device_uid=b.uid,
        rf_enabled=True,persistent_settings=True,application_unchanged=True,preserve_internal_loader=False,
        flash_write_authorized=False,settings_region={'offset':0xf0000,'bytes':65536,'preserve_on_update':True},
        files={name:sha(data) for name,data in files.items()},transaction=plan.manifest())
    (folder/'kit.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    return read(folder)

def read(folder):
    folder=Path(folder);m=json.loads((folder/'kit.json').read_text(encoding='utf8'))
    b=status_update.read_native(folder/'baseline-kit')
    if m.get('schema')!=1 or m.get('kind')!='resident-usb-boot-from-native' \
        or m.get('board')!=b.manifest['board'] or m.get('device_uid')!=b.uid \
        or any(m.get(name) is not True for name in ('rf_enabled','persistent_settings','application_unchanged')) \
        or m.get('preserve_internal_loader') is not False or m.get('flash_write_authorized') is not False \
        or m.get('settings_region')!={'offset':0xf0000,'bytes':65536,'preserve_on_update':True} \
        or set(m.get('files',{}))!=set(install_kit.FILES+EXTRA):raise ValueError('Invalid USB boot kit')
    files={name:(folder/name).read_bytes() for name in m['files']}
    if any(sha(data)!=m['files'][name] for name,data in files.items()):raise ValueError('USB boot kit hash mismatch')
    native_update.installed_record(folder/'baseline-installed.json',b)
    internal,external=files['original-internal.bin'],files['original-external.bin']
    status_update.verify_old(b,internal,external)
    raw=boot_elf.binary(files['boot.elf']);validate_boot(files['boot.elf'],raw,json.loads(files['boot-build.json']))
    if files['boot.bin']!=raw+b'\xff'*((-len(raw))%32) or files['payload.bin']!=b.plan.payload \
        or files['payload.bin']!=external[:len(files['payload.bin'])] \
        or files['reader.bin']!=b.reader or files['reader.elf']!=(b.folder/'reader.elf').read_bytes():
        raise ValueError('USB boot/installed app/reader differs from frozen inputs')
    c=json.loads(files['capture.json'])
    if c!=dict(schema=1,device_uid=b.uid,internal_sha256=sha(internal),external_sha256=sha(external),
               settings_sha256=sha(external[0xf0000:]),flash_mutation_commands=0):raise ValueError('Snapshot differs')
    plan=Transaction(*(files[name] for name in install_kit.FILES[:4]))
    if plan.erase_bytes>0xf0000 or plan.manifest()!=m['transaction']:raise ValueError('USB transaction differs')
    return USBInstallKit(folder,plan,b.reader,b.entry,b.uid,m)

def checklist(kit):
    result=install_kit.checklist(kit)
    result.update(application_unchanged=True,usb_update_api=1,approval_domain='tx15-usb-boot-update-v1',
        limitations=['Resident normal boot/EXIT/recovery entry and USB Flash update acceptance pending'],
        install_note='Rewrites the SAME installed external app prefix, then replaces the internal 128KiB bank')
    return result

def reuse_snapshot(root,folder,baseline_folder,snapshot_folder):
    """Reuse an already validated snapshot; installation still compares live bytes.

    This never opens a device or claims the saved settings are current. If any
    byte has changed, the existing install transaction refuses before erasing.
    """
    snapshot=status_update.read_native(snapshot_folder)
    baseline,_=status_update.baseline(root,baseline_folder)
    if snapshot.uid!=baseline.uid:raise ValueError('Snapshot belongs to another device')
    return prepare(root,folder,baseline_folder,snapshot.plan.original_internal,snapshot.plan.original_external)

def export_recovery(kit,destination):
    destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(kit.folder.rglob('*')):
            if p.is_file() and p.name not in ('session.lock','active.json') and not p.name.startswith('transaction-'):
                z.write(p,p.relative_to(kit.folder).as_posix())
    with tempfile.TemporaryDirectory(prefix='TX15 recovery verify ') as tmp:
        with zipfile.ZipFile(destination) as z:
            if z.testzip():raise ValueError('Recovery archive CRC failure')
            z.extractall(tmp) # Archive members created exclusively from this verified kit.
        recovered=read(tmp)
        if recovered.plan!=kit.plan or recovered.uid!=kit.uid:raise ValueError('Recovery archive differs')
    return destination

def capture(folder,baseline_folder,frequency=500000,window=600):
    import flash_install
    if not sys.stdin.isatty():raise ValueError('Interactive terminal required')
    if Path(folder).exists():raise FileExistsError(folder)
    b,_=status_update.baseline(ROOT,baseline_folder);candidate(ROOT) # Before probe opening/reset.
    context=None;report=dict(utc=datetime.now(timezone.utc).isoformat(),mode='usb-boot-snapshot',flash_mutation_commands=0)
    try:
        with install_entry.lease(Path(tempfile.gettempdir()),'new-deviation-tx15-pwlink2.lock'):
            context=flash_install.RecoveryContext(flash_install.open_probe(frequency),wait=window,
                ready_gate=lambda:flash_install.power_held_gate(window))
            try:
                observed=context.enter(b);backend=context.backend(read_only=True)
                if backend.check_device()!=observed:raise ValueError('Flash observations differ')
                internal=backend.read_internal(0x08000000,131072);external=backend.read_external(0,1048576)
                kit=prepare(ROOT,folder,baseline_folder,internal,external)
                archive=export_recovery(kit,Path(folder).with_suffix('.recovery.zip'))
                report.update(status='snapshot-verified',checklist=checklist(kit),recovery_archive=str(archive))
            finally:install_entry.finish_context(context)
    except BaseException as exc:
        report.update(status='failed-no-resume',error=type(exc).__name__+': '+str(exc));raise
    finally:
        if context:report['report']=context.report
        logs=ROOT/'local/hardware-session';logs.mkdir(parents=True,exist_ok=True)
        path=logs/('usb-boot-snapshot-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
        path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print('Saved',path,flush=True)
    print('SNAPSHOT VERIFIED; CPU HALTED. Disconnect both USB cables and battery for 5 seconds, then power on.',flush=True)
    return 0

def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if '--reuse-snapshot' in args:
        p=argparse.ArgumentParser(description='Offline kit using an existing verified snapshot; no device opened')
        p.add_argument('--reuse-snapshot',action='store_true')
        p.add_argument('--snapshot',type=Path,required=True)
        p.add_argument('--baseline',type=Path,default=DEFAULT_BASELINE)
        p.add_argument('--kit',type=Path,default=DEFAULT_KIT)
        a=p.parse_args(args)
        kit=reuse_snapshot(ROOT,a.kit,a.baseline,a.snapshot)
        archive=export_recovery(kit,Path(a.kit).with_suffix('.recovery.zip'))
        print(json.dumps(dict(checklist=checklist(kit),existing_snapshot=str(a.snapshot),
            recovery_archive=str(archive),live_snapshot_verified=False),indent=2))
        return 0
    if '--capture' in args:
        p=argparse.ArgumentParser(description=__doc__)
        p.add_argument('--capture',action='store_true');p.add_argument('--arm',action='store_true')
        p.add_argument('--baseline',type=Path,default=DEFAULT_BASELINE);p.add_argument('--kit',type=Path,default=DEFAULT_KIT)
        p.add_argument('--press-window',type=int,default=600)
        p.add_argument('--swd-frequency',type=int,choices=(50000,500000),default=500000)
        a=p.parse_args(args)
        if not a.arm or not 60<=a.press_window<=600:p.error('Capture needs --arm and bounded window')
        return capture(a.kit,a.baseline,a.swd_frequency,a.press_window)
    if '--prepare' in args:raise ValueError('Use read-only --capture --arm for the latest model/calibration snapshot')
    if '--kit' not in args:args+=['--kit',str(DEFAULT_KIT)]
    if not any(flag in args for flag in ('--install','--recover','--rehearse')):
        p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kit',type=Path,required=True)
        kit=read(p.parse_args(args).kit);print(json.dumps(checklist(kit),indent=2));return 0
    import flash_install
    return flash_install.main(args,kit_reader=read)

if __name__=='__main__':raise SystemExit(main())

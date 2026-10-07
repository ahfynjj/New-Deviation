"""Status-display update from installed ELRS, preserving a fresh model snapshot.
--capture --arm is strictly read-only Flash; install needs a frozen approval.
"""
import argparse,json,shutil,sys,tempfile
from pathlib import Path
from datetime import datetime,timezone
import elrs_update,native_update,install_kit,install_entry,flash_install,boot_image
from flash_transaction import Transaction,sha
ROOT=Path(__file__).resolve().parents[2]
DEFAULT_KIT=ROOT/'local/tx15-hardware/install/status-kit'
EXTRA=elrs_update.EXTRA+('capture.json',)
class StatusKit(install_kit.Kit):
 def approval(self,action):
  if action not in ('install','recover'):raise ValueError('Unknown action')
  return sha(('tx15-status-update-v1:'+action+':'+self.plan.seal+':'+self.uid).encode())
def read_native(folder,depth=0):
 if depth>8:raise ValueError('Native baseline chain too deep')
 kind=json.loads((Path(folder)/'kit.json').read_text(encoding='utf8')).get('kind')
 if kind=='elrs-update-from-controls':return elrs_update.read(folder)
 if kind in ('status-update-from-elrs','status-update-from-native'):return read(folder,depth)
 raise ValueError('Unsupported native baseline')
def baseline(root,folder=None):
 b=read_native(folder or Path(root)/'local/tx15-hardware/install/elrs-kit')
 install_entry.active(b)
 pointer=json.loads((b.folder/'active.json').read_text(encoding='utf8'))
 path=b.folder/pointer['journal'];native_update.installed_record(path,b)
 return b,path
def verify_old(b,internal,external):
 oldi,olde=native_update.baseline_images(b)
 if len(internal)!=131072 or len(external)!=1048576 or internal!=oldi or external[:0xf0000]!=olde[:0xf0000]:
  raise ValueError('Unknown installed loader/application; no write')
def prepare(root,folder,internal,external,baseline_folder=None):
 root,folder=Path(root),Path(folder);b,journal=baseline(root,baseline_folder)
 verify_old(b,internal,external)
 appdir=root/'local/tx15-hardware/app-standalone'
 boot=(root/'local/tx15-hardware/boot/tx15-boot.elf').read_bytes()
 app=(appdir/'tx15-app.elf').read_bytes();meta=(appdir/'build.json').read_bytes()
 payload=(appdir/'tx15-app.nd15').read_bytes()
 newi,newe=elrs_update.candidate(boot,app,payload,json.loads(meta))
 capture=dict(schema=1,device_uid=b.uid,internal_sha256=sha(internal),external_sha256=sha(external),
  settings_sha256=sha(external[0xf0000:]),flash_mutation_commands=0)
 files=dict(zip(install_kit.FILES,(newi,newe,internal,external,(b.folder/'reader.elf').read_bytes(),b.reader)))
 files.update({'app.elf':app,'boot.elf':boot,'build.json':meta,'baseline-installed.json':journal.read_bytes(),
  'capture.json':(json.dumps(capture,sort_keys=True)+'\n').encode()})
 plan=Transaction(newi,newe,internal,external)
 folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir()
 shutil.copytree(b.folder,folder/'baseline-kit',ignore=shutil.ignore_patterns('active.json','transaction-*','session.lock','checklist.json'))
 for name,data in files.items():(folder/name).write_bytes(data)
 manifest=dict(schema=1,kind='status-update-from-native',board=b.manifest['board'],device_uid=b.uid,
  rf_enabled=True,persistent_settings=True,preserve_internal_loader=True,flash_write_authorized=False,
  settings_region={'offset':983040,'bytes':65536,'preserve_on_update':True},
  files={name:sha(data) for name,data in files.items()},transaction=plan.manifest())
 (folder/'kit.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
 return read(folder)
def read(folder,depth=0):
 folder=Path(folder);m=json.loads((folder/'kit.json').read_text(encoding='utf8'));b=read_native(folder/'baseline-kit',depth+1)
 if (m.get('schema')!=1 or m.get('kind') not in ('status-update-from-elrs','status-update-from-native') or m.get('board')!=b.manifest['board']
  or m.get('device_uid')!=b.uid or m.get('rf_enabled') is not True or m.get('persistent_settings') is not True
  or m.get('preserve_internal_loader') is not True or m.get('flash_write_authorized') is not False
  or m.get('settings_region')!={'offset':983040,'bytes':65536,'preserve_on_update':True}
  or set(m.get('files',{}))!=set(install_kit.FILES+EXTRA)):raise ValueError('Invalid status kit')
 files={n:(folder/n).read_bytes() for n in m['files']}
 if any(sha(v)!=m['files'][n] for n,v in files.items()):raise ValueError('Status kit hash mismatch')
 native_update.installed_record(folder/'baseline-installed.json',b)
 verify_old(b,files['original-internal.bin'],files['original-external.bin'])
 newi,newe=elrs_update.candidate(files['boot.elf'],files['app.elf'],boot_image.pack(files['app.elf']),json.loads(files['build.json']))
 if (files['boot.bin']!=newi or files['payload.bin']!=newe or files['reader.bin']!=b.reader
  or files['reader.elf']!=(b.folder/'reader.elf').read_bytes()):raise ValueError('Status candidate/reader differs')
 c=json.loads(files['capture.json'])
 if c!=dict(schema=1,device_uid=b.uid,internal_sha256=sha(files['original-internal.bin']),external_sha256=sha(files['original-external.bin']),
  settings_sha256=sha(files['original-external.bin'][0xf0000:]),flash_mutation_commands=0):raise ValueError('Snapshot metadata differs')
 plan=Transaction(*(files[n] for n in install_kit.FILES[:4]))
 if plan.manifest()!=m['transaction']:raise ValueError('Status transaction differs')
 return StatusKit(folder,plan,b.reader,b.entry,b.uid,m)
def capture(folder,frequency=500000,window=600,baseline_folder=None):
 if not sys.stdin.isatty():raise ValueError('Interactive terminal required')
 if Path(folder).exists():raise FileExistsError(folder)
 b,_=baseline(ROOT,baseline_folder)
 # Validate new image before any reset; it will be checked again while freezing.
 a=ROOT/'local/tx15-hardware/app-standalone'
 elrs_update.candidate((ROOT/'local/tx15-hardware/boot/tx15-boot.elf').read_bytes(),
  (a/'tx15-app.elf').read_bytes(),(a/'tx15-app.nd15').read_bytes(),json.loads((a/'build.json').read_text(encoding='utf8')))
 context=None;report=dict(utc=datetime.now(timezone.utc).isoformat(),mode='status-snapshot',flash_mutation_commands=0)
 try:
  with install_entry.lease(Path(tempfile.gettempdir()),'new-deviation-tx15-pwlink2.lock'):
   context=flash_install.RecoveryContext(flash_install.open_probe(frequency),wait=window,
    ready_gate=lambda:flash_install.power_held_gate(window))
   try:
    observation=context.enter(b);backend=context.backend(read_only=True)
    if backend.check_device()!=observation:raise ValueError('Flash observations differ')
    internal=backend.read_internal(0x08000000,131072);external=backend.read_external(0,1048576)
    verify_old(b,internal,external);kit=prepare(ROOT,folder,internal,external,baseline_folder)
    report.update(status='snapshot-verified',checklist=install_kit.checklist(kit))
   finally:install_entry.finish_context(context)
 except BaseException as exc:
  report.update(status='failed-no-resume',error=type(exc).__name__+': '+str(exc));raise
 finally:
  if context:report['report']=context.report
  logs=ROOT/'local/hardware-session';logs.mkdir(parents=True,exist_ok=True)
  path=logs/('status-snapshot-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
  path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8');print('Saved',path,flush=True)
 print('SNAPSHOT VERIFIED; CPU HALTED. Disconnect debugger USB and battery for 5 seconds, then power on.',flush=True)
 print(json.dumps(report['checklist'],indent=2));return 0
def main(argv=None):
 args=list(sys.argv[1:] if argv is None else argv)
 if '--capture' in args:
  p=argparse.ArgumentParser();p.add_argument('--capture',action='store_true');p.add_argument('--arm',action='store_true')
  p.add_argument('--baseline',type=Path);p.add_argument('--kit',type=Path,default=DEFAULT_KIT);p.add_argument('--press-window',type=int,default=600)
  p.add_argument('--swd-frequency',type=int,choices=(50000,500000),default=500000);a=p.parse_args(args)
  if not a.arm or not 60<=a.press_window<=600:p.error('Capture requires --arm and bounded window')
  return capture(a.kit,a.swd_frequency,a.press_window,a.baseline)
 if '--prepare' in args:raise ValueError('Use read-only --capture --arm to freeze live models')
 if '--kit' not in args:args+=['--kit',str(DEFAULT_KIT)]
 return flash_install.main(args,kit_reader=read)
if __name__=='__main__':raise SystemExit(main())

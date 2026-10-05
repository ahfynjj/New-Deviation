"""Frozen ELRS candidate update from the verified controls install only.
Default is offline. Hardware entry preserves loader/settings and checks all old bytes.
"""
import json,shutil,sys
from pathlib import Path
import install_kit,install_entry,native_update,boot_elf,boot_image,app_image
from flash_transaction import Transaction,sha
ROOT=Path(__file__).resolve().parents[2]
DEFAULT_KIT=ROOT/'local/tx15-hardware/install/elrs-kit'
EXTRA=('app.elf','boot.elf','build.json','baseline-installed.json')
class ElrsKit(install_kit.Kit):
 def approval(self,action):
  if action not in ('install','recover'):raise ValueError('Unknown action')
  return sha(('tx15-elrs-update-v1:'+action+':'+self.plan.seal+':'+self.uid).encode())
def candidate(boot,app,payload,metadata):
 boot_elf.parse(boot)
 internal=boot_elf.binary(boot);internal+=b'\xff'*((-len(internal))%32)
 if sha(internal)!=install_kit.BOOT_SHA:raise ValueError('ELRS update cannot replace native loader')
 if (metadata.get('schema')!=1 or metadata.get('mode')!='standalone-elrs-candidate'
  or metadata.get('rf_enabled') is not True or metadata.get('persistent_settings') is not True
  or metadata.get('elf_sha256')!=sha(app) or metadata.get('payload_sha256')!=sha(payload)):
  raise ValueError('Require exact standalone ELRS/persistence metadata')
 if boot_image.unpack(payload)!=app_image.parse(app):raise ValueError('ELRS payload differs from ELF')
 external=payload+b'\xff'*((-len(payload))%256)
 if (len(external)+4095)&~4095>0xf0000:raise ValueError('Candidate overlaps settings region')
 return internal,external
def prepare(root,folder):
 root,folder=Path(root),Path(folder)
 baseline=native_update.read(root/'local/tx15-hardware/install/controls-kit')
 install_entry.active(baseline)
 pointer=json.loads((baseline.folder/'active.json').read_text(encoding='utf8'))
 journal=baseline.folder/pointer['journal'];native_update.installed_record(journal,baseline)
 appdir=root/'local/tx15-hardware/app-standalone'
 boot=(root/'local/tx15-hardware/boot/tx15-boot.elf').read_bytes()
 app=(appdir/'tx15-app.elf').read_bytes();payload=(appdir/'tx15-app.nd15').read_bytes()
 meta=(appdir/'build.json').read_bytes()
 internal,external=candidate(boot,app,payload,json.loads(meta))
 old_internal,old_external=native_update.baseline_images(baseline)
 contents=dict(zip(install_kit.FILES,(internal,external,old_internal,old_external,
  (baseline.folder/'reader.elf').read_bytes(),baseline.reader)))
 contents.update({'app.elf':app,'boot.elf':boot,'build.json':meta,'baseline-installed.json':journal.read_bytes()})
 plan=Transaction(internal,external,old_internal,old_external)
 folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir()
 shutil.copytree(baseline.folder,folder/'baseline-kit',ignore=shutil.ignore_patterns('active.json','transaction-*','session.lock','checklist.json'))
 for name,data in contents.items():(folder/name).write_bytes(data)
 manifest=dict(schema=1,kind='elrs-update-from-controls',board=baseline.manifest['board'],
  device_uid=baseline.uid,rf_enabled=True,persistent_settings=True,preserve_internal_loader=True,
  settings_region={'offset':983040,'bytes':65536,'preserve_on_update':True},
  flash_write_authorized=False,files={name:sha(data) for name,data in contents.items()},transaction=plan.manifest())
 (folder/'kit.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
 read(folder);return manifest
def read(folder):
 folder=Path(folder);manifest=json.loads((folder/'kit.json').read_text(encoding='utf8'))
 baseline=native_update.read(folder/'baseline-kit')
 if (manifest.get('schema')!=1 or manifest.get('kind')!='elrs-update-from-controls'
  or manifest.get('board')!=baseline.manifest['board'] or manifest.get('device_uid')!=baseline.uid
  or manifest.get('rf_enabled') is not True or manifest.get('persistent_settings') is not True
  or manifest.get('preserve_internal_loader') is not True or manifest.get('flash_write_authorized') is not False
  or manifest.get('settings_region')!={'offset':983040,'bytes':65536,'preserve_on_update':True}
  or set(manifest.get('files',{}))!=set(install_kit.FILES+EXTRA)):
  raise ValueError('Invalid frozen ELRS kit')
 contents={name:(folder/name).read_bytes() for name in manifest['files']}
 if any(sha(data)!=manifest['files'][name] for name,data in contents.items()):raise ValueError('ELRS kit digest mismatch')
 native_update.installed_record(folder/'baseline-installed.json',baseline)
 internal,external=candidate(contents['boot.elf'],contents['app.elf'],boot_image.pack(contents['app.elf']),json.loads(contents['build.json']))
 old_internal,old_external=native_update.baseline_images(baseline)
 expected=dict(zip(install_kit.FILES,(internal,external,old_internal,old_external,
  (baseline.folder/'reader.elf').read_bytes(),baseline.reader)))
 if any(contents[name]!=data for name,data in expected.items()):raise ValueError('ELRS images differ from known controls baseline/candidate')
 plan=Transaction(*(contents[name] for name in install_kit.FILES[:4]))
 if plan.manifest()!=manifest['transaction']:raise ValueError('ELRS transaction differs from frozen files')
 return ElrsKit(folder,plan,baseline.reader,baseline.entry,baseline.uid,manifest)
def main(argv=None):
 args=list(sys.argv[1:] if argv is None else argv)
 if '--prepare-update' in args:
  if args!=['--prepare-update']:raise ValueError('Prepare update is offline only')
  prepare(ROOT,DEFAULT_KIT);print(json.dumps(install_kit.checklist(read(DEFAULT_KIT)),indent=2));return 0
 if '--prepare' in args:raise ValueError('Use --prepare-update; first install remains fixed')
 if '--kit' not in args:args+=['--kit',str(DEFAULT_KIT)]
 import flash_install
 return flash_install.main(args,kit_reader=read)
if __name__=='__main__':raise SystemExit(main())

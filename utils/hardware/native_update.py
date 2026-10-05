"""Freeze/update the RF-off application from the verified first native install.

Default prints an offline checklist. This deliberately supports that fixed
baseline only; it cannot overwrite an unknown later app or replace the loader.
Hardware install/recovery use the same reset-catch, full comparison, journal,
bounded backend and halted exit as the first install.
"""
import json
from pathlib import Path
import shutil
import sys
import install_kit
import install_entry
from flash_journal import Journal
from flash_transaction import Transaction,sha
from install_plan import build_plan
import boot_elf

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_KIT=ROOT/'local/tx15-hardware/install/controls-kit'
EXTRA=('app.elf','boot.elf','build.json','baseline-installed.json')

class NativeUpdateKit(install_kit.Kit):
    def approval(self,action):
        if action not in ('install','recover'):raise ValueError('Unknown action')
        return sha(('tx15-native-update-v1:'+action+':'+self.plan.seal+':'+self.uid).encode())

def baseline_images(first):
    internal=first.plan.boot+b'\xff'*(131072-len(first.plan.boot))
    external=(first.plan.payload+b'\xff'*(first.plan.erase_bytes-len(first.plan.payload))
              +first.plan.original_external[first.plan.erase_bytes:])
    return internal,external

def installed_record(path,first):
    record=Journal.read(path)
    if (record['plan_seal']!=first.plan.seal or record['action']!='install'
        or record['state']!='installed' or record['checkpoints']!=['external','internal']):
        raise ValueError('Require the verified first native install as baseline')
    return record

def candidate(boot,app,payload,metadata):
    _,internal,external=build_plan(boot,boot_elf.binary(boot),app,payload,metadata)
    if sha(internal)!=install_kit.BOOT_SHA:raise ValueError('Native update cannot change the installed loader')
    return internal,external

def prepare(root,folder):
    root,folder=Path(root),Path(folder)
    first=install_kit.read(root/'local/tx15-hardware/install/kit')
    pointer=json.loads((first.folder/'active.json').read_text(encoding='utf8'))
    # Validate pointer with the existing path and plan guards before reading it.
    install_entry.active(first)
    journal=first.folder/pointer['journal'];installed_record(journal,first)
    appfolder=root/'local/tx15-hardware/app-standalone'
    boot=(root/'local/tx15-hardware/boot/tx15-boot.elf').read_bytes()
    app=(appfolder/'tx15-app.elf').read_bytes()
    metadata=json.loads((appfolder/'build.json').read_text(encoding='utf8'))
    payload=(appfolder/'tx15-app.nd15').read_bytes()
    internal,external=candidate(boot,app,payload,metadata)
    old_internal,old_external=baseline_images(first)
    contents=dict(zip(install_kit.FILES,(internal,external,old_internal,old_external,
        (first.folder/'reader.elf').read_bytes(),first.reader)))
    contents.update({'boot.elf':boot,'app.elf':app,
        'build.json':(appfolder/'build.json').read_bytes(),'baseline-installed.json':journal.read_bytes()})
    plan=Transaction(internal,external,old_internal,old_external)
    folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir()
    shutil.copytree(first.folder,folder/'baseline-kit',
        ignore=shutil.ignore_patterns('active.json','transaction-*','session.lock','checklist.json'))
    for name,data in contents.items():(folder/name).write_bytes(data)
    manifest=dict(schema=1,kind='native-app-update-from-first-install',board=first.manifest['board'],
        device_uid=first.uid,rf_enabled=False,preserve_internal_loader=True,
        flash_write_authorized=False,files={name:sha(data) for name,data in contents.items()},
        transaction=plan.manifest())
    (folder/'kit.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    read(folder)
    return manifest

def read(folder):
    folder=Path(folder)
    manifest=json.loads((folder/'kit.json').read_text(encoding='utf8'))
    first=install_kit.read(folder/'baseline-kit')
    if (manifest.get('schema')!=1 or manifest.get('kind')!='native-app-update-from-first-install'
        or manifest.get('board')!=first.manifest['board'] or manifest.get('device_uid')!=first.uid
        or manifest.get('rf_enabled') is not False or manifest.get('flash_write_authorized') is not False
        or manifest.get('preserve_internal_loader') is not True
        or set(manifest.get('files',{}))!=set(install_kit.FILES+EXTRA)):
        raise ValueError('Invalid native update kit')
    contents={name:(folder/name).read_bytes() for name in manifest['files']}
    if any(sha(data)!=manifest['files'][name] for name,data in contents.items()):
        raise ValueError('Native update file digest mismatch')
    installed_record(folder/'baseline-installed.json',first)
    from boot_image import pack
    metadata=json.loads(contents['build.json'].decode('utf8'))
    internal,external=candidate(contents['boot.elf'],contents['app.elf'],pack(contents['app.elf']),metadata)
    old_internal,old_external=baseline_images(first)
    expected=dict(zip(install_kit.FILES,(internal,external,old_internal,old_external,
        (first.folder/'reader.elf').read_bytes(),first.reader)))
    if any(contents[name]!=data for name,data in expected.items()):
        raise ValueError('Update images differ from native baseline/compiled RF-off candidate')
    plan=Transaction(*(contents[name] for name in install_kit.FILES[:4]))
    if plan.manifest()!=manifest['transaction']:raise ValueError('Native update transaction mismatch')
    return NativeUpdateKit(folder,plan,first.reader,first.entry,first.uid,manifest)

def main(argv=None):
    import flash_install
    args=list(sys.argv[1:] if argv is None else argv)
    if '--prepare-update' in args:
        if args!=['--prepare-update']:raise ValueError('Preparation takes no hardware options')
        prepare(ROOT,DEFAULT_KIT)
        return flash_install.main(['--kit',str(DEFAULT_KIT)],kit_reader=read)
    if '--prepare' in args:raise ValueError('Use --prepare-update; do not regenerate the first-install kit')
    if '--kit' not in args:args+=['--kit',str(DEFAULT_KIT)]
    return flash_install.main(args,kit_reader=read)

if __name__=='__main__':raise SystemExit(main())

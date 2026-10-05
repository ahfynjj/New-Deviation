"""Frozen first-install/recovery files. Preparation never opens hardware."""
from dataclasses import dataclass
import json
import re
from pathlib import Path
from flash_transaction import Transaction,load_bundle,sha
from flash_info_bundle import ELF_SHA,BIN_SHA
from check_ram_elf import check
from install_plan import INTERNAL_SHA

EXTERNAL_SLOT_SHA='6f1afac85dd9acaa9e07522f9ace8b4124d68da88df856cb54b1c247dc08b315'
FILES=('boot.bin','payload.bin','original-internal.bin','original-external.bin','reader.elf','reader.bin')
BOOT_SHA='5241eea8b1761243f3aef4be42793027d64b3dc815c8d24d99e53ae03cbb4ef1'
PAYLOAD_SHA='085a9e98960aaa343aeb843cfa927263a48f727ba271ef8ce209c86b433e1546'

def uid_valid(uid):
    return isinstance(uid,str) and bool(re.fullmatch('[0-9a-f]{24}',uid)) and uid not in ('00'*12,'ff'*12)

@dataclass(frozen=True)
class Kit:
    folder:Path
    plan:Transaction
    reader:bytes
    entry:int
    uid:str
    manifest:dict
    def approval(self,action):
        if action not in ('install','recover'):raise ValueError('Unknown action')
        return sha(('tx15-first-install-v1:'+action+':'+self.plan.seal+':'+self.uid).encode())

def prepare(root,folder,uid):
    if not uid_valid(uid):raise ValueError('A nonzero, lowercase 96-bit MCU UID is required')
    root,folder=Path(root),Path(folder)
    plan=load_bundle(root)
    from flash_info_bundle import validate
    validate(root)
    contents=dict(zip(FILES,(plan.boot,plan.payload,plan.original_internal,plan.original_external,
        (root/'local/tx15-hardware/flash-info/flash-info.elf').read_bytes(),
        (root/'local/tx15-hardware/flash-info/flash-info.bin').read_bytes())))
    manifest=dict(schema=1,board='TX15 MAX STM32H750',device_uid=uid,
        transaction=plan.manifest(),files={name:sha(data) for name,data in contents.items()},
        flash_write_authorized=False,first_install_rf_enabled=False)
    folder.parent.mkdir(parents=True,exist_ok=True)
    folder.mkdir() # Never replace even an incomplete previous kit.
    for name,data in contents.items():(folder/name).write_bytes(data)
    (folder/'kit.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    kit=read(folder)
    if kit.plan!=plan:raise ValueError('Export verification failed')
    return manifest

def read(folder):
    folder=Path(folder)
    manifest=json.loads((folder/'kit.json').read_text(encoding='utf8'))
    if (manifest.get('schema')!=1 or manifest.get('board')!='TX15 MAX STM32H750'
        or not uid_valid(manifest.get('device_uid')) or manifest.get('flash_write_authorized') is not False
        or manifest.get('first_install_rf_enabled') is not False or set(manifest.get('files',{}))!=set(FILES)):
        raise ValueError('Invalid frozen kit manifest')
    contents={name:(folder/name).read_bytes() for name in FILES}
    if any(sha(data)!=manifest['files'][name] for name,data in contents.items()):raise ValueError('Kit file digest mismatch')
    if sha(contents['boot.bin'])!=BOOT_SHA or sha(contents['payload.bin'])!=PAYLOAD_SHA:
        raise ValueError('Not the reviewed RF-off first-install candidate')
    if sha(contents['original-internal.bin'])!=INTERNAL_SHA or sha(contents['original-external.bin'])!=EXTERNAL_SLOT_SHA:
        raise ValueError('Not the verified original TX15 backups')
    if sha(contents['reader.elf'])!=ELF_SHA or sha(contents['reader.bin'])!=BIN_SHA:raise ValueError('Unreviewed RAM initializer')
    plan=Transaction(*(contents[name] for name in FILES[:4]))
    if plan.manifest()!=manifest['transaction']:raise ValueError('Transaction manifest differs from frozen bytes')
    layout=check(contents['reader.elf'])
    return Kit(folder,plan,contents['reader.bin'],int(layout['entry'],16),manifest['device_uid'],manifest)

def checklist(kit):
    preserved=kit.plan.original_internal==kit.plan.boot+b'\xff'*(131072-len(kit.plan.boot))
    return dict(schema=1,board=kit.manifest['board'],device_uid=kit.uid,
        internal_address='0x08000000',internal_erase_bytes=0 if preserved else 131072,
        internal_program_bytes=0 if preserved else len(kit.plan.boot),internal_full_read_bytes=131072,
        external_offset=0,external_erase_bytes=kit.plan.erase_bytes,external_program_bytes=len(kit.plan.payload),
        recovery_external_bytes=1048576,recovery_internal_bytes=131072,
        file_sha256=kit.manifest['files'],install_approval=kit.approval('install'),
        recovery_approval=kit.approval('recover'),flash_write_authorized=False,
        success_exit='CPU halted; manual battery power cycle',rf_enabled=kit.manifest.get("rf_enabled",False),
        persistent_settings=kit.manifest.get("persistent_settings",False),
        settings_region=kit.manifest.get("settings_region"),
        limitations=(['Updated app hardware acceptance and native rollback untested'] if preserved else
            ['First physical programming/recovery and POR untested'])+['No USB updater']+(['Model1 NOR storage untested; calibration not stored'] if kit.manifest.get('persistent_settings') else ['No persistent model/calibration storage']))

"""Bounded install/recovery transaction core, independent of hardware transport.

There is deliberately no device-opening CLI/backend here. The CLI is plan-only.
A future SWD adapter
must check fresh identity, geometry, protection, idle state, CPU/clock/PH12 and
bundle provenance before calling this core. A seal binds exact bytes and ranges;
it is NOT evidence of human permission. Caller may pass it only after approval.
On WriteFailure keep CPU/power held; never boot a partially replaced image.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()

@dataclass(frozen=True)
class Transaction:
    boot:bytes
    payload:bytes
    original_internal:bytes
    original_external:bytes

    def __post_init__(self):
        if any(type(v) is not bytes for v in (self.boot,self.payload,self.original_internal,self.original_external)):
            raise ValueError('Immutable image bytes required')
        if not 0<len(self.boot)<=131072 or len(self.boot)%32 or not 0<len(self.payload)<=1048576 or len(self.payload)%256:
            raise ValueError('Unaligned/oversized installation image')
        if len(self.original_internal)!=131072 or len(self.original_external)!=1048576:
            raise ValueError('Complete internal and external slot backups required')

    @property
    def erase_bytes(self):return (len(self.payload)+4095)&~4095

    def manifest(self):
        return dict(schema=1,operation='transaction-core-no-hardware-backend',
            flash_write_authorized=False,internal_address='0x08000000',internal_erase_bytes=131072,
            external_offset=0,external_erase_bytes=self.erase_bytes,external_slot_bytes=1048576,
            external_erase_command='0x20',external_page_bytes=256,internal_word_bytes=32,
            boot_sha256=sha(self.boot),payload_sha256=sha(self.payload),
            original_internal_sha256=sha(self.original_internal),original_external_sha256=sha(self.original_external),
            install_order=['external erase/program/readback','internal erase/program/readback'],
            recovery_order=['external full slot/readback','internal full bank/readback'],
            physical_programming_tested=False)

    @property
    def seal(self):return sha(json.dumps(self.manifest(),sort_keys=True,separators=(',',':')).encode())

    @property
    def recovery_seal(self):return sha(('recover:'+self.seal).encode())

class WriteFailure(RuntimeError):
    def __init__(self,message,external_dirty,internal_dirty):
        super().__init__(message)
        self.external_dirty=external_dirty;self.internal_dirty=internal_dirty

def _external(backend,data,erase_bytes):
    if not 0<len(data)<=erase_bytes<=1048576 or erase_bytes%4096 or len(data)%256:
        raise ValueError('External range/page violation')
    for offset in range(0,erase_bytes,4096):backend.erase_external(offset,4096)
    if backend.read_external(0,erase_bytes)!=b'\xff'*erase_bytes:raise RuntimeError('External erase readback failed')
    for offset in range(0,len(data),256):
        page=data[offset:offset+256]
        if page!=b'\xff'*256:backend.program_external(offset,page)
    expected=data+b'\xff'*(erase_bytes-len(data))
    if backend.read_external(0,erase_bytes)!=expected:raise RuntimeError('External program readback failed')

def _internal(backend,data):
    if not 0<len(data)<=131072 or len(data)%32:raise ValueError('Internal bank/word violation')
    backend.erase_internal(0x08000000,131072)
    if backend.read_internal(0x08000000,131072)!=b'\xff'*131072:raise RuntimeError('Internal erase readback failed')
    for offset in range(0,len(data),32):
        word=data[offset:offset+32]
        if word!=b'\xff'*32:backend.program_internal(0x08000000+offset,word)
    if backend.read_internal(0x08000000,131072)!=data+b'\xff'*(131072-len(data)):
        raise RuntimeError('Internal program readback failed')

def install(plan,backend,authorization):
    if authorization!=plan.seal:raise ValueError('Exact reviewed install authorization required')
    backend.check_device()
    if (backend.read_internal(0x08000000,131072)!=plan.original_internal or
        backend.read_external(0,1048576)!=plan.original_external):
        raise ValueError('Live original content differs from verified backups; no erase')
    internal_dirty=False
    try:
        _external(backend,plan.payload,plan.erase_bytes)
        if backend.read_external(plan.erase_bytes,1048576-plan.erase_bytes)!=plan.original_external[plan.erase_bytes:]:
            raise RuntimeError('External bytes outside erase range changed')
        if hasattr(backend,'verified_stage'):backend.verified_stage('external')
        internal_dirty=True  # mark BEFORE issuing a potentially interrupted erase
        _internal(backend,plan.boot)
        if hasattr(backend,'verified_stage'):backend.verified_stage('internal')
    except BaseException as error:
        # Ctrl+C/SystemExit after an erase is also a partial replacement.
        raise WriteFailure(str(error),True,internal_dirty) from error
    return ['external-verified','internal-verified']

def recover(plan,backend,authorization):
    if authorization!=plan.recovery_seal:raise ValueError('Exact reviewed recovery authorization required')
    backend.check_device()
    try:
        _external(backend,plan.original_external,1048576)
        if hasattr(backend,'verified_stage'):backend.verified_stage('external')
        _internal(backend,plan.original_internal)
        if hasattr(backend,'verified_stage'):backend.verified_stage('internal')
    except BaseException as error:
        # Recovery begins from an unknown/partial image. It is unsafe even if
        # this attempt failed before touching the already-damaged internal bank.
        raise WriteFailure(str(error),True,True) from error
    return ['original-external-verified','original-internal-verified']

def validated_observation(record):
    from flash_info_bundle import decode
    run=record.get('ram_run',{})
    if (record.get('status')!='ram_live_verified' or record.get('cleanup_errors')!=[]
        or run.get('context_restored') is not True or run.get('live') is not True
        or run.get('recovery_errors')!=[] or not run.get('qspi',{}).get('backup_prefix_matches')):
        raise ValueError('Require successful read-only observation and complete recovery')
    observed=decode(bytes.fromhex(run['flash_info_raw_hex']),int(run['qspi']['jedec_id'],16))
    if not observed['conservative_status_clear']:raise ValueError('Observed protection/busy state requires investigation')
    return observed

def load_bundle(root):
    from install_plan import build_plan,backup_pair,INTERNAL_SHA,EXTERNAL_SHA
    boot=root/'local/tx15-hardware/boot';app=root/'local/tx15-hardware/app-standalone'
    _,internal,external=build_plan((boot/'tx15-boot.elf').read_bytes(),(boot/'tx15-boot.bin').read_bytes(),
        (app/'tx15-app.elf').read_bytes(),(app/'tx15-app.nd15').read_bytes(),
        json.loads((app/'build.json').read_text(encoding='utf8')))
    ib=root/'local/backups/tx15-20260926-191005'
    eb=root/'local/backups/tx15-external-20261003-155621'
    original_internal=backup_pair(ib/'internal-flash-08000000-read1.bin',ib/'internal-flash-08000000-read2.bin',131072,INTERNAL_SHA)
    original_external=backup_pair(eb/'external-mapped-90000000-read1.bin',eb/'external-mapped-90000000-read2.bin',16777216,EXTERNAL_SHA)
    return Transaction(internal,external,original_internal,original_external[:1048576])

def main():
    import argparse
    root=Path(__file__).resolve().parents[2]
    parser=argparse.ArgumentParser(description='Plan only: bind images/backups/observed geometry. Never opens a device.')
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--output',type=Path,default=root/'local/tx15-hardware/install/transaction-plan.json')
    args=parser.parse_args()
    plan=load_bundle(root)
    observed=validated_observation(json.loads(args.evidence.read_text(encoding='utf8')))
    manifest=plan.manifest()|dict(install_seal=plan.seal,recovery_seal=plan.recovery_seal,
        device_observation=observed,evidence_file=str(args.evidence.resolve()),
        pending=['Reset/RAM recovery entry hardware rehearsal and device UID-bound frozen kit',
                 'First physical erase/program and complete recovery verification',
                 'Fresh device/protection/content checks at actual installation',
                 'Human approval of exact persistent replacement',
                 'Power-off cold boot and power-button shutdown acceptance'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print('Prepared plan:',args.output,'; no device opened or Flash written.')
    print('External erase bytes:',plan.erase_bytes,'; internal erase bytes: 131072; authorization: false')
    return 0

if __name__=='__main__':raise SystemExit(main())

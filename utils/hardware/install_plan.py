"""Generate a reviewable installation/recovery bundle; never opens a device.

This plan describes replacement of native-owned storage. It is not write
authorization, a Flash programmer, or proof of board POR/recovery acceptance.
"""
import argparse,hashlib,json,sys
from pathlib import Path
try:
    from . import boot_elf,app_image,boot_image
except ImportError:
    import boot_elf,app_image,boot_image

ROOT=Path(__file__).resolve().parents[2]
INTERNAL_SHA='984420d754587cd5561c1b3f3df49ccdd34da868ff785efbdcdc0cff09569ad0'
EXTERNAL_SHA='968cab41ec1bd50f271b8c2ad7fff0fc981fefdca42aadc3ef672933ce2ad7a1'
def sha(data):return hashlib.sha256(data).hexdigest()
def padded(data,alignment):return data+b'\xff'*((-len(data))%alignment)

def backup_pair(first,second,size,expected_sha):
    if first.resolve()==second.resolve():raise ValueError('Two distinct backup files required')
    one,two=first.read_bytes(),second.read_bytes()
    if len(one)!=size or one!=two or sha(one)!=expected_sha:raise ValueError('Backup pair differs from recorded size/hash')
    return one

def build_plan(boot,boot_bin,app,payload,metadata):
    layout=boot_elf.parse(boot)
    if boot_elf.binary(boot)!=boot_bin:raise ValueError('Boot BIN does not match boot ELF')
    if (metadata.get('schema')!=1 or metadata.get('mode')!='standalone-first-boot-rf-off'
            or metadata.get('rf_enabled') is not False or metadata.get('persistent_settings') is not False
            or metadata.get('elf_sha256')!=sha(app) or metadata.get('payload_sha256')!=sha(payload)):
        raise ValueError('Require matching standalone RF-off app build metadata')
    entry,segments=app_image.parse(app)
    if boot_image.unpack(payload)!=(entry,segments):raise ValueError('Payload differs from the application ELF')
    internal,external=padded(boot_bin,32),padded(payload,256)
    erase=(len(external)+4095)&~4095
    if len(internal)>131072 or erase>1048576:raise ValueError('Images exceed native-owned boot storage')
    manifest={'schema':1,'operation':'plan-only-no-device-access','flash_write_authorized':False,
        'board':'TX15 MAX STM32H750','expected_jedec_id':'0xc84018',
        'app_mode':metadata['mode'],'app_entry':hex(entry),'boot_entry':layout['entry'],
        'writes':[
            {'address':'0x08000000','erase_bytes':131072,'program_bytes':len(internal),
             'file':'boot-flash.bin','sha256':sha(internal),'alignment':32},
            {'address':'0x90000000','storage_offset':0,'erase_bytes':erase,'program_bytes':len(external),
             'file':'payload-flash.bin','sha256':sha(external),'page_bytes':256,'candidate_erase_sector_bytes':4096}],
        'pending_verification':['Full native loader/app chain in RAM',
            'Live Flash protection, actual erase/program geometry and recovery writer',
            'User authorization for these exact persistent writes',
            'True power-off cold boot and power-button shutdown'],
        'limitations':['RF disabled','No persistent model/calibration storage','No USB updater'],
        'restore_order':['Restore changed external boot slot from original backup and verify',
                         'Restore original internal 128KiB last and verify',
                         'Power off and verify original system boots']}
    return manifest,internal,external

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'local/tx15-hardware/install')
    args=parser.parse_args()
    boot=ROOT/'local/tx15-hardware/boot';app=ROOT/'local/tx15-hardware/app-standalone'
    manifest,internal,external=build_plan((boot/'tx15-boot.elf').read_bytes(),(boot/'tx15-boot.bin').read_bytes(),
        (app/'tx15-app.elf').read_bytes(),(app/'tx15-app.nd15').read_bytes(),json.loads((app/'build.json').read_text(encoding='utf8')))
    ib=ROOT/'local/backups/tx15-20260926-191005';eb=ROOT/'local/backups/tx15-external-20261003-155621'
    original_internal=backup_pair(ib/'internal-flash-08000000-read1.bin',ib/'internal-flash-08000000-read2.bin',131072,INTERNAL_SHA)
    original_external=backup_pair(eb/'external-mapped-90000000-read1.bin',eb/'external-mapped-90000000-read2.bin',16777216,EXTERNAL_SHA)
    recovery=original_external[:1048576]
    manifest['backups']={'internal_128k_sha256':sha(original_internal),'external_16m_sha256':sha(original_external),
        'recovery_external_slot_sha256':sha(recovery),'two_files_match_recorded_hashes':True,
        'physical_restore_tested':False}
    args.output.mkdir(parents=True,exist_ok=True)
    for name,data in [('boot-flash.bin',internal),('payload-flash.bin',external),
                      ('recovery-internal-128k.bin',original_internal),('recovery-external-slot-1m.bin',recovery)]:
        (args.output/name).write_bytes(data)
    (args.output/'install-plan.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print('Review bundle:',args.output,'; no device opened; NOT authorized or accepted for flashing.')
    print(json.dumps(manifest['writes'],indent=2));return 0

if __name__=='__main__':raise SystemExit(main())

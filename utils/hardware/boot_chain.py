"""Bounded RAM source upload and V10 proof for the native loader/app chain.

Source substitution is only bench evidence. It cannot prove installed NOR boot
or true power-on. No program/erase commands and no host app-destination writes.
"""
import hashlib,json,struct
from probe_report import FIELDS, SDRAM_FIELDS
SOURCE=0xd0200000
MAX_BYTES=0xec040
READY=0x43485244
GO=0x4348474f
CONTROL=0x24001b70
ELF_SHA='077cdceb4dd84865327f4408b9234e04a17382992598b7ca50785f2c1a4f1659'
BIN_SHA='e6573cefc35899fa69fc9e488a3757b073ec644480ff4153a0500977fae0fb68'
APP_SHA='c338a00af8e4ff74147161ac9681e1ea988ebc18930cd1b02b2ed40f063ac0c4'
PAYLOAD_SHA='bc2fcd3f844fe88f242c5e259820f4dff091cbf72c50a79eb2f1e07533549153'
BACKUP_SHA='968cab41ec1bd50f271b8c2ad7fff0fc981fefdca42aadc3ef672933ce2ad7a1'

def validate_bundle(root):
    from check_ram_elf import check
    from boot_image import pack
    folder=root/'local/tx15-hardware/boot-chain'
    elf=(folder/'boot-chain.elf').read_bytes();binary=(folder/'boot-chain.bin').read_bytes()
    meta=json.loads((folder/'build.json').read_text())
    appfolder=root/'local/tx15-hardware/app-standalone'
    app=(appfolder/'tx15-app.elf').read_bytes();payload=(appfolder/'tx15-app.nd15').read_bytes()
    appmeta=json.loads((appfolder/'build.json').read_text())
    for data,expected in ((elf,ELF_SHA),(binary,BIN_SHA),(app,APP_SHA),(payload,PAYLOAD_SHA)):
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Candidate differs from reviewed chain build')
    if meta!=dict(schema=1,mode='ram-chain-no-flash',control=CONTROL,elf_sha256=ELF_SHA,bin_sha256=BIN_SHA):
        raise ValueError('Chain control metadata mismatch')
    if appmeta!=dict(schema=1,mode='standalone-first-boot-rf-off',elf_sha256=APP_SHA,
                    payload_sha256=PAYLOAD_SHA,rf_enabled=False,persistent_settings=False):
        raise ValueError('Not RF-off standalone app')
    layout=check(elf)
    if not 704<=len(binary)<0xe000 or struct.unpack_from('<2I',binary)!=(0x24010000,int(layout['entry'],16)):
        raise ValueError('Invalid chain vectors/size')
    if payload!=pack(app):raise ValueError('Payload not packed from candidate ELF')
    backup=(root/'local/backups/tx15-external-20261003-155621/external-mapped-90000000-read1.bin').read_bytes()
    if len(backup)!=16777216 or hashlib.sha256(backup).hexdigest()!=BACKUP_SHA:
        raise ValueError('Known original backup unavailable/mismatch')
    return binary+bytes((-len(binary))%8),layout,payload,backup[:64]

def source_chunks(data):
    if not 64<=len(data)<=MAX_BYTES: raise ValueError('Invalid chain source size')
    data+=bytes((-len(data))%8)
    for off in range(0,len(data),256): yield SOURCE+off,data[off:off+256]

def decode(data):
    if len(data)!=128: raise ValueError('Expected 128-byte native V10 mailbox')
    r=dict(zip(FIELDS+SDRAM_FIELDS,struct.unpack('<32I',data)))
    if r['magic']!=0x4e445631 or r['version']!=10: raise ValueError('Not native V10 application')
    r['power_status']=r.pop('reserved')
    return r

def is_live(current,previous):
    for r in (current,previous):
        if (r['version']!=10 or r['state']!=3 or r['error'] or r['power_status']&15!=15
            or r['cpuid']!=0x411fc271 or r['device_id']&0xfff!=0x450
            or r['ram_words']!=31 or r['sdram_state']!=2 or r['sdram_error']
            or r['rcc_cr']&0x3f0f001d!=0x33030005 or r['rcc_cfgr']&0x3f!=0x1b
            or r['rcc_d1cfgr']&0xf7f!=0x48 or r['scb_ccr']&0x30000 or r['mpu_ctrl']&1
            or any(r[k] for k in ('fault_exception','cfsr','hfsr','mmfar','bfar'))): return False
    if current['device_id']!=previous['device_id']: return False
    return all(0<((current[k]-previous[k])&0xffffffff)<0x80000000 for k in ('ticks','loops'))

def upload(ap,dp,data):
    if not ap.read32(0xe000edf0)&(1<<17) or ap.read32(0xe000ed04)&0x1ff:
        raise RuntimeError('Source upload requires halted thread mode')
    if dp.read_ap(0)&0x37!=0x12: raise RuntimeError('Unexpected MEM-AP CSW')
    count=0;next_print=0
    for at,chunk in source_chunks(data):
        words=len(chunk)//4
        dp.write_ap(4,at);dp.write_ap_multiple(12,struct.unpack('<%dI'%words,chunk));dp.flush()
        dp.write_ap(4,at)
        actual=struct.pack('<%dI'%words,*dp.read_ap_multiple(12,words))
        if actual!=chunk: raise RuntimeError('Chain source readback mismatch at '+hex(at))
        count+=len(chunk)
        if count>=next_print:
            print('CHAIN SOURCE READBACK',count,'bytes',flush=True);next_print=count+65536
    return count

def quiesce_thread(read,write,reg_write,wait_halt,sleep):
    """Halt and drain an active SysTick without fabricating exception return.

    Fault/other active exception: keep CPU halted, leave fault status intact,
    prohibit replacing original context. A manual power cycle remains possible
    because this bench never writes Flash. Only SysTick is enabled by this app.
    """
    write(0xe000edf0,0xa05f0003);wait_halt()
    write(0xe000e010,0);write(0xe000e014,0);write(0xe000e018,0)
    write(0xe000ed04,(1<<25)|(1<<27))
    reg_write(20,1)
    for _ in range(20):
        active=read(0xe000ed04)&0x1ff
        if not active:return
        if active!=15 or read(0xe000ed28) or read(0xe000ed2c):
            raise RuntimeError('Active fault/unsupported exception; manual power-cycle recovery required')
        write(0xe000edf0,0xa05f0001);sleep(0.002)
        write(0xe000edf0,0xa05f0003);wait_halt()
    raise RuntimeError('Active SysTick did not return; context replacement refused')

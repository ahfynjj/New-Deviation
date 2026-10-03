"""Strict native bootloader storage/runtime map, no hardware access."""
import struct
FLASH=(0x08000000,0x08020000)
RAM=(0x24000000,0x2400e000)

def parse(data):
    if len(data)<52 or data[:7]!=b'\x7fELF\x01\x01\x01':raise ValueError('Expected ELF32 LE')
    _,kind,machine,version,entry,phoff,_,_,_,phsize,phnum,_,_,_=struct.unpack_from('<16sHHIIIIIHHHHHH',data)
    if (kind,machine,version,phsize)!=(2,40,1,32) or not entry&1 or not 1<=phnum<=8:
        raise ValueError('Invalid ARM boot executable')
    vectors=None;stack=mailbox=False;virtual=[];physical=[];end=FLASH[0];execute=[]
    for i in range(phnum):
        at=phoff+i*32
        if at+32>len(data):raise ValueError('Truncated headers')
        typ,off,va,pa,fs,ms,flags,align=struct.unpack_from('<8I',data,at)
        if typ!=1:continue
        if not ms or fs>ms or off>len(data) or fs>len(data)-off:raise ValueError('Invalid segment')
        if any(max(va,a)<min(va+ms,b) for a,b in virtual):raise ValueError('RAM/ROM overlap')
        virtual.append((va,va+ms))
        if fs:
            if not FLASH[0]<=pa or pa+fs>FLASH[1]:raise ValueError('Physical storage outside internal Flash')
            if any(max(pa,a)<min(pa+fs,b) for a,b in physical):raise ValueError('Storage overlap')
            physical.append((pa,pa+fs));end=max(end,pa+fs)
        if FLASH[0]<=va and va+ms<=FLASH[1] and va==pa and fs==ms and flags==5:
            execute.append((va,va+fs))
            if va==FLASH[0] and fs>=704:vectors=data[off:off+704]
        elif RAM[0]<=va and va+ms<=RAM[1] and flags==6:
            if not fs and pa!=va:raise ValueError('Invalid BSS map')
        elif va==0x2400e000 and ms==128 and not fs and flags==6 and pa==va:mailbox=True
        elif va==0x2400f000 and ms==4096 and not fs and flags==6 and pa==va:stack=True
        else:raise ValueError('Unexpected boot runtime region')
    if not stack or not mailbox or vectors is None:raise ValueError('Missing boot vectors/stack/mailbox')
    words=struct.unpack('<176I',vectors)
    if words[:2]!=(0x24010000,entry):raise ValueError('Wrong boot SP/entry')
    if any(not v&1 or not any(a<=(v&~1)<b for a,b in execute) for v in words[1:]):
        raise ValueError('Boot vector outside loaded executable Flash')
    return {'entry':hex(entry),'flash_start':hex(FLASH[0]),'flash_bytes':end-FLASH[0],
            'stack_top':'0x24010000','mailbox':'0x2400e000'}

def binary(data):
    """Match objcopy raw binary, including zero-filled physical storage gaps."""
    layout=parse(data);result=bytearray(layout['flash_bytes'])
    phoff=struct.unpack_from('<I',data,28)[0];phnum=struct.unpack_from('<H',data,44)[0]
    for i in range(phnum):
        typ,off,va,pa,fs,ms,flags,align=struct.unpack_from('<8I',data,phoff+i*32)
        if typ==1 and fs:result[pa-FLASH[0]:pa-FLASH[0]+fs]=data[off:off+fs]
    return bytes(result)

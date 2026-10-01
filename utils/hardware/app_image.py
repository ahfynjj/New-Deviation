"""Strict load map for the native app stage; never permits Flash writes."""
import struct

CODE=(0x24010000,0x2407c000)
STACK=(0x2407c000,0x24080000)
RESOURCES=(0xd0080000,0xd0100000)

def parse(data):
    if len(data)<52 or data[:7]!=b'\x7fELF\x01\x01\x01': raise ValueError('Expected ELF32 LE')
    _,kind,machine,version,entry,phoff,_,_,_,phsize,phnum,_,_,_=struct.unpack_from('<16sHHIIIIIHHHHHH',data)
    if (kind,machine,version,phsize)!=(2,40,1,32) or not entry&1: raise ValueError('Invalid ARM executable')
    segments=[]; occupied=[]; stack=False
    for i in range(phnum):
        at=phoff+i*phsize
        if at+32>len(data): raise ValueError('Truncated program headers')
        typ,off,va,pa,fs,ms,flags,align=struct.unpack_from('<8I',data,at)
        if typ!=1: continue
        if va!=pa or fs>ms or off+fs>len(data): raise ValueError('Invalid segment')
        if va==STACK[0] and ms==STACK[1]-STACK[0] and fs==0 and flags==6:
            stack=True
        elif CODE[0]<=va<CODE[1] and va+ms<=CODE[1] and fs and flags==7:
            segments.append((va,data[off:off+fs]))
        elif RESOURCES[0]<=va<RESOURCES[1] and va+ms<=RESOURCES[1] and fs==ms and fs and flags==4:
            segments.append((va,data[off:off+fs]))
        else: raise ValueError('Segment outside app-owned RAM or unexpected permissions')
        if any(max(va,a)<min(va+ms,b) for a,b in occupied): raise ValueError('Overlapping segments')
        occupied.append((va,va+ms))
    code=next((b for a,b in segments if a==CODE[0]),None)
    if not stack or code is None or len(code)<704: raise ValueError('Missing vectors/stack')
    vectors=struct.unpack_from('<176I',code)
    if vectors[:2]!=(STACK[1],entry): raise ValueError('Wrong entry/SP')
    if any(not v&1 or not CODE[0]<=(v&~1)<CODE[0]+len(code) for v in vectors[1:]):
        raise ValueError('Exception vector outside loaded code')
    if len(segments)!=2 or not any(a==RESOURCES[0] for a,b in segments):
        raise ValueError('Expected code plus resource segments')
    for a,b in segments:
        if a%8 or not allowed(a,(len(b)+7)&~7): raise ValueError('Unaligned/out-of-range transfer')
    return entry,segments

def allowed(address,size):
    return size>0 and address%4==0 and size%4==0 and any(lo<=address and address+size<=hi for lo,hi in (CODE,RESOURCES))

def transfer_chunks(address,data):
    """Pad full ECC doublewords and never cross MEM-AP 1KiB auto-increment wrap."""
    data+=bytes((-len(data))%8)
    if not allowed(address,len(data)): raise ValueError('Disallowed app transfer')
    offset=0
    while offset<len(data):
        n=min(256,1024-((address+offset)%1024),len(data)-offset)
        yield address+offset,data[offset:offset+n]
        offset+=n

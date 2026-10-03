"""TX15 native boot payload, not a directly flashable installer.

Storage offset and cold-start initialization belong to the future installer/loader.
The same fixed-layout validation is implemented in hardware/tx15/boot/image.c.
"""
import argparse
import json
import struct
import zlib
from pathlib import Path
if __package__:
    from . import app_image
else:
    import app_image

MAGIC=b'ND15APP1'
BOARD=0x54583135
HEADER_SIZE=64
MAX_SIZE=64+(app_image.CODE[1]-app_image.CODE[0])+(app_image.RESOURCES[1]-app_image.RESOURCES[0])

def aligned(n): return (n+7)&~7

def pack(elf):
    entry,segments=app_image.parse(elf)
    segments=sorted(segments)
    payload=bytearray();descriptors=[]
    for address,data in segments:
        descriptors.extend((address,HEADER_SIZE+len(payload),len(data),zlib.crc32(data)))
        payload.extend(data);payload.extend(bytes((-len(data))%8))
    header=struct.pack('<8s13I',MAGIC,1,HEADER_SIZE+len(payload),entry,BOARD,*descriptors,0)
    result=header+struct.pack('<I',zlib.crc32(header))+payload
    unpack(result)
    return result

def unpack(data):
    if len(data)<HEADER_SIZE or len(data)>MAX_SIZE: raise ValueError('Invalid image length')
    magic,version,total,entry,board,*fields=struct.unpack_from('<8s14I',data)
    if (magic,version,total,board,fields[8]) != (MAGIC,1,len(data),BOARD,0):
        raise ValueError('Invalid boot header/board/version')
    if zlib.crc32(data[:60])!=fields[9]: raise ValueError('Header CRC mismatch')
    result=[];expected_offset=HEADER_SIZE
    for i,(lo,hi) in enumerate((app_image.CODE,app_image.RESOURCES)):
        address,offset,length,crc=fields[i*4:i*4+4]
        end=offset+aligned(length)
        if address!=lo or offset!=expected_offset or not length or lo+aligned(length)>hi or end>total:
            raise ValueError('Invalid segment layout')
        block=data[offset:offset+length]
        if zlib.crc32(block)!=crc or any(data[offset+length:end]):
            raise ValueError('Payload CRC/padding mismatch')
        result.append((address,block));expected_offset=end
    if expected_offset!=total: raise ValueError('Trailing data')
    code=result[0][1]
    if len(code)<704 or not entry&1: raise ValueError('Missing vectors/Thumb entry')
    vectors=struct.unpack_from('<176I',code)
    if vectors[:2]!=(app_image.STACK[1],entry): raise ValueError('Invalid stack/entry')
    if any(not v&1 or not app_image.CODE[0]<=(v&~1)<app_image.CODE[0]+len(code) for v in vectors[1:]):
        raise ValueError('Invalid exception vector')
    return entry,result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('pack','inspect'))
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.command=='pack':
        if args.output is None: parser.error('pack requires --output')
        raw=pack(args.input.read_bytes());args.output.write_bytes(raw)
    else: raw=args.input.read_bytes()
    entry,segments=unpack(raw)
    print(json.dumps(dict(format='ND15APP1',bytes=len(raw),entry=hex(entry),
        segments=[dict(destination=hex(a),bytes=len(b)) for a,b in segments],
        installable=False,reason='Requires native cold-start loader and verified storage layout'),indent=2))

if __name__=='__main__': main()

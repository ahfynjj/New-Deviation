"""Parse bounded SFDP observations; never opens hardware or authorizes writes.

Field definitions checked against Linux spi-nor sfdp.h/sfdp.c (JESD216).
https://github.com/torvalds/linux/blob/master/drivers/mtd/spi-nor/sfdp.h
GD25Q128H is a command/status reference, not an exact-part identification.
"""
import hashlib
import struct

def parse_sfdp(data):
    if len(data)<16 or data[:4]!=b'SFDP' or data[5]!=1 or data[7]!=0xff:
        raise ValueError('Missing supported SFDP header/protocol')
    count=data[6]+1
    if count>16 or 8+count*8>len(data):raise ValueError('Truncated/oversized SFDP headers')
    tables=[]
    for i in range(count):
        h=data[8+i*8:16+i*8]
        ident=(h[7]<<8)|h[0]
        if ident==0xff81:raise ValueError('Sector-map table requires region-aware validation')
        if ident==0xff00 and h[2]==1:
            offset=int.from_bytes(h[4:7],'little');size=h[3]*4
            if size<44 or offset<8+count*8 or offset%4 or offset+size>len(data):
                raise ValueError('Invalid/truncated basic parameter table')
            tables.append((h[1],h[3],offset))
    if not tables:raise ValueError('No usable basic parameter table')
    minor,length,offset=max(tables)
    words=struct.unpack_from('<%dI'%length,data,offset)
    address=(words[0]>>17)&3
    if address not in (0,1):raise ValueError('Three-byte address mode not supported')
    density=words[1]
    if density&0x80000000:
        exponent=density&0x7fffffff
        if not 3<=exponent<=31:raise ValueError('Unsupported density exponent')
        bits=1<<exponent
    else:bits=density+1
    if bits%8 or not 4096<=bits//8<=16777216:raise ValueError('Unsupported capacity')
    page_exp=(words[10]>>4)&15
    if not 8<=page_exp<=12:raise ValueError('Unsupported page size')
    erases=[]
    for word in words[7:9]:
        for shift in (0,16):
            exponent=(word>>shift)&255;opcode=(word>>(shift+8))&255
            if not exponent:continue
            if not 12<=exponent<=24 or opcode in (0,255):raise ValueError('Invalid erase type')
            erases.append((1<<exponent,opcode))
    if not erases:raise ValueError('No supported erase types')
    return dict(capacity_bytes=bits//8,page_bytes=1<<page_exp,address_bytes=3,
        erase_types=sorted(set(erases)),bfpt_revision=[1,minor],bfpt_dwords=length,
        sfdp_sha256=hashlib.sha256(data).hexdigest())

def assess(jedec,status,sfdp):
    if jedec!=0xc84018 or len(status)!=3:raise ValueError('Unexpected identity/status record')
    geometry=parse_sfdp(sfdp)
    if (geometry['capacity_bytes']!=16777216 or geometry['page_bytes']!=256
            or (4096,0x20) not in geometry['erase_types']):
        raise ValueError('Geometry differs from candidate installation')
    # Deliberately conservative across this ID family. QE/drive strength may
    # remain set; reject WIP/WEL/BP/SRP/CMP/suspend/locks/other configuration.
    clear=not (status[0] or status[1]&~0x02 or status[2]&~0x60)
    return dict(jedec_id=hex(jedec),status_hex=bytes(status).hex(),geometry=geometry,
        conservative_status_clear=clear,exact_part_suffix=None,
        flash_write_authorized=False,physical_write_recovery_tested=False)

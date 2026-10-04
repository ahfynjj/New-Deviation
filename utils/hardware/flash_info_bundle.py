"""Exact small RAM read-only Flash-info candidate and report contract."""
import hashlib
import json
import struct
from check_ram_elf import check
from flash_geometry import assess
from install_plan import EXTERNAL_SHA
ELF_SHA='7df17ec5959416d7ce527600309db744af76ded319d88ba5b12a7aa54a3d8265'
BIN_SHA='d097c3f89118eab9576a27eca2d8d7a6df8c9d868ff71063344889085b8f00ad'
INFO_ADDR,QSPI_ADDR=0x24000ef0,0x240012fc
REPORT_BYTES=1036

def validate(root):
    folder=root/'local/tx15-hardware/flash-info'
    elf=(folder/'flash-info.elf').read_bytes()
    binary=(folder/'flash-info.bin').read_bytes()
    meta=json.loads((folder/'build.json').read_text(encoding='utf8'))
    if (hashlib.sha256(elf).hexdigest()!=ELF_SHA or hashlib.sha256(binary).hexdigest()!=BIN_SHA
        or len(binary)!=3816 or meta!={'schema':1,'mode':'read-only-flash-info',
            'elf_sha256':ELF_SHA,'bin_sha256':BIN_SHA,'info_report':INFO_ADDR,'qspi_report':QSPI_ADDR}):
        raise ValueError('Unreviewed Flash-info candidate')
    layout=check(elf)
    backup=(root/'local/backups/tx15-external-20261003-155621/external-mapped-90000000-read1.bin').read_bytes()
    if len(backup)!=16777216 or hashlib.sha256(backup).hexdigest()!=EXTERNAL_SHA:
        raise ValueError('Original backup does not match recorded hash')
    return binary,layout,backup[:64]

def decode(data,jedec):
    if len(data)!=REPORT_BYTES or struct.unpack_from('<II',data)!=(0x46494e31,0) or data[11]:
        raise ValueError('Incomplete/failed Flash-info report')
    return assess(jedec,data[8:11],data[12:])

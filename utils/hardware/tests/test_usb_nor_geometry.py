"""The C updater must assess SFDP with the existing read-only Python policy."""
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from test_flash_geometry import fixture
import flash_geometry

ROOT=Path(__file__).resolve().parents[3]
HARNESS=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nor_geometry.h"
int main(int argc,char **argv) {
    if(argc!=6)return 2;
    FILE *f=fopen(argv[1],"rb");if(!f)return 2;
    unsigned char data[2048];size_t n=fread(data,1,sizeof(data),f);fclose(f);
    unsigned char sr[3];for(unsigned j=0;j<3;j++)sr[j]=(unsigned char)strtoul(argv[j+3],0,16);
    struct tx15_update_flash_info info;memset(&info,0xa5,sizeof(info));
    int ok=tx15_update_nor_assess((uint32_t)strtoul(argv[2],0,16),sr,data,n,&info);
    if(!ok) {
        const unsigned char *p=(const unsigned char *)&info;
        for(size_t j=0;j<sizeof(info);j++)if(p[j])return 3;
        puts("0");return 0;
    }
    printf("1 %u %u %u %u %u\n",info.jedec,info.capacity,info.page_bytes,
           info.erase_bytes,tx15_update_flash_writable(&info));return 0;
}
'''

class USBNorGeometryTests(unittest.TestCase):
    def test_c_and_python_assess_valid_and_malformed_tables(self):
        source=ROOT/'hardware/tx15/usb_update/nor_geometry.c'
        self.assertTrue(source.exists(),'Native NOR SFDP assessment is missing')
        cases=[(fixture(),0xc84018,b'\0\x02\x60')]
        for status in [b'\0\0\0',b'\1\2\x60',b'\4\2\x60',b'\0\x42\x60',b'\0\2\x64']:
            cases.append((fixture(),0xc84018,status))
        cases.extend((data,0xc84018,b'\0\0\0') for data in [b'',fixture()[:15],fixture()[:100],b'BAD!'+fixture()[4:]])
        for offset,value in [(12,8),(12,0xfffffc),(0x44,0x800000ff),(0x44,0x8000001b),
                             (0x40,2<<17),(0x68,0),(0x68,9<<4),(0x5c,0x520f210c)]:
            data=bytearray(fixture());struct.pack_into('<I',data,offset,value)
            cases.append((bytes(data),0xc84018,b'\0\2\x60'))
        data=bytearray(fixture());data[6]=1
        data[16:24]=bytes([0x81,0,1,1,0x90,0,0,0xff])
        cases.append((bytes(data),0xc84018,b'\0\0\0'))
        cases.extend((fixture(),jedec,b'\0\0\0') for jedec in [0xef4018,0xc84017])
        for offset,value in [(5,2),(6,255),(7,0),(10,2),(11,10),
                             (12,0x41),(0x68,0x70),(0x5d,0),(0x5d,255),(0x5c,11)]:
            data=bytearray(fixture());data[offset]=value
            cases.append((bytes(data),0xc84018,b'\0\0\0'))
        # Newest BFPT must win; selecting the old valid table would authorize
        # this newer, incompatible page geometry.
        data=bytearray(fixture());data[6]=1
        data[16:24]=bytes([0,7,1,16,0xc0,0,0,0xff])
        data[0xc0:0x100]=data[0x40:0x80]
        struct.pack_into('<I',data,0xe8,9<<4)
        cases.append((bytes(data),0xc84018,b'\0\0\0'))
        gcc=Path(tempfile.gettempdir())/'new-deviation-ucrt64/bin/gcc.exe'
        env=dict(os.environ,PATH=str(gcc.parent)+os.pathsep+os.environ.get('PATH',''))
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);harness=tmp/'test.c';harness.write_text(HARNESS)
            exe=tmp/'test.exe';directory=ROOT/'hardware/tx15/usb_update'
            command=[str(gcc),'-std=c99','-Wall','-Wextra','-Werror',
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/include'),
                '-I',str(ROOT.parent/'tools/msys64/ucrt64/lib/gcc/x86_64-w64-mingw32/16.2.0/include'),
                '-I',str(directory),
                str(harness),str(source),str(directory/'transaction.c'),str(directory/'package.c'),
                str(ROOT/'hardware/tx15/boot/image.c'),'-o',str(exe)]
            built=subprocess.run(command,env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
            self.assertEqual(built.returncode,0,built.stderr)
            for data,jedec,status in cases:
                with self.subTest(bytes=len(data),jedec=jedec,status=status.hex(),data=data[:16].hex()):
                    path=tmp/'sfdp.bin';path.write_bytes(data)
                    observed=subprocess.run([str(exe),str(path),hex(jedec),*[hex(v) for v in status]],
                        env=env,capture_output=True,text=True,encoding='utf8',errors='replace')
                    self.assertEqual(observed.returncode,0,observed.stderr)
                    try:
                        reference=flash_geometry.assess(jedec,status,data)
                    except ValueError:
                        expected=[0]
                    else:
                        g=reference['geometry']
                        expected=[1,jedec,g['capacity_bytes'],g['page_bytes'],4096,
                                  int(reference['conservative_status_clear'])]
                    self.assertEqual([int(v) for v in observed.stdout.split()],expected)

/* Matches utils/hardware/flash_geometry.py. No hardware or write operations. */
#include "nor_geometry.h"
#include <string.h>
static uint32_t word(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
int tx15_update_nor_assess(uint32_t jedec,const uint8_t status[3],
                           const uint8_t *sfdp,size_t bytes,
                           struct tx15_update_flash_info *out)
{
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (jedec!=0xc84018u || !status || !sfdp || bytes<16
        || memcmp(sfdp,"SFDP",4) || sfdp[5]!=1 || sfdp[7]!=255) return 0;
    unsigned count=(unsigned)sfdp[6]+1;
    if (count>16 || bytes<8u+count*8u) return 0;
    unsigned minor=0,length=0;uint32_t selected=0;
    for (unsigned i=0;i<count;i++) {
        const uint8_t *h=sfdp+8+i*8;
        unsigned id=(unsigned)h[7]<<8|h[0];
        /* A nonuniform sector map cannot use the fixed application range. */
        if (id==0xff81) return 0;
        if (id!=0xff00 || h[2]!=1) continue;
        uint32_t offset=(uint32_t)h[4]|(uint32_t)h[5]<<8|(uint32_t)h[6]<<16;
        size_t size=(size_t)h[3]*4;
        if (size<44 || offset<8u+count*8u || offset%4
            || offset>bytes || size>bytes-offset) return 0;
        if (!selected || h[1]>minor || (h[1]==minor && h[3]>length)
            || (h[1]==minor && h[3]==length && offset>selected)) {
            selected=offset;minor=h[1];length=h[3];
        }
    }
    if (!selected) return 0;
    const uint8_t *table=sfdp+selected;
    if (((word(table)>>17)&3u)>1) return 0;
    uint32_t density=word(table+4);uint64_t bits;
    if (density&0x80000000u) {
        unsigned exponent=density&0x7fffffffu;
        if (exponent<3 || exponent>31) return 0;
        bits=(uint64_t)1<<exponent;
    } else bits=(uint64_t)density+1;
    if (bits%8 || bits/8!=0x1000000u || ((word(table+40)>>4)&15u)!=8) return 0;
    unsigned has4k=0,types=0;
    for (unsigned i=0;i<4;i++) {
        unsigned exponent=table[28+i*2],opcode=table[29+i*2];
        if (!exponent) continue;
        if (exponent<12 || exponent>24 || !opcode || opcode==255) return 0;
        types++;
        if (exponent==12 && opcode==0x20) has4k=1;
    }
    if (!types || !has4k) return 0;
    out->jedec=jedec;out->capacity=0x1000000u;out->page_bytes=256;
    out->erase_bytes=4096;out->sr1=status[0];out->sr2=status[1];out->sr3=status[2];
    out->sfdp_valid=1;
    return 1;
}

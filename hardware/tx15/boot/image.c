/* New Deviation native boot payload validation; GPL-3.0-or-later. */
#include "image.h"

static uint32_t word(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static uint32_t crc32(const uint8_t *p, uint32_t n)
{
    uint32_t crc=0xffffffffu;
    while (n--) {
        crc^=*p++;
        for (unsigned i=0;i<8;i++) crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);
    }
    return ~crc;
}
uint32_t tx15_boot_image_size(const uint8_t p[64])
{
    static const uint8_t magic[8]={'N','D','1','5','A','P','P','1'};
    static const uint32_t dest[2]={0x24010000u,0xd0080000u};
    static const uint32_t capacity[2]={0x6c000u,0x80000u};
    if (!p) return 0;
    for (unsigned i=0;i<8;i++) if (p[i]!=magic[i]) return 0;
    uint32_t bytes=word(p+12),offset=64;
    if (bytes<64 || bytes>64u+0x6c000u+0x80000u || word(p+8)!=1
            || word(p+20)!=0x54583135u || word(p+56) || word(p+60)!=crc32(p,60)) return 0;
    for (unsigned i=0;i<2;i++) {
        const uint8_t *d=p+24+i*16;
        uint32_t length=word(d+8),padded=(length+7u)&~7u;
        if (word(d)!=dest[i] || word(d+4)!=offset || !length || length>capacity[i]
                || padded>capacity[i] || padded>bytes-offset) return 0;
        if (!i && (length<704 || !(word(p+16)&1u) || (word(p+16)&~1u)<dest[0]
                || (word(p+16)&~1u)-dest[0]>=length)) return 0;
        offset+=padded;
    }
    return offset==bytes?bytes:0;
}
int tx15_boot_image_validate(const uint8_t *p, size_t bytes, struct tx15_boot_image *plan)
{
    static const uint32_t dest[2]={0x24010000u,0xd0080000u};
    static const uint32_t capacity[2]={0x6c000u,0x80000u};
    if (!plan) return 0;
    plan->entry=0;
    for (unsigned i=0;i<2;i++) {
        plan->segments[i].source=0;
        plan->segments[i].destination=plan->segments[i].length=0;
    }
    if (!p || bytes<64 || bytes>64u+0x6c000u+0x80000u) return 0;
    if (tx15_boot_image_size(p)!=bytes) return 0;
    uint32_t offset=64, lengths[2], starts[2];
    for (unsigned i=0;i<2;i++) {
        const uint8_t *d=p+24+i*16;
        uint32_t length=word(d+8);
        if (word(d)!=dest[i] || word(d+4)!=offset || !length || length>capacity[i]) return 0;
        uint32_t padded=(length+7u)&~7u;
        if (padded>capacity[i] || padded>bytes-offset || word(d+12)!=crc32(p+offset,length)) return 0;
        for (uint32_t j=length;j<padded;j++) if (p[offset+j]) return 0;
        starts[i]=offset;lengths[i]=length;offset+=padded;
    }
    uint32_t entry=word(p+16);
    if (offset!=bytes || lengths[0]<704 || !(entry&1u)) return 0;
    const uint8_t *vectors=p+64;
    if (word(vectors)!=0x24080000u || word(vectors+4)!=entry) return 0;
    for (unsigned i=1;i<176;i++) {
        uint32_t v=word(vectors+i*4);
        if (!(v&1u) || (v&~1u)<dest[0] || (v&~1u)-dest[0]>=lengths[0]) return 0;
    }
    /* Commit the plan only when every segment and vector has passed. */
    plan->entry=entry;
    for (unsigned i=0;i<2;i++) {
        plan->segments[i].source=p+starts[i];
        plan->segments[i].destination=dest[i];
        plan->segments[i].length=lengths[i];
    }
    return 1;
}

/* New Deviation native USB update package; GPL-3.0-or-later. */
#include "package.h"
#include <string.h>
static uint32_t word(const uint8_t *p)
{
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
uint32_t tx15_update_crc(uint32_t crc, const uint8_t *p, size_t bytes)
{
    crc=~crc;
    while (bytes--) {
        crc^=*p++;
        for (unsigned i=0;i<8;i++) crc=(crc>>1)^((0u-(crc&1u))&0xedb88320u);
    }
    return ~crc;
}
uint32_t tx15_update_header_validate(const uint8_t *p, uint32_t api, uint32_t abi)
{
    if (!p || memcmp(p,"ND15UPD1",8) || word(p+8)!=1 || word(p+12)!=0x54583135u
        || !word(p+24) || word(p+24)>api || !abi || word(p+28)!=abi
        || word(p+124)!=tx15_update_crc(0,p,124)) return 0;
    for (unsigned i=32;i<124;i++) if (p[i]) return 0;
    uint32_t n=word(p+16);
    return n>=64 && n<=TX15_UPDATE_IMAGE_MAX?n:0;
}
int tx15_update_package_validate(const uint8_t *p, size_t bytes, uint32_t api,
                                 uint32_t abi, struct tx15_update_package *out)
{
    if (!out) return 0;
    memset(out,0,sizeof(*out));
    if (!p || bytes<TX15_UPDATE_HEADER_BYTES || bytes>TX15_UPDATE_HEADER_BYTES+TX15_UPDATE_IMAGE_MAX) return 0;
    uint32_t n=tx15_update_header_validate(p,api,abi);
    if (!n || bytes!=TX15_UPDATE_HEADER_BYTES+n || word(p+20)!=tx15_update_crc(0,p+128,n)) return 0;
    struct tx15_boot_image boot;
    if (!tx15_boot_image_validate(p+128,n,&boot)) return 0;
    out->image=p+128; out->image_bytes=n; out->image_crc=word(p+20); out->boot=boot;
    return 1;
}

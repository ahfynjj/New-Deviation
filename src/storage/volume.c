#include "volume.h"
#include <string.h>
static uint16_t le16(const uint8_t *p) {return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static int signature(const uint8_t *b) {return b[510]==0x55 && b[511]==0xaa;}
int nd_volume_partition(const uint8_t b[512],uint64_t media,uint32_t *lba,uint64_t *span) {
    if(!signature(b) || !media || media>0x100000000ull || !lba || !span)return -1;
    *lba=0;*span=0;
    if((b[0]==0xeb || b[0]==0xe9) && (le16(b+11)==512 || !memcmp(b+3,"EXFAT   ",8))) {
        *span=media;return ND_VOLUME_SUPER;
    }
    unsigned selected=4;uint64_t starts[4]={0},ends[4]={0};
    for(unsigned i=0;i<4;i++) {
        const uint8_t *p=b+446+i*16;
        if(!p[4])continue;
        if(p[0]!=0 && p[0]!=0x80)return -1;
        uint32_t start=le32(p+8),count=le32(p+12);
        if(!start || !count || (uint64_t)start+count>media)return -1;
        starts[i]=start;ends[i]=(uint64_t)start+count;
        if(p[4]==0xee)return ND_VOLUME_GPT;
        for(unsigned j=0;j<i;j++)if(ends[j] && starts[i]<ends[j] && starts[j]<ends[i])return -1;
        if(selected==4 && (p[4]==1 || p[4]==4 || p[4]==6 || p[4]==7 || p[4]==0x0b || p[4]==0x0c || p[4]==0x0e))selected=i;
    }
    if(selected==4)return -1;
    *lba=(uint32_t)starts[selected];*span=ends[selected]-starts[selected];return ND_VOLUME_MBR;
}
int nd_volume_decode(const uint8_t b[512],uint32_t lba,uint64_t span,uint64_t media,struct nd_volume *v) {
    memset(v,0,sizeof(*v));
    if(!signature(b) || !span || media>0x100000000ull || (uint64_t)lba+span>media)return -1;
    if(!memcmp(b+3,"EXFAT   ",8)) {v->fs=ND_FS_EXFAT;v->lba=lba;return ND_FS_EXFAT;}
    unsigned spc=b[13],fats=b[16],reserved=le16(b+14),roots=le16(b+17);
    uint32_t short_total=le16(b+19),long_total=le32(b+32);
    uint32_t blocks=short_total?short_total:long_total;
    uint32_t fat16=le16(b+22),fat_blocks=fat16?fat16:le32(b+36);
    if(le16(b+11)!=512 || !spc || spc>128 || (spc&(spc-1)) || !reserved
       || !fats || fats>2 || !blocks || blocks>span || !fat_blocks
       || (short_total && long_total))return -1;
    uint64_t overhead=(uint64_t)reserved+(uint64_t)fats*fat_blocks+((uint64_t)roots*32+511)/512;
    if(overhead>=blocks)return -1;
    uint32_t clusters=(uint32_t)((blocks-overhead)/spc);
    unsigned fs=clusters<4085?ND_FS_FAT12:clusters<65525?ND_FS_FAT16:ND_FS_FAT32;
    uint64_t fat_bytes=(uint64_t)fat_blocks*512,needed=(uint64_t)clusters+2;
    uint32_t root=0;
    if(fs==ND_FS_FAT32) {
        root=le32(b+44);unsigned flags=le16(b+40);
        if(fat16 || roots || le16(b+42) || root<2 || root>=needed
           || clusters>0x0ffffff3u || fat_bytes/4<needed
           || ((flags&0x80) && (flags&15)>=fats))return -1;
    } else if(!fat16 || !roots || (fs==ND_FS_FAT16?fat_bytes/2<needed:fat_bytes*2/3<needed))return -1;
    if(!clusters)return -1;
    v->fs=fs;v->cluster_blocks=spc;v->lba=lba;v->blocks=blocks;
    v->data_lba=(uint32_t)(lba+overhead);v->clusters=clusters;v->root_cluster=root;return (int)fs;
}

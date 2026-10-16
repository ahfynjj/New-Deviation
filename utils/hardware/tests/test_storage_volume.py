"""Bounded read-only MBR/BPB inspection, including corrupt media geometry."""
import unittest
import test_controls as controls
COMMON=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "src/storage/volume.h"
static uint8_t b[512];
static void w16(unsigned p,unsigned v){b[p]=v;b[p+1]=v>>8;}
static void w32(unsigned p,uint32_t v){for(unsigned i=0;i<4;i++)b[p+i]=v>>(8*i);}
static void boot(void){
 memset(b,0,sizeof(b));b[0]=0xeb;b[2]=0x90;w16(11,512);b[13]=8;
 w16(14,32);b[16]=2;w32(32,1048576);w32(36,1024);w32(44,2);
 w16(510,0xaa55);
}
'''
class StorageVolumeTests(unittest.TestCase):
    compile_run=controls.ControlsTests.compile_run
    def test_partition_and_fat_geometry_are_bounded_by_real_media(self):
        self.compile_run(COMMON+r'''
int main(void){
 struct nd_volume v;uint32_t lba;uint64_t span;
 boot();assert(nd_volume_partition(b,2097152,&lba,&span)==ND_VOLUME_SUPER);
 assert(lba==0 && span==2097152);
 assert(nd_volume_decode(b,0,2097152,2097152,&v)==ND_FS_FAT32);
 assert(v.blocks==1048576 && v.data_lba==2080 && v.root_cluster==2 && v.cluster_blocks==8);
 memset(b,0,sizeof(b));w16(510,0xaa55);b[450]=0x0c;w32(454,2048);w32(458,1048576);
 assert(nd_volume_partition(b,2097152,&lba,&span)==ND_VOLUME_MBR && lba==2048 && span==1048576);
 boot();assert(nd_volume_decode(b,lba,span,2097152,&v)==ND_FS_FAT32 && v.data_lba==4128);
 boot();w16(17,512);w16(22,128);w32(36,0);w32(32,65536);b[13]=4;
 assert(nd_volume_decode(b,0,65536,65536,&v)==ND_FS_FAT16);
 boot();w16(17,224);w16(22,9);w16(19,2880);w32(32,0);b[13]=1;
 assert(nd_volume_decode(b,0,2880,2880,&v)==ND_FS_FAT12);
 memset(b,0,sizeof(b));b[0]=0xeb;memcpy(b+3,"EXFAT   ",8);w16(510,0xaa55);
 assert(nd_volume_decode(b,0,1048576,1048576,&v)==ND_FS_EXFAT);
 return 0;
}''',['src/storage/volume.c'])

    def test_malformed_partitions_bpb_and_overflows_are_rejected(self):
        self.compile_run(COMMON+r'''
int main(void){
 struct nd_volume v;uint32_t lba;uint64_t span;
 boot();b[13]=3;assert(nd_volume_decode(b,0,2097152,2097152,&v)<0);
 boot();w16(11,4096);assert(nd_volume_decode(b,0,2097152,2097152,&v)<0);
 boot();w32(36,0xffffffff);assert(nd_volume_decode(b,0,2097152,2097152,&v)<0);
 boot();w32(36,1);assert(nd_volume_decode(b,0,2097152,2097152,&v)<0); /* FAT cannot hold clusters. */
 boot();w32(44,0xffffffff);assert(nd_volume_decode(b,0,2097152,2097152,&v)<0);
 boot();assert(nd_volume_decode(b,0,100,2097152,&v)<0);
 boot();assert(nd_volume_decode(b,0xfffffff0,2097152,0x100000000ull,&v)<0);
 boot();b[510]=0;assert(nd_volume_decode(b,0,2097152,2097152,&v)<0);
 memset(b,0,sizeof(b));w16(510,0xaa55);b[450]=0x0c;w32(454,0xfffffff0);w32(458,0x100);
 assert(nd_volume_partition(b,0x100000000ull,&lba,&span)<0);
 w32(454,2048);w32(458,1000);b[446]=1;
 assert(nd_volume_partition(b,2097152,&lba,&span)<0);
 b[446]=0;b[450]=0xee;
 assert(nd_volume_partition(b,2097152,&lba,&span)==ND_VOLUME_GPT);
 b[450]=0x0c;b[466]=0x0c;w32(470,2500);w32(474,1000);
 assert(nd_volume_partition(b,2097152,&lba,&span)<0); /* Overlapping partitions. */
 return 0;
}''',['src/storage/volume.c'])

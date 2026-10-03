#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hardware/tx15/boot/loader.h"
static unsigned reads,copies,checks,mode;
static unsigned char *image;
static size_t bytes;
static unsigned char code[0x6c000],resources[0x80000];
static int read_image(void *ctx,uint32_t address,uint8_t *dst,uint32_t count) {
    (void)ctx;reads++;
    assert(address>=0x100000 && address-0x100000<bytes);
    assert(count<=bytes-(address-0x100000));
    if(mode==1 && reads==2)return 0;
    memcpy(dst,image+address-0x100000,count);return 1;
}
static uint8_t *destination(const struct tx15_boot_segment *s) {
    assert((s->destination==0x24010000 && s->length<=sizeof(code)) ||
           (s->destination==0xd0080000 && s->length<=sizeof(resources)));
    return s->destination==0x24010000?code:resources;
}
static int copy(void *ctx,const struct tx15_boot_segment *s) {
    (void)ctx;copies++;
    if(mode==2 && copies==2)return 0;
    memcpy(destination(s),s->source,s->length);return 1;
}
static int verify(void *ctx,const struct tx15_boot_segment *s) {
    (void)ctx;checks++;
    if(mode==3)return 0;
    return !memcmp(destination(s),s->source,s->length);
}
int main(int argc,char **argv) {
    assert(argc==3);mode=(unsigned)atoi(argv[2]);
    FILE *f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);bytes=(size_t)ftell(f);rewind(f);
    image=malloc(bytes);assert(image && fread(image,1,bytes,f)==bytes);fclose(f);
    uint8_t *staging=malloc(TX15_BOOT_MAX_BYTES);assert(staging);
    struct tx15_boot_io io={NULL,read_image,copy,verify};uint32_t entry=99;
    enum tx15_boot_load_result result=tx15_boot_load(&io,0x100000,0x100000,staging,TX15_BOOT_MAX_BYTES,&entry);
    if(mode==0) {
        assert(result==TX15_BOOT_LOAD_OK && entry==0x240102c1 && copies==2 && checks==2);
        assert(reads>=2);
    } else {
        assert(result!=TX15_BOOT_LOAD_OK && entry==0);
        if(mode==1 || mode>=4) assert(!copies && !checks);
        if(mode==2)assert(copies==2 && checks==1);
        if(mode==3)assert(copies==1 && checks==1);
    }
    entry=99;unsigned before=reads;
    assert(tx15_boot_load(&io,0xfff000,0x100000,staging,TX15_BOOT_MAX_BYTES,&entry)==TX15_BOOT_LOAD_BAD_ARGUMENT);
    assert(entry==0 && reads==before);
    assert(tx15_boot_load(&io,0x100000,64,staging,TX15_BOOT_MAX_BYTES,&entry)!=TX15_BOOT_LOAD_OK);
    assert(tx15_boot_load(&io,0x100000,0x100000,staging,63,&entry)==TX15_BOOT_LOAD_BAD_ARGUMENT);
    io.verify=NULL;
    assert(tx15_boot_load(&io,0x100000,0x100000,staging,TX15_BOOT_MAX_BYTES,&entry)==TX15_BOOT_LOAD_BAD_ARGUMENT);
    free(staging);free(image);return 0;
}

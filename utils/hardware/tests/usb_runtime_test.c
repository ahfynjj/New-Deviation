#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../../hardware/tx15/usb_update/runtime.h"
static uint8_t nor[0x100000],shadow[0x100000],staging[0xec0c0],uid[12]={1};
static struct tx15_update_runtime runtime;
static unsigned writes,services;
static struct tx15_frame commit;
static int observation(void *ctx,struct tx15_update_flash_info *out)
{ (void)ctx;*out=(struct tx15_update_flash_info){.jedec=0xc84018,.capacity=0x1000000,.page_bytes=256,.erase_bytes=4096,.sfdp_valid=1};return 1; }
static int read_nor(void *ctx,uint32_t off,uint8_t *p,size_t n)
{ (void)ctx;assert(off+n<=sizeof(nor));memcpy(p,nor+off,n);return 1; }
static int erase(void *ctx,uint32_t off)
{ (void)ctx;assert(off+4096<=0xf0000);memset(nor+off,0xff,4096);writes++;return 1; }
static int program(void *ctx,uint32_t off,const uint8_t *p,size_t n)
{ (void)ctx;assert(off+n<=0xf0000);memcpy(nor+off,p,n);writes++;return 1; }
static void service(void *ctx)
{
    (void)ctx;services++;struct tx15_frame f={.kind=TX15_BEGIN,.session=123,.sequence=1,.bytes=128},out;
    memset(f.payload,0xcc,128);tx15_update_runtime_request(&runtime,&f,&out);
    assert(tx15_update_word(out.payload+4));
    f.kind=TX15_ABORT;f.bytes=0;tx15_update_runtime_request(&runtime,&f,&out);
    assert(tx15_update_word(out.payload+4));
    unsigned before=writes;tx15_update_runtime_request(&runtime,&commit,&out);assert(writes==before);
}
static const struct tx15_update_io io={NULL,observation,read_nor,erase,program,service};
static void ready(const uint8_t *data,size_t n)
{
    struct tx15_frame f={.kind=TX15_BEGIN,.session=123,.sequence=1,.bytes=128},out;
    memcpy(f.payload,data,128);tx15_update_runtime_request(&runtime,&f,&out);assert(!tx15_update_word(out.payload+4));
    f.kind=TX15_DATA;f.sequence=2;f.bytes=(uint32_t)n-128;memcpy(f.payload,data+128,f.bytes);
    tx15_update_runtime_request(&runtime,&f,&out);assert(!tx15_update_word(out.payload+4));
    f.kind=TX15_FINALIZE;f.sequence=3;f.bytes=0;tx15_update_runtime_request(&runtime,&f,&out);
    assert(tx15_update_word(out.payload)==TX15_READY && !tx15_update_word(out.payload+4));
}
int main(int argc,char **argv)
{
    assert(argc==2);FILE *file=fopen(argv[1],"rb");assert(file);fseek(file,0,SEEK_END);long n=ftell(file);rewind(file);
    uint8_t *data=malloc((size_t)n);assert(data && fread(data,1,(size_t)n,file)==(size_t)n);fclose(file);
    tx15_update_runtime_init(&runtime,&io,staging,sizeof(staging),shadow,sizeof(shadow),uid,123,0);
    ready(data,(size_t)n);struct tx15_frame out;
    commit=(struct tx15_frame){.kind=TX15_COMMIT,.session=123,.sequence=4,.bytes=20};
    memcpy(commit.payload,uid,12);tx15_update_put_word(commit.payload+12,(uint32_t)n-128);
    tx15_update_put_word(commit.payload+16,tx15_update_word(data+20));
    commit.payload[0]=2;tx15_update_runtime_request(&runtime,&commit,&out);assert(!writes && tx15_update_word(out.payload+4));
    commit.payload[0]=1;runtime.synchronized=0;tx15_update_runtime_request(&runtime,&commit,&out);assert(!writes && tx15_update_word(out.payload+4));
    runtime.synchronized=1;tx15_update_runtime_request(&runtime,&commit,&out);
    assert(!tx15_update_word(out.payload+4) && runtime.committed && !writes);
    assert(!memcmp(staging,data,(size_t)n));
    /* Disconnect/reconnect cannot cancel or mutate the already frozen transaction. */
    tx15_update_runtime_session(&runtime,456);
    while (tx15_update_runtime_step(&runtime)==0) {}
    assert(runtime.tx.status.state==TX15_DONE && writes && services>1000);
    assert(!memcmp(nor,data+128,(size_t)n-128));unsigned before=writes;
    tx15_update_runtime_request(&runtime,&commit,&out);assert(writes==before);
    tx15_update_runtime_init(&runtime,&io,staging,sizeof(staging),shadow,sizeof(shadow),uid,123,1);
    ready(data,(size_t)n);runtime.synchronized=1;
    tx15_update_runtime_request(&runtime,&commit,&out);assert(writes==before && tx15_update_word(out.payload+4)==TX15_READ_ONLY);
    free(data);return 0;
}

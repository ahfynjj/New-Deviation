#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../../hardware/tx15/usb_update/transaction.h"
static uint8_t nor[0x100000],original[0x100000],shadow[0x100000];
static int fail_at,mutations,header_written,services,corrupt,protected;
static int observe(void *ctx,struct tx15_update_flash_info *out)
{
    (void)ctx;*out=(struct tx15_update_flash_info){.jedec=0xc84018,.capacity=0x1000000,
        .page_bytes=256,.erase_bytes=4096,.sfdp_valid=1,.sr1=protected?4:0};return 1;
}
static int read_nor(void *ctx,uint32_t at,uint8_t *p,size_t n)
{
    (void)ctx;assert(at<sizeof(nor) && n<=sizeof(nor)-at);memcpy(p,nor+at,n);
    if (corrupt && mutations && at<=0xf0000 && at+n>0xf0000) p[0xf0000-at]^=1;
    return 1;
}
static int erase(void *ctx,uint32_t at)
{
    (void)ctx;assert(at%4096==0 && at+4096<=0xf0000);assert(!header_written);
    if (++mutations==fail_at)return 0;
    memset(nor+at,0xff,4096);return 1;
}
static int program(void *ctx,uint32_t at,const uint8_t *p,size_t n)
{
    (void)ctx;assert(n && n<=256-at%256 && at+n<=0xf0000);assert(!header_written);
    if (++mutations==fail_at)return 0;
    for (size_t i=0;i<n;i++) { assert((nor[at+i]&p[i])==p[i]);nor[at+i]&=p[i]; }
    if (!at) { assert(n==64);header_written=1; }
    return 1;
}
static void service(void *ctx) { (void)ctx;services++; }
static const struct tx15_update_io io={NULL,observe,read_nor,erase,program,service};
static void reset(int fail,int damage,int protect)
{
    for (unsigned i=0;i<sizeof(nor);i++) original[i]=nor[i]=(uint8_t)(i*13u+7u);
    memset(shadow,0,sizeof(shadow));fail_at=fail;corrupt=damage;protected=protect;
    mutations=header_written=services=0;
}
int main(int argc,char **argv)
{
    if (argc!=2)return 2;
    FILE *f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);
    uint8_t *data=malloc((size_t)n);assert(data && fread(data,1,(size_t)n,f)==(size_t)n);fclose(f);
    struct tx15_update_package package;assert(tx15_update_package_validate(data,(size_t)n,1,1,&package));
    struct tx15_update_tx tx;reset(0,0,0);
    assert(tx15_update_tx_prepare(&tx,&io,&package,shadow,sizeof(shadow)));
    assert(!mutations);int result=0;unsigned steps=0;
    while (!result && steps++<2000) result=tx15_update_tx_step(&tx);
    assert(result==1 && tx.status.state==TX15_DONE && tx.status.verification_flags==1 && header_written);
    assert(!memcmp(nor,package.image,package.image_bytes));
    assert(!memcmp(nor+package.image_bytes,original+package.image_bytes,sizeof(nor)-package.image_bytes));
    assert(services>1000);int actions=mutations;
    assert(tx15_update_tx_step(&tx)==1 && mutations==actions);
    for (int failed=1;failed<=actions;failed++) {
        reset(failed,0,0);assert(tx15_update_tx_prepare(&tx,&io,&package,shadow,sizeof(shadow)));
        result=0;steps=0;while (!result && steps++<2000)result=tx15_update_tx_step(&tx);
        assert(result==-1 && tx.status.state==TX15_ERROR && !tx.status.verification_flags);
        assert(!memcmp(nor+0xf0000,original+0xf0000,65536));
    }
    reset(0,1,0);assert(tx15_update_tx_prepare(&tx,&io,&package,shadow,sizeof(shadow)));
    result=0;steps=0;while (!result && steps++<2000)result=tx15_update_tx_step(&tx);
    assert(result==-1 && !tx.status.verification_flags);
    reset(0,0,1);assert(!tx15_update_tx_prepare(&tx,&io,&package,shadow,sizeof(shadow)) && !mutations);
    reset(0,0,0);assert(!tx15_update_tx_prepare(&tx,&io,&package,shadow,128) && !mutations);
    data[128+64]^=1;assert(!tx15_update_tx_prepare(&tx,&io,&package,shadow,sizeof(shadow)) && !mutations);
    free(data);return 0;
}

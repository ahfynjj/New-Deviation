#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
static uint32_t rd(uint32_t);
static void wr(uint32_t,uint32_t);
static uint8_t rd8(uint32_t);
static void wr8(uint32_t,uint8_t);
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_READ8(a) rd8(a)
#define TX15_WRITE8(a,v) wr8(a,v)
#include "../../../hardware/tx15/usb_update/nor.c"
static uint8_t flash[0x100000],sfdp[1024],fake_status[3];
static unsigned opcode,cursor,address,length,wren,erases,programs,services,now;
static unsigned stall,no_wel,forever_busy,invalid_config,reenter,busy_after,seen_busy;
static struct tx15_update_nor nor;
static uint32_t rd(uint32_t a) {
    if(a==0x580244d4u)return 0x4000;
    if(a==QSPI)return invalid_config?0:0x0f000001u;
    if(a==QSPI+4)return 0x00170300u;
    if(a==QSPI+8)return stall?0x20:(opcode==2?6:0x102); /* TX space vs RX data */
    assert(0);return 0;
}
static void wr(uint32_t a,uint32_t v) {
    if(a==QSPI+12)return;
    if(a==QSPI+16){length=v+1;return;}
    if(a==QSPI+20){
        opcode=v&255;cursor=0;
        uint32_t expected=opcode|0x100u;
        if(opcode==3||opcode==0x20||opcode==2||opcode==0x5a)expected|=0x2400;
        if(opcode!=6 && opcode!=0x20)expected|=0x1000000;
        if(opcode!=6 && opcode!=0x20 && opcode!=2)expected|=0x4000000;
        if(opcode==0x5a)expected|=8u<<18;
        assert(v==expected);
        if(opcode==6){wren++;if(!no_wel)fake_status[0]|=2;}
        assert(opcode==6||opcode==5||opcode==0x35||opcode==0x15||opcode==0x9f
            ||opcode==0x5a||opcode==3||opcode==0x20||opcode==2);
        return;
    }
    if(a==QSPI+24){
        address=v;
        if(opcode==0x20){assert(fake_status[0]&2);assert(v<0xf0000 && !(v%4096));
            memset(flash+v,255,4096);fake_status[0]&=~2;erases++;if(busy_after)forever_busy=1;}
        if(opcode==2){assert(fake_status[0]&2);assert(v<0xf0000 && length<=256-v%256);
            fake_status[0]&=~2;programs++;if(busy_after)forever_busy=1;}
        return;
    }
    assert(0);
}
static uint8_t rd8(uint32_t a) {
    assert(a==QSPI+32);
    if(opcode==5){if(forever_busy)seen_busy++;return fake_status[0]|(forever_busy?1:0);}
    if(opcode==0x35)return fake_status[1];
    if(opcode==0x15)return fake_status[2];
    if(opcode==0x9f){static const uint8_t id[]={0xc8,0x40,0x18};return id[cursor++];}
    if(opcode==0x5a)return sfdp[cursor++];
    assert(opcode==3);return flash[address+cursor++];
}
static void wr8(uint32_t a,uint8_t v) {
    assert(a==QSPI+32 && opcode==2 && cursor<length);
    flash[address+cursor++] &= v;
}
static uint32_t ticks(void *ctx){(void)ctx;return now;}
static void fake_service(void *ctx){
    (void)ctx;services++;now++;
    if(reenter){uint8_t x;assert(!tx15_update_nor_read(&nor,0,&x,1));}
}
int main(int argc,char **argv) {
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);
    fread(sfdp,1,sizeof(sfdp),f);fclose(f);memset(flash,255,sizeof(flash));
    assert(tx15_update_nor_init(&nor,fake_service,ticks,0,1000));
    struct tx15_update_flash_info info;
    assert(tx15_update_nor_observe(&nor,&info));assert(info.sfdp_valid);
    uint8_t page[256];memset(page,0x55,sizeof(page));
    assert(!tx15_update_nor_erase4k(&nor,1));
    assert(!tx15_update_nor_erase4k(&nor,0xf0000));
    assert(!tx15_update_nor_program(&nor,255,page,2));
    assert(!tx15_update_nor_program(&nor,0xf0000,page,256));
    assert(!tx15_update_nor_program(&nor,0,page,257));
    assert(!tx15_update_nor_read(&nor,0x100000,page,1));
    assert(wren==0);
    fake_status[0]=4;assert(!tx15_update_nor_erase4k(&nor,0));assert(wren==0);
    fake_status[0]=0;assert(tx15_update_nor_init(&nor,fake_service,ticks,0,1000));
    reenter=1;
    assert(tx15_update_nor_erase4k(&nor,0xeF000));
    assert(tx15_update_nor_program(&nor,0xeff00,page,256));
    uint8_t readback[256];assert(tx15_update_nor_read(&nor,0xeff00,readback,256));
    assert(!memcmp(page,readback,256));assert(erases==1 && programs==1 && services);
    reenter=0;no_wel=1;
    assert(!tx15_update_nor_erase4k(&nor,0));assert(erases==1);
    no_wel=0;assert(tx15_update_nor_init(&nor,fake_service,ticks,0,1000));
    forever_busy=1;assert(!tx15_update_nor_program(&nor,0,page,256));assert(programs==1);
    forever_busy=0;assert(tx15_update_nor_init(&nor,fake_service,ticks,0,1000));
    busy_after=1;unsigned prior=services;
    assert(!tx15_update_nor_program(&nor,0,page,256));assert(programs==2);
    assert(services>=prior+100 && seen_busy>=100 && !nor.ready);
    busy_after=forever_busy=0;assert(tx15_update_nor_init(&nor,fake_service,ticks,0,1000));
    stall=1;assert(!tx15_update_nor_read(&nor,0,page,256));
    stall=0;invalid_config=1;assert(!tx15_update_nor_init(&nor,fake_service,ticks,0,1000));
    puts("NOR boundaries, commands, protection, timeout and reentry passed");return 0;
}

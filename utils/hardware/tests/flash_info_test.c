#include <assert.h>
#include <stdint.h>
static uint32_t q[9];
static unsigned commands,left,pos,reads,opcode;
static unsigned busy,error,bad_clock;
static uint32_t rd(uint32_t a) {
    assert(++reads<10000);
    if(a==0x580244d4)return bad_clock?0:0x4000;
    assert(a>=0x52005000 && a<=0x52005020);
    if(a==0x52005008)return error?1:(busy?0x20:(left?0x120:2));
    return q[(a-0x52005000)/4];
}
static void begin(void) {left=q[4]+1;pos=0;commands++;}
static void wr(uint32_t a,uint32_t v) {
    assert(a==0x5200500c || a==0x52005010 || a==0x52005014 || a==0x52005018);
    q[(a-0x52005000)/4]=v;
    if(a==0x52005014) {
        opcode=v&255;
        assert(opcode==5 || opcode==0x35 || opcode==0x15 || opcode==0x5a);
        if(opcode==0x5a)assert(v==0x0520255a);
        else {assert(v==(0x05000100|opcode));begin();}
    }
    if(a==0x52005018){assert(v==0);begin();}
}
static uint8_t rd8(uint32_t a) {
    assert(a==0x52005020 && left);left--;
    if(opcode==0x5a)return (uint8_t)pos++;
    return opcode;
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_READ8(a) rd8(a)
#include "hardware/tx15/boot/flash_info.c"
static void reset(void) {
    for(unsigned i=0;i<9;i++)q[i]=0;
    q[0]=0x0f000001;q[1]=0x00170300;
    commands=left=pos=reads=opcode=busy=error=bad_clock=0;
}
int main(void) {
    struct tx15_flash_info info;
    reset();assert(tx15_flash_info_read(0xc84018,&info,20)==TX15_QSPI_OK);
    assert(commands==4 && info.status[0]==5 && info.status[1]==0x35 && info.status[2]==0x15);
    for(unsigned i=0;i<1024;i++)assert(info.sfdp[i]==(uint8_t)i);
    reset();assert(tx15_flash_info_read(0xef4018,&info,20)==TX15_QSPI_BAD_ID);assert(!commands);
    reset();bad_clock=1;assert(tx15_flash_info_read(0xc84018,&info,20)==TX15_QSPI_BAD_STATE);assert(!commands);
    reset();busy=1;assert(tx15_flash_info_read(0xc84018,&info,2)==TX15_QSPI_TIMEOUT);assert(!commands);
    reset();error=1;assert(tx15_flash_info_read(0xc84018,&info,2)==TX15_QSPI_TRANSFER_ERROR);assert(!commands);
    reset();assert(tx15_flash_info_read(0xc84018,0,2)==TX15_QSPI_BAD_STATE);assert(!commands);
}

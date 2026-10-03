#include <assert.h>
#include <stdint.h>
static uint32_t ahb3,ahb4,rst,q[8],f[10],g[10],cr,cfgr,d1,kernel;
static unsigned commands,writes,reads,left,position;
static int stuck,transfer_error,invalid_id;
static unsigned fault_mode,fault_command;
static uint32_t rd(uint32_t a) {
    assert(++reads<10000);
    if(a==0x58024400) return cr;
    if(a==0x58024410) return cfgr;
    if(a==0x58024418) return d1;
    if(a==0x58024428) return 0xc2;
    if(a==0x5802442c) return 0x10008;
    if(a==0x58024430) return 0x23f;
    if(a==0x5802444c) return kernel;
    if(a==0x580244d4) return ahb3;
    if(a==0x580244e0) return ahb4;
    if(a==0x5802447c) return rst;
    if(a>=0x58021400 && a<0x58021428) return f[(a-0x58021400)/4];
    if(a>=0x58021800 && a<0x58021828) return g[(a-0x58021800)/4];
    assert(a>=0x52005000 && a<0x52005020 && (ahb3&0x4000));
    if(a==0x52005008) {
        if(stuck) return 0x20;
        if(transfer_error) return 1;
        if(fault_mode && commands>=fault_command) {
            if(fault_mode==1 || (fault_mode==2 && position>=1))return fault_mode==2?1:0x20;
            if(!left && fault_mode==3)return 0;
            if(!left && fault_mode==4)return 0x22;
        }
        return left?0x120:2; // one FIFO byte available or transfer done
    }
    return q[(a-0x52005000)/4];
}
static void begin(void) { left=q[4]+1;position=0;commands++; }
static void wr(uint32_t a,uint32_t v) {
    writes++;
    if(a==0x580244d4) { ahb3=v;return; }
    if(a==0x580244e0) { ahb4=v;return; }
    if(a==0x5802447c) { rst=v;if(v&0x4000) {for(unsigned i=0;i<8;i++)q[i]=0;left=0;}return; }
    if(a>=0x58021400 && a<0x58021428) {f[(a-0x58021400)/4]=v;return;}
    if(a>=0x58021800 && a<0x58021828) {g[(a-0x58021800)/4]=v;return;}
    assert(a>=0x52005000 && a<0x52005020 && (ahb3&0x4000));
    if(a==0x52005014) {
        assert(v==0x0500019f || v==0x05002503); // only JEDEC / 24-bit Read
        assert(q[0]==0x0f000001 && q[1]==0x00170300);
        if((v&255)==0x9f)begin();
    }
    if(a==0x52005018) {assert(v<0x1000000);begin();}
    q[(a-0x52005000)/4]=v;
}
static uint8_t rd8(uint32_t a) {
    assert(a==0x52005020 && left);
    left--;
    if((q[5]&255)==0x9f) {
        static const uint8_t id[]={0xef,0x40,0x18};
        return invalid_id?0xff:id[position++];
    }
    return (uint8_t)(q[6]+position++);
}
#define TX15_READ32(a) rd(a)
#define TX15_WRITE32(a,v) wr(a,v)
#define TX15_READ8(a) rd8(a)
#include "hardware/tx15/boot/qspi.c"
static void reset(void) {
    ahb3=0x1010;ahb4=0x9f;rst=0;cr=0x3034025;cfgr=0x1b;d1=0x48;kernel=0;
    for(unsigned i=0;i<8;i++)q[i]=0;
    for(unsigned i=0;i<10;i++)f[i]=g[i]=0xcccccccc;
    commands=writes=reads=left=position=0;stuck=transfer_error=invalid_id=0;
    fault_mode=fault_command=0;
}
int main(void) {
    uint32_t id;uint8_t bytes[64];
    reset();assert(tx15_boot_qspi_init(&id,20)==TX15_QSPI_OK);assert(id==0xef4018);
    assert(ahb3==0x5010 && ahb4==0xff && !(rst&0x4000));
    assert(f[8]==0x99cccccc && f[9]==0xccccc9aa && g[8]==0xcacccccc);
    assert(tx15_boot_qspi_read(128,bytes,64,20)==TX15_QSPI_OK);
    for(unsigned i=0;i<64;i++)assert(bytes[i]==(uint8_t)(128+i));
    unsigned old=commands;
    assert(tx15_boot_qspi_read(0xffffff,bytes,2,20)==TX15_QSPI_BAD_STATE);
    assert(tx15_boot_qspi_read(0,0,1,20)==TX15_QSPI_BAD_STATE);assert(commands==old);
    tx15_boot_qspi_stop();assert(ahb3==0x1010 && !(rst&0x4000));
    reset();ahb3|=0x4000;assert(tx15_boot_qspi_init(&id,20)==TX15_QSPI_BAD_STATE);assert(!writes);
    reset();cfgr=0;assert(tx15_boot_qspi_init(&id,20)==TX15_QSPI_BAD_STATE);assert(!writes);
    reset();stuck=1;assert(tx15_boot_qspi_init(&id,20)==TX15_QSPI_TIMEOUT);assert(!id);tx15_boot_qspi_stop();
    reset();transfer_error=1;assert(tx15_boot_qspi_init(&id,20)==TX15_QSPI_TRANSFER_ERROR);assert(!id);tx15_boot_qspi_stop();
    reset();invalid_id=1;assert(tx15_boot_qspi_init(&id,20)==TX15_QSPI_BAD_ID);assert(!id);tx15_boot_qspi_stop();
    for(unsigned mode=1;mode<=4;mode++) {
        reset();fault_mode=mode;fault_command=1;
        assert(tx15_boot_qspi_init(&id,20)==(mode==2?TX15_QSPI_TRANSFER_ERROR:TX15_QSPI_TIMEOUT));
        assert(commands==1 && !id);tx15_boot_qspi_stop();
        fault_mode=0;assert(tx15_boot_qspi_init(&id,20)==TX15_QSPI_OK);tx15_boot_qspi_stop();
    }
    reset();assert(tx15_boot_qspi_init(&id,20)==TX15_QSPI_OK);
    fault_mode=2;fault_command=2;
    assert(tx15_boot_qspi_read(128,bytes,64,20)==TX15_QSPI_TRANSFER_ERROR);
    assert(commands==2 && bytes[0]==128);
    assert(tx15_boot_qspi_read(128,bytes,64,20)==TX15_QSPI_BAD_STATE);assert(commands==2);
    tx15_boot_qspi_stop();fault_mode=0;
    assert(tx15_boot_qspi_init(&id,20)==TX15_QSPI_OK);tx15_boot_qspi_stop();
    reset();assert(tx15_boot_qspi_init(&id,0)==TX15_QSPI_BAD_STATE);assert(!writes);
}

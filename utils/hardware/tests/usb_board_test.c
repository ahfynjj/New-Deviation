#include <assert.h>
#include <stdint.h>
#include <string.h>
struct reg { uint32_t a,v; };
static struct reg regs[128];static unsigned count;static int ready=1,rng=1;
static uint32_t read32(uint32_t a)
{
    if (a==0x48021804u) return rng==1?1u:rng==2?2u:0u;
    if (a==0x48021808u) { static unsigned random=123;return ++random; }
    for (unsigned i=0;i<count;i++) if (regs[i].a==a) return regs[i].v;
    return 0;
}
static void write32(uint32_t a,uint32_t v)
{
    /* Init must never touch PLL1/3 or the power-hold latch/mode. */
    assert(a!=0x58024410u && a!=0x58024428u && a!=0x5802442cu
           && a!=0x58024430u && a!=0x58024440u && a!=0x58024444u);
    if (a==0x58024400u) assert((v&~0x1000u)==read32(a));
    if (a==0x58021c00u) assert((v&(3u<<24))==(read32(a)&(3u<<24)));
    if (a==0x58021c18u) assert(!(v&0x10001000u));
    if (a==0x58024400u && ready) v|=0x2000u;
    if (a==0x5802480cu && ready) v|=1u<<26;
    for (unsigned i=0;i<count;i++) if (regs[i].a==a) { regs[i].v=v;return; }
    assert(count<128);regs[count++]=(struct reg){a,v};
}
#define TX15_READ32(a) read32(a)
#define TX15_WRITE32(a,v) write32(a,v)
#include "../../../hardware/tx15/usb_update/usb_hw.c"
int main(void)
{
    regs[count++]=(struct reg){0x58021c00u,1u<<24};
    assert(tx15_usb_hw_init(100)==0);
    assert((read32(0x58024454u)&(3u<<20))==(3u<<20));
    assert(((read32(0x58020024u)>>12)&0xffu)==0xaau);
    assert(!(read32(0x58020414u)&(1u<<13)) && !(read32(0x58020c14u)&(1u<<4)));
    uint64_t session=0;assert(tx15_usb_hw_session(&session,100)==0 && session);
    rng=2;session=0xa5;assert(tx15_usb_hw_session(&session,100)!=0 && !session);
    rng=0;assert(tx15_usb_hw_session(&session,1)!=0);
    rng=1;assert(tx15_usb_hw_session(&session,1)!=0 && !session);
    ready=0;count=0;assert(tx15_usb_hw_init(3)!=0);
    ready=1;assert(tx15_usb_hw_init(0)!=0);
    return 0;
}

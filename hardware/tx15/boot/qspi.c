/* New Deviation native TX15 read-only SPI NOR bootstrap; GPL-3.0-or-later. */
#include "qspi.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a)=(v))
#endif
#ifndef TX15_READ8
#define TX15_READ8(a) (*(volatile uint8_t *)(a))
#endif
#define QSPI 0x52005000u
#define AHB3 0x580244d4u
#define AHB4 0x580244e0u
#define RESET 0x5802447cu
static unsigned owned,identified;
static void modify(uint32_t a,uint32_t mask,uint32_t value)
{
    TX15_WRITE32(a,(TX15_READ32(a)&~mask)|value);
}
static void pin(uint32_t base,unsigned n,unsigned af)
{
    unsigned shift=n*2;
    modify(base+0x20+(n/8)*4,15u<<((n%8)*4),af<<((n%8)*4));
    modify(base+4,1u<<n,0);
    modify(base+8,3u<<shift,3u<<shift);
    modify(base+12,3u<<shift,(n==6 && base==0x58021800u)?1u<<shift:0);
    modify(base,3u<<shift,2u<<shift);
}
static enum tx15_qspi_result idle(uint32_t budget)
{
    while (budget--) {
        uint32_t status=TX15_READ32(QSPI+8);
        if (status&0x11u) return TX15_QSPI_TRANSFER_ERROR;
        if (!(status&0x20u)) return TX15_QSPI_OK;
    }
    return TX15_QSPI_TIMEOUT;
}
static enum tx15_qspi_result receive(unsigned opcode,uint32_t offset,uint8_t *dst,uint32_t bytes,uint32_t budget)
{
    enum tx15_qspi_result status=idle(budget);
    if (status!=TX15_QSPI_OK) return status;
    TX15_WRITE32(QSPI+12,0x1bu);
    TX15_WRITE32(QSPI+16,bytes-1);
    /* IMODE/DMODE=1 line; indirect read. A 24-bit address only for data. */
    TX15_WRITE32(QSPI+20,opcode==0x9f?0x0500019fu:0x05002503u);
    if (opcode==0x03) TX15_WRITE32(QSPI+24,offset);
    for (uint32_t i=0;i<bytes;i++) {
        unsigned available=0;
        for (uint32_t remaining=budget;remaining;remaining--) {
            uint32_t sr=TX15_READ32(QSPI+8);
            if (sr&0x11u) return TX15_QSPI_TRANSFER_ERROR;
            if (sr&0x3f00u) { available=1;break; }
        }
        if (!available) return TX15_QSPI_TIMEOUT;
        dst[i]=TX15_READ8(QSPI+32);
    }
    for (uint32_t remaining=budget;remaining;remaining--) {
        uint32_t sr=TX15_READ32(QSPI+8);
        if (sr&0x11u) return TX15_QSPI_TRANSFER_ERROR;
        if ((sr&0x22u)==2u) {
            TX15_WRITE32(QSPI+12,0x1bu);return TX15_QSPI_OK;
        }
    }
    return TX15_QSPI_TIMEOUT;
}
enum tx15_qspi_result tx15_boot_qspi_init(uint32_t *id,uint32_t budget)
{
    if (id) *id=0;
    if (!id || !budget || owned || (TX15_READ32(AHB3)&0x4000u)
            || (TX15_READ32(RESET)&0x4000u)
            || (TX15_READ32(0x58024400u)&0x3f0f001du)!=0x3030005u
            || (TX15_READ32(0x58024410u)&0x3fu)!=0x1bu
            || (TX15_READ32(0x58024418u)&0xf7fu)!=0x48u
            || (TX15_READ32(0x58024428u)&0x3f3u)!=0xc2u
            || (TX15_READ32(0x5802442cu)&0x7000fu)!=0x10008u
            || (TX15_READ32(0x58024430u)&0xffffu)!=0x23fu
            || (TX15_READ32(0x5802444cu)&0x30u)) return TX15_QSPI_BAD_STATE;
    TX15_WRITE32(AHB4,TX15_READ32(AHB4)|0x60u);(void)TX15_READ32(AHB4);
    /* Board AFs confirmed against this TX15's live GPIO readback. */
    TX15_WRITE32(0x58021818u,1u<<6);
    pin(0x58021800u,6,10);
    for (unsigned n=6;n<=10;n++) pin(0x58021400u,n,n==8||n==9?10:9);
    TX15_WRITE32(AHB3,TX15_READ32(AHB3)|0x4000u);(void)TX15_READ32(AHB3);
    owned=1;identified=0;
    modify(RESET,0x4000u,0x4000u);modify(RESET,0x4000u,0);
    TX15_WRITE32(QSPI+4,0x00170300u); // 16MiB address window, CS high 4 cycles
    TX15_WRITE32(QSPI,0x0f000001u); // HCLK64 / 16 = 4MHz; FIFO threshold 1
    uint8_t bytes[3];
    enum tx15_qspi_result result=receive(0x9f,0,bytes,3,budget);
    if (result!=TX15_QSPI_OK) return result;
    uint32_t value=(uint32_t)bytes[0]<<16|(uint32_t)bytes[1]<<8|bytes[2];
    if (!bytes[0] || bytes[0]==0xff || !bytes[2] || bytes[2]==0xff) return TX15_QSPI_BAD_ID;
    *id=value;identified=1;return TX15_QSPI_OK;
}
enum tx15_qspi_result tx15_boot_qspi_read(uint32_t offset,uint8_t *dst,uint32_t bytes,uint32_t budget)
{
    if (!owned || !identified || !dst || !bytes || !budget || offset>=0x1000000u
            || bytes>0x1000000u-offset || !(TX15_READ32(AHB3)&0x4000u)) return TX15_QSPI_BAD_STATE;
    enum tx15_qspi_result result=receive(0x03,offset,dst,bytes,budget);
    if (result!=TX15_QSPI_OK) identified=0;
    return result;
}
void tx15_boot_qspi_stop(void)
{
    if (owned) {
        modify(RESET,0x4000u,0x4000u);modify(RESET,0x4000u,0);
        modify(AHB3,0x4000u,0);
    }
    owned=identified=0;
}

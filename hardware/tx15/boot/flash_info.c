/* New Deviation TX15 read-only installation prerequisites; GPL-3.0-or-later. */
#include "flash_info.h"
#ifndef TX15_READ32
#define TX15_READ32(a) (*(volatile uint32_t *)(a))
#define TX15_WRITE32(a,v) (*(volatile uint32_t *)(a)=(v))
#define TX15_READ8(a) (*(volatile uint8_t *)(a))
#endif
#define QSPI 0x52005000u
static enum tx15_qspi_result receive(unsigned opcode,uint8_t *dst,uint32_t n,uint32_t budget)
{
    unsigned ready=0;
    for(uint32_t i=0;i<budget;i++) {
        uint32_t sr=TX15_READ32(QSPI+8);
        if(sr&0x11u)return TX15_QSPI_TRANSFER_ERROR;
        if(!(sr&0x20u)){ready=1;break;}
    }
    if(!ready)return TX15_QSPI_TIMEOUT;
    TX15_WRITE32(QSPI+12,0x1b);
    TX15_WRITE32(QSPI+16,n-1);
    TX15_WRITE32(QSPI+20,opcode==0x5a?0x0520255au:(0x05000100u|opcode));
    if(opcode==0x5a)TX15_WRITE32(QSPI+24,0); /* 24-bit address + 8 dummy clocks */
    for(uint32_t i=0;i<n;i++) {
        ready=0;
        for(uint32_t j=0;j<budget;j++) {
            uint32_t sr=TX15_READ32(QSPI+8);
            if(sr&0x11u)return TX15_QSPI_TRANSFER_ERROR;
            if(sr&0x3f00u){ready=1;break;}
        }
        if(!ready)return TX15_QSPI_TIMEOUT;
        dst[i]=TX15_READ8(QSPI+32);
    }
    for(uint32_t i=0;i<budget;i++) {
        uint32_t sr=TX15_READ32(QSPI+8);
        if(sr&0x11u)return TX15_QSPI_TRANSFER_ERROR;
        if((sr&0x22u)==2u){TX15_WRITE32(QSPI+12,0x1b);return TX15_QSPI_OK;}
    }
    return TX15_QSPI_TIMEOUT;
}
enum tx15_qspi_result tx15_flash_info_read(uint32_t jedec,struct tx15_flash_info *info,uint32_t budget)
{
    if(!info || !budget)return TX15_QSPI_BAD_STATE;
    if(jedec!=0xc84018u)return TX15_QSPI_BAD_ID;
    if(!(TX15_READ32(0x580244d4u)&0x4000u) || TX15_READ32(QSPI)!=0x0f000001u
        || TX15_READ32(QSPI+4)!=0x00170300u)return TX15_QSPI_BAD_STATE;
    static const uint8_t opcodes[]={0x05,0x35,0x15};
    info->reserved=0;
    for(unsigned i=0;i<3;i++) {
        enum tx15_qspi_result r=receive(opcodes[i],&info->status[i],1,budget);
        if(r!=TX15_QSPI_OK)return r;
    }
    return receive(0x5a,info->sfdp,TX15_SFDP_CAPTURE_BYTES,budget);
}

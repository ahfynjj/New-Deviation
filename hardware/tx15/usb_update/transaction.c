/* Restricted external application transaction; GPL-3.0-or-later. */
#include "transaction.h"
#include <string.h>
int tx15_update_flash_writable(const struct tx15_update_flash_info *i)
{
    return i && i->jedec==0xc84018u && i->capacity==0x1000000u && i->page_bytes==256
        && i->erase_bytes==4096 && i->sfdp_valid==1 && !i->sr1
        && !(i->sr2&~2u) && !(i->sr3&~0x60u);
}
static void service(struct tx15_update_tx *tx)
{ if (tx->io.service) tx->io.service(tx->io.ctx); }
static int failed(struct tx15_update_tx *tx)
{ tx->active=0;tx->status.state=TX15_ERROR;tx->status.error=TX15_IO_ERROR;tx->status.verification_flags=0;return -1; }
int tx15_update_tx_prepare(struct tx15_update_tx *tx,const struct tx15_update_io *io,
                           const struct tx15_update_package *p,uint8_t *shadow,size_t capacity)
{
    if (!tx) return 0;
    memset(tx,0,sizeof(*tx));tx->status.state=TX15_ERROR;tx->status.error=TX15_BAD_PACKAGE;
    struct tx15_boot_image boot;
    if (!io || !io->observe || !io->read || !io->erase4k || !io->program || !p || !p->image
        || !p->image_bytes || p->image_bytes>TX15_UPDATE_IMAGE_MAX || !shadow || capacity<0x100000
        || !tx15_boot_image_validate(p->image,p->image_bytes,&boot)
        || tx15_update_crc(0,p->image,p->image_bytes)!=p->image_crc) return 0;
    uintptr_t image=(uintptr_t)p->image,mirror=(uintptr_t)shadow;
    if (image>UINTPTR_MAX-p->image_bytes || mirror>UINTPTR_MAX-0x100000u
        || (image<mirror+0x100000u && mirror<image+p->image_bytes)) return 0;
    tx->io=*io;tx->package=*p;tx->package.boot=boot;tx->shadow=shadow;
    tx->erase_bytes=(p->image_bytes+4095u)&~4095u;
    if (tx->erase_bytes>0xf0000u) return 0;
    struct tx15_update_flash_info info;
    if (!io->observe(io->ctx,&info) || !tx15_update_flash_writable(&info)) return 0;
    /* Not active yet, but runtime must already freeze COMMIT/READY before this
     * service callback. Preparation is an immutable read phase. */
    for (uint32_t at=0;at<0x100000u;at+=1024) {
        if (!io->read(io->ctx,at,shadow+at,1024)) { failed(tx);return 0; }
        service(tx);
    }
    /* Re-observe just before first mutation; no protection changes are made. */
    if (!io->observe(io->ctx,&info) || !tx15_update_flash_writable(&info)) return 0;
    tx->active=1;tx->status=(struct tx15_update_reply){TX15_ERASING,0,0,p->image_bytes,p->image_crc,0};
    return 1;
}
int tx15_update_tx_step(struct tx15_update_tx *tx)
{
    if (!tx || tx->stepping) return -1;
    if (tx->status.state==TX15_DONE) return 1;
    if (!tx->active) return -1;
    tx->stepping=1;int result=0;
    if (tx->status.state==TX15_ERASING) {
        if (!tx->io.erase4k(tx->io.ctx,tx->offset)) result=failed(tx);
        else {
            tx->offset+=4096;
            if (tx->offset==tx->erase_bytes) {tx->offset=64;tx->status.state=TX15_PROGRAMMING;}
        }
    } else if (tx->status.state==TX15_PROGRAMMING) {
        uint8_t page[256];uint32_t at=tx->offset,n;
        if (at==tx->erase_bytes) {
            /* ND15 header is the last programming operation. */
            at=0;n=64;memcpy(page,tx->package.image,n);tx->header_pending=1;
        } else {
            n=256u-at%256u;
            for (uint32_t i=0;i<n;i++) page[i]=at+i<tx->package.image_bytes?
                tx->package.image[at+i]:tx->shadow[at+i];
        }
        if (!tx->io.program(tx->io.ctx,at,page,n)) result=failed(tx);
        else if (tx->header_pending) {tx->offset=0;tx->status.state=TX15_VERIFYING;}
        else tx->offset+=n;
    } else if (tx->status.state==TX15_VERIFYING) {
        uint8_t block[1024];uint32_t at=tx->offset;
        if (!tx->io.read(tx->io.ctx,at,block,sizeof(block))) result=failed(tx);
        else {
            for (unsigned i=0;i<sizeof(block);i++) {
                uint32_t index=at+i;
                uint8_t expected=index<tx->package.image_bytes?tx->package.image[index]:tx->shadow[index];
                if (block[i]!=expected) {result=failed(tx);break;}
            }
            if (!result) {
                memcpy(tx->shadow+at,block,sizeof(block));tx->offset+=sizeof(block);
                tx->status.received=tx->offset<tx->package.image_bytes?tx->offset:tx->package.image_bytes;
                if (tx->offset==0x100000u) {
                    struct tx15_boot_image checked;
                    if (!tx15_boot_image_validate(tx->shadow,tx->package.image_bytes,&checked)
                        || tx15_update_crc(0,tx->shadow,tx->package.image_bytes)!=tx->package.image_crc) result=failed(tx);
                    else {tx->status.state=TX15_DONE;tx->status.verification_flags=1;tx->active=0;result=1;}
                }
            }
        }
    } else result=failed(tx);
    service(tx);tx->stepping=0;return result;
}

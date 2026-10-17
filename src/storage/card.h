/* Cooperative read-only SD metadata probe. GPL-3.0-or-later. */
#ifndef ND_STORAGE_CARD_H
#define ND_STORAGE_CARD_H
#include "volume.h"
enum {ND_CARD_OFF,ND_CARD_BUSY,ND_CARD_READY,ND_CARD_ERROR};
enum {ND_CARD_HW=1,ND_CARD_TIMEOUT,ND_CARD_PROTOCOL,ND_CARD_CAPACITY,ND_CARD_PARTITION,ND_CARD_VOLUME,ND_CARD_IO};
enum {ND_SD_NONE,ND_SD_SHORT,ND_SD_OCR,ND_SD_LONG};
enum {ND_SD_TIMEOUT=-1,ND_SD_CRC=-2};
struct nd_sd_ops {
    int (*init)(void *);void (*stop)(void *);
    int (*command)(void *,unsigned cmd,uint32_t argument,unsigned response_kind);
    int (*response)(void *,uint32_t response[4]); /* 0 pending,1 done,<0 failure */
    int (*read_start)(void *,uint32_t lba,int block_addressed);
    int (*read_poll)(void *,uint8_t sector[512]);
};
struct nd_card_report {
    unsigned state,error,last_command,steps,high_capacity,partition_kind;
    uint32_t last_response,rca,ocr,cid[4],csd[4];uint64_t blocks;
    struct nd_volume volume;
    uint32_t elapsed,max_gap;
};
struct nd_card {
    struct nd_card_report report;
    const struct nd_sd_ops *ops;void *ctx;
    unsigned active,phase,pending,v2;
    uint32_t next,deadline,total_deadline,lba;uint64_t span;
    uint32_t started,last_poll;
    uint8_t sector[512];
};
/* Zero-initialize object before first use. Only init/read commands are issued.
 * Successful metadata completion releases transport, retaining the report. */
int nd_card_begin(struct nd_card *,const struct nd_sd_ops *,void *,uint32_t now);
void nd_card_poll(struct nd_card *,uint32_t now);
void nd_card_stop(struct nd_card *);
int nd_card_capacity(const uint32_t csd[4],uint64_t *blocks);
#endif

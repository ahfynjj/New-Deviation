/* Bounded local-module selection writes and readback; GPL-3.0-or-later. */
#ifndef CRSF_TOOLS_H
#define CRSF_TOOLS_H
#include "crsf_link.h"
enum { CRSF_TOOL_PING=1,CRSF_TOOL_READ,CRSF_TOOL_STATS,CRSF_TOOL_WRITE };
enum { CRSF_WRITE_IDLE,CRSF_WRITE_WAIT,CRSF_WRITE_VERIFIED,CRSF_WRITE_MISMATCH,
       CRSF_WRITE_TIMEOUT,CRSF_WRITE_CANCELLED };
struct crsf_tool_field { uint8_t ready,min,max,value,nonempty[32];uint32_t schema; };
struct crsf_tool_report {
    uint32_t state,writes,verified,failed,denied,stats,reads,id,previous,expected,actual,started;
};
struct crsf_tools {
    struct crsf_tool_field fields[65];
    struct crsf_tool_report report;
    uint8_t bytes[512];
    unsigned enabled,used,assembly_id,next_chunk,request_id,request_chunk,request_active;
    unsigned verify_read,remaining;
    uint32_t pending_schema;
};
void crsf_tools_init(struct crsf_tools *,int enable_writes);
/* Pure classification; never records a write until hardware accepts it. */
int crsf_tools_kind(const struct crsf_tools *,uint8_t,const uint8_t *,unsigned);
/* A legitimate reread may wait for settling. Retain it, do not drop it. */
int crsf_tools_defer(const struct crsf_tools *,uint8_t,const uint8_t *,unsigned,uint32_t now);
void crsf_tools_sent(struct crsf_tools *,uint8_t,const uint8_t *,unsigned,uint32_t now);
void crsf_tools_receive(struct crsf_tools *,const struct crsf_message *,uint32_t now);
void crsf_tools_tick(struct crsf_tools *,uint32_t now);
void crsf_tools_cancel(struct crsf_tools *);
#endif

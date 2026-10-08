/* Bounded local-module selections and command sessions; GPL-3.0-or-later. */
#ifndef CRSF_TOOLS_H
#define CRSF_TOOLS_H
#include "crsf_link.h"
enum { CRSF_TOOL_PING=1,CRSF_TOOL_READ,CRSF_TOOL_STATS,CRSF_TOOL_WRITE,CRSF_TOOL_COMMAND };
enum { CRSF_WRITE_IDLE,CRSF_WRITE_WAIT,CRSF_WRITE_VERIFIED,CRSF_WRITE_MISMATCH,
       CRSF_WRITE_TIMEOUT,CRSF_WRITE_CANCELLED,CRSF_COMMAND_COMPLETE };
struct crsf_tool_field { uint8_t ready,min,max,value,nonempty[32],type;uint32_t schema; };
struct crsf_tool_report {
    uint32_t state,writes,verified,failed,denied,stats,reads,id,previous,expected,actual,started;
    /* command=1 identifies the current/last command. Completion only means
     * the module reported READY, never proof of binding or WiFi connectivity. */
    uint32_t command,commands,confirmed,polled,cancelled,completed;
};
struct crsf_tools {
    struct crsf_tool_field fields[65];
    struct crsf_tool_report report;
    uint8_t bytes[512];
    unsigned enabled,used,assembly_id,next_chunk,request_id,request_chunk,request_active;
    unsigned verify_read,remaining;
    uint32_t pending_schema;
    unsigned command_active,command_reply,cancel_sent;
    uint32_t command_feedback;
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
/* Terminal command failure, suitable for a visible tool error. */
const char *crsf_tools_error(const struct crsf_tools *);
/* Popup scripts POLL instead of requesting continuation chunks. Host sends
 * this bounded READ through the same RC-aware UART path; retry only if busy. */
int crsf_tools_command_chunk(const struct crsf_tools *,uint8_t payload[4]);
#endif

/* GPL-3.0-or-later */
#ifndef CRSF_STREAM_H
#define CRSF_STREAM_H
#include "crsf_link.h"
struct crsf_stream { uint8_t bytes[64]; unsigned size; uint32_t last_ms; };
struct crsf_device { char name[32]; uint32_t serial,hardware,software,fields; };
/* Discovery parser: 10ms inter-call gap discards partial data. Adapter drains
 * queued RX bytes before rendering and resets parser after UART overflow. */
int crsf_stream_feed(struct crsf_stream *, uint8_t byte, uint32_t ms, struct crsf_frame *);
int crsf_device_info(const struct crsf_frame *, struct crsf_device *);
#endif

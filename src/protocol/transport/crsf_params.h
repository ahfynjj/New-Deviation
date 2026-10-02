/* Bounded read-only parameter capture for bench validation. GPL-3.0-or-later. */
#ifndef CRSF_PARAMS_H
#define CRSF_PARAMS_H
#include "crsf_link.h"
#define CRSF_PARAM_COUNT 64
#define CRSF_PARAM_BYTES 512
struct crsf_params {
    uint32_t count,current,chunk,remaining;
    uint16_t lengths[CRSF_PARAM_COUNT];
    uint8_t data[CRSF_PARAM_COUNT][CRSF_PARAM_BYTES];
};
int crsf_params_init(struct crsf_params *, unsigned count);
int crsf_params_request(const struct crsf_params *, uint8_t payload[4]);
/* -1 invalid/overflow, 0 unrelated, 1 more chunks, 2 field done, 3 all done.
 * Does not interpret values or issue writes; raw payload is reusable evidence. */
int crsf_params_accept(struct crsf_params *, const struct crsf_message *);
void crsf_params_restart(struct crsf_params *);
#endif

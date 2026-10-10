/* Native update dispatcher; GPL-3.0-or-later. */
#ifndef TX15_UPDATE_RUNTIME_H
#define TX15_UPDATE_RUNTIME_H
#include "transaction.h"
struct tx15_update_runtime {
    struct tx15_update_receiver receiver;
    struct tx15_update_tx tx;
    struct tx15_update_io io;
    uint8_t uid[12],*shadow;
    size_t shadow_capacity;
    unsigned read_only,synchronized,committed;
};
void tx15_update_runtime_init(struct tx15_update_runtime*,const struct tx15_update_io*,
                              uint8_t*,size_t,uint8_t*,size_t,const uint8_t[12],uint64_t,unsigned);
void tx15_update_runtime_session(struct tx15_update_runtime*,uint64_t);
void tx15_update_runtime_request(struct tx15_update_runtime*,const struct tx15_frame*,struct tx15_frame*);
int tx15_update_runtime_step(struct tx15_update_runtime*);
#endif

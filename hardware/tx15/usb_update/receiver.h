/* New Deviation RAM-only update receiver; GPL-3.0-or-later. */
#ifndef TX15_UPDATE_RECEIVER_H
#define TX15_UPDATE_RECEIVER_H
#include "protocol.h"
enum tx15_update_state { TX15_IDLE, TX15_RECEIVING, TX15_VALIDATING, TX15_READY,
    TX15_ERASING, TX15_PROGRAMMING, TX15_VERIFYING, TX15_DONE, TX15_ERROR };
enum tx15_update_error { TX15_OK, TX15_BAD_REQUEST, TX15_BAD_SESSION, TX15_BAD_STATE,
    TX15_BAD_SEQUENCE, TX15_BAD_OFFSET, TX15_BAD_PACKAGE, TX15_TIMEOUT,
    TX15_READ_ONLY, TX15_BAD_IDENTITY, TX15_IO_ERROR };
struct tx15_update_reply { uint32_t state,error,received,total,image_crc,verification_flags; };
struct tx15_update_receiver {
    uint8_t *staging; size_t capacity; uint64_t session;
    uint32_t boot_api,settings_abi,now,start,last_activity,next_sequence;
    uint32_t last_sequence,last_offset,last_bytes,final_sequence;
    struct tx15_update_reply status;
    struct tx15_update_package package;
};
void tx15_update_receiver_init(struct tx15_update_receiver*,uint8_t*,size_t,uint64_t,uint32_t,uint32_t);
void tx15_update_receiver_tick(struct tx15_update_receiver*,uint32_t now);
int tx15_update_receiver_request(struct tx15_update_receiver*,const struct tx15_frame*,struct tx15_update_reply*);
#endif

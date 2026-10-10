/* New Deviation native USB update framing; GPL-3.0-or-later. */
#ifndef TX15_UPDATE_PROTOCOL_H
#define TX15_UPDATE_PROTOCOL_H
#include "package.h"
#define TX15_FRAME_PAYLOAD_MAX 1024u
#define TX15_FRAME_BYTES_MAX (32u+TX15_FRAME_PAYLOAD_MAX)
enum tx15_update_opcode { TX15_HELLO=1, TX15_BEGIN, TX15_DATA, TX15_FINALIZE,
    TX15_STATUS, TX15_READ_SETTINGS, TX15_COMMIT, TX15_ABORT };
struct tx15_frame {
    uint64_t session;
    uint32_t sequence, offset, bytes;
    uint8_t kind;
    uint8_t payload[TX15_FRAME_PAYLOAD_MAX];
};
struct tx15_frame_parser { uint8_t buffer[TX15_FRAME_BYTES_MAX]; size_t used; };
typedef void (*tx15_frame_callback)(void *, const struct tx15_frame *);
void tx15_update_frame_init(struct tx15_frame_parser *parser);
int tx15_update_frame_feed(struct tx15_frame_parser*,const uint8_t*,size_t,tx15_frame_callback,void*);
size_t tx15_update_frame_encode(const struct tx15_frame*,uint8_t*,size_t);
uint32_t tx15_update_word(const uint8_t*);
void tx15_update_put_word(uint8_t*,uint32_t);
#endif

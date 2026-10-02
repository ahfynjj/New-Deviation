/* Native CRSF transport core; GPL-3.0-or-later. No hardware or Lua dependency. */
#ifndef DEVIATION_CRSF_LINK_H
#define DEVIATION_CRSF_LINK_H

#include <stdint.h>

#define CRSF_LINK_FRAME_MAX 64
#define CRSF_LINK_PAYLOAD_MAX 60
#define CRSF_LINK_TX_DEPTH 4
#define CRSF_LINK_RX_DEPTH 8
enum crsf_slot { CRSF_SLOT_OFF = -1, CRSF_SLOT_INTERNAL = 0, CRSF_SLOT_EXTERNAL = 1 };

struct crsf_frame {
    uint8_t bytes[CRSF_LINK_FRAME_MAX];
    unsigned size;
};
struct crsf_message {
    uint8_t type, payload[CRSF_LINK_PAYLOAD_MAX];
    unsigned size;
};
struct crsf_link {
    int slot;
    uint32_t generation;
    struct crsf_frame rc, tx[CRSF_LINK_TX_DEPTH];
    struct crsf_message rx[CRSF_LINK_RX_DEPTH];
    unsigned rc_pending, tx_head, tx_count, rx_head, rx_count;
};

/* All link operations are serialized by one task, never called from IRQ.
 * Callback must copy/accept the ENTIRE frame synchronously, returning 1;
 * busy/error returns 0 without accepting bytes. It must not reenter the link.
 * Hardware owns UART timing, half-duplex turnaround and scheduling deadlines.
 */
typedef int (*crsf_link_send)(void *context, int slot, uint32_t generation,
                              const uint8_t *frame, unsigned size);

uint8_t crsf_link_crc(const uint8_t *bytes, unsigned size);
int crsf_frame_build(struct crsf_frame *frame, uint8_t address, uint8_t type,
                     const uint8_t *payload, unsigned size);
int crsf_frame_valid(const struct crsf_frame *frame);
void crsf_link_init(struct crsf_link *link);
/* Stop/drain hardware FIRST. Each valid select resets all queues (even same
 * slot); return nonzero session generation, or 0 for invalid selection.
 * Stale hardware completions must retain the generation they started with.
 */
uint32_t crsf_link_select(struct crsf_link *link, int slot);
int crsf_link_set_channels(struct crsf_link *link, const int32_t *channels, unsigned count);
int crsf_link_can_push(const struct crsf_link *link);
int crsf_link_push(struct crsf_link *link, uint8_t type, const uint8_t *payload, unsigned size);
/* At most one frame per call. Latest pending RC precedes parameter traffic.
 * This prioritization is not itself a real-time scheduler or rate guarantee. */
int crsf_link_service(struct crsf_link *link, crsf_link_send send, void *context);
/* Adapter supplies a complete frame. Byte parsing/timeouts and non-Lua
 * telemetry dispatch belong to the adapter. False means rejected or full. */
int crsf_link_receive(struct crsf_link *link, int slot, uint32_t generation,
                      const struct crsf_frame *frame);
int crsf_link_pop(struct crsf_link *link, struct crsf_message *message);

#endif

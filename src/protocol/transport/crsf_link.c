/* Native CRSF transport core; GPL-3.0-or-later. */
#include "crsf_link.h"
#include <string.h>

uint8_t crsf_link_crc(const uint8_t *bytes, unsigned size)
{
    uint8_t crc = 0;
    while (size--) {
        crc ^= *bytes++;
        for (unsigned bit = 0; bit < 8; bit++)
            crc = (uint8_t)((crc << 1) ^ ((crc & 0x80) ? 0xd5 : 0));
    }
    return crc;
}

int crsf_frame_build(struct crsf_frame *frame, uint8_t address, uint8_t type,
                     const uint8_t *payload, unsigned size)
{
    if (!frame || size > CRSF_LINK_PAYLOAD_MAX || (size && !payload)) return 0;
    frame->bytes[0] = address;
    frame->bytes[1] = (uint8_t)(size + 2);
    frame->bytes[2] = type;
    if (size) memcpy(frame->bytes + 3, payload, size);
    frame->bytes[size + 3] = crsf_link_crc(frame->bytes + 2, size + 1);
    frame->size = size + 4;
    return 1;
}

int crsf_frame_valid(const struct crsf_frame *frame)
{
    if (!frame || frame->size < 4 || frame->size > CRSF_LINK_FRAME_MAX) return 0;
    if (frame->bytes[1] != frame->size - 2) return 0;
    return crsf_link_crc(frame->bytes + 2, frame->size - 3) == frame->bytes[frame->size - 1];
}

void crsf_link_init(struct crsf_link *link)
{
    memset(link, 0, sizeof(*link));
    link->slot = CRSF_SLOT_OFF;
}

uint32_t crsf_link_select(struct crsf_link *link, int slot)
{
    if (slot < CRSF_SLOT_OFF || slot > CRSF_SLOT_EXTERNAL) return 0;
    link->slot = slot;
    /* Zero is reserved as an invalid token. Caller drains hardware on every
     * transition, so token wrap cannot retain an old physical operation. */
    if (++link->generation == 0) ++link->generation;
    link->rc_pending = link->tx_head = link->tx_count = 0;
    link->rx_head = link->rx_count = 0;
    return link->generation;
}

int crsf_link_set_channels(struct crsf_link *link, const int32_t *channels, unsigned count)
{
    if (link->slot == CRSF_SLOT_OFF || !channels || count == 0 || count > 16) return 0;
    uint8_t payload[22] = {0};
    uint32_t accumulator = 0;
    unsigned bits = 0, pos = 0;
    for (unsigned i = 0; i < 16; i++) {
        int32_t value = i < count ? channels[i] : 0;
        /* Preserve Deviation +/-100%=800 ticks, safely clamp extended travel.
         * Bound before multiplication to avoid overflow even for corrupt input. */
        if (value < -12400) value = -12400;
        if (value > 12400) value = 12400;
        unsigned ticks = (unsigned)(992 + value * 800 / 10000);
        accumulator |= ticks << bits;
        bits += 11;
        while (bits >= 8) {
            payload[pos++] = (uint8_t)accumulator;
            accumulator >>= 8;
            bits -= 8;
        }
    }
    crsf_frame_build(&link->rc, 0xee, 0x16, payload, sizeof(payload));
    link->rc_pending = 1;
    return 1;
}

int crsf_link_can_push(const struct crsf_link *link)
{
    return link->slot != CRSF_SLOT_OFF && link->tx_count < CRSF_LINK_TX_DEPTH;
}

int crsf_link_push(struct crsf_link *link, uint8_t type, const uint8_t *payload, unsigned size)
{
    /* Extended frames include destination and origin in the payload; preserve
     * them verbatim. RC frames cannot be injected from the script queue. */
    if (!crsf_link_can_push(link) || type < 0x28 || size < 2) return 0;
    unsigned tail = (link->tx_head + link->tx_count) % CRSF_LINK_TX_DEPTH;
    if (!crsf_frame_build(&link->tx[tail], 0xee, type, payload, size)) return 0;
    link->tx_count++;
    return 1;
}

int crsf_link_service(struct crsf_link *link, crsf_link_send send, void *context)
{
    if (link->slot == CRSF_SLOT_OFF || !send) return 0;
    const struct crsf_frame *frame;
    if (link->rc_pending) frame = &link->rc;
    else if (link->tx_count) frame = &link->tx[link->tx_head];
    else return 0;
    if (!send(context, link->slot, link->generation, frame->bytes, frame->size)) return 0;
    if (link->rc_pending) link->rc_pending = 0;
    else {
        link->tx_head = (link->tx_head + 1) % CRSF_LINK_TX_DEPTH;
        link->tx_count--;
    }
    return 1;
}

int crsf_link_receive(struct crsf_link *link, int slot, uint32_t generation,
                      const struct crsf_frame *frame)
{
    if (link->slot == CRSF_SLOT_OFF || slot != link->slot || generation != link->generation)
        return 0;
    if (!crsf_frame_valid(frame) || frame->size < 6 || frame->bytes[2] < 0x28) return 0;
    /* Uplink replies addressed to the handset or broadcast, not other nodes. */
    if (frame->bytes[3] != 0xea && frame->bytes[3] != 0) return 0;
    if (link->rx_count == CRSF_LINK_RX_DEPTH) return 0;
    unsigned tail = (link->rx_head + link->rx_count) % CRSF_LINK_RX_DEPTH;
    struct crsf_message *message = &link->rx[tail];
    message->type = frame->bytes[2];
    message->size = frame->size - 4;
    memcpy(message->payload, frame->bytes + 3, message->size);
    link->rx_count++;
    return 1;
}

int crsf_link_pop(struct crsf_link *link, struct crsf_message *message)
{
    if (!message || !link->rx_count) return 0;
    *message = link->rx[link->rx_head];
    link->rx_head = (link->rx_head + 1) % CRSF_LINK_RX_DEPTH;
    link->rx_count--;
    return 1;
}

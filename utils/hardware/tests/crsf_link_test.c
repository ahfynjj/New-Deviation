#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include "crsf_link.h"

static struct crsf_frame sent;
static int busy, calls, sent_slot;
static uint32_t sent_generation;
static int send_frame(void *ctx, int slot, uint32_t generation,
                      const uint8_t *bytes, unsigned size)
{
    assert(ctx == &busy);
    calls++;
    if (busy) return 0;
    sent_slot = slot; sent_generation = generation;
    memcpy(sent.bytes, bytes, size); sent.size = size;
    return 1;
}

/* Decode each bit independently of the implementation's packing algorithm. */
static unsigned channel(unsigned ch)
{
    unsigned value = 0;
    for (unsigned bit = 0; bit < 11; bit++) {
        unsigned at = ch * 11 + bit;
        value |= ((sent.bytes[3 + at / 8] >> (at % 8)) & 1u) << bit;
    }
    return value;
}

int main(void)
{
    struct crsf_link link;
    struct crsf_frame frame;
    struct crsf_message msg;
    int32_t channels[16] = {-10000, 0, 10000, INT_MIN, INT_MAX};
    const uint8_t ping[] = {0, 0xea};
    const uint8_t reply[] = {0xea, 0xee, 1, 2, 3};
    /* CRC-8/DVB-S2 published check value, polynomial D5, init zero. */
    assert(crsf_link_crc((const uint8_t *)"123456789", 9) == 0xbc);
    assert(crsf_frame_build(&frame, 0xee, 0x28, ping, 2));
    assert(frame.size == 6 && frame.bytes[1] == 4 && frame.bytes[2] == 0x28);
    assert(frame.bytes[3] == 0 && frame.bytes[4] == 0xea);
    assert(crsf_frame_valid(&frame));
    frame.bytes[3] ^= 1; assert(!crsf_frame_valid(&frame));
    uint8_t payload[61] = {0};
    assert(crsf_frame_build(&frame, 0xc8, 0x2b, payload, 60));
    assert(frame.size == 64 && crsf_frame_valid(&frame));
    assert(!crsf_frame_build(&frame, 0xc8, 0x2b, payload, 61));
    assert(!crsf_frame_build(&frame, 0xc8, 0x2b, NULL, 1));
    assert(!crsf_frame_build(&frame, 0xc8, 0x2b, payload, UINT_MAX));
    for (unsigned i = 1; i < frame.size; i++) {
        frame.bytes[i] ^= 1;
        assert(!crsf_frame_valid(&frame));
        frame.bytes[i] ^= 1;
    }
    frame.size = 65; assert(!crsf_frame_valid(&frame));
    frame.size = 2; assert(!crsf_frame_valid(&frame));

    crsf_link_init(&link);
    assert(link.slot == CRSF_SLOT_OFF);
    assert(!crsf_link_push(&link, 0x28, ping, 2));
    assert(!crsf_link_set_channels(&link, channels, 16));
    assert(!crsf_link_service(&link, send_frame, &busy));
    assert(crsf_link_select(&link, 2) == 0); /* invalid slot leaves state */
    uint32_t first = crsf_link_select(&link, CRSF_SLOT_INTERNAL);
    assert(first && link.slot == 0);
    assert(!crsf_link_push(&link, 0x16, ping, 2)); /* script cannot inject RC */
    assert(!crsf_link_push(&link, 0x28, ping, 1)); /* extended addresses required */
    assert(!crsf_link_push(&link, 0x28, ping, 61));
    assert(!crsf_link_set_channels(&link, channels, 0));
    assert(!crsf_link_set_channels(&link, channels, 17));
    assert(!crsf_link_set_channels(&link, NULL, 16));
    for (unsigned i = 0; i < CRSF_LINK_TX_DEPTH; i++) {
        uint8_t request[] = {0xee, 0xea, (uint8_t)i, 0};
        assert(crsf_link_push(&link, 0x2c, request, sizeof(request)));
    }
    assert(!crsf_link_can_push(&link));
    assert(!crsf_link_push(&link, 0x28, ping, 2));
    assert(crsf_link_set_channels(&link, channels, 16));
    channels[5] = 5000; /* newest channels replace stale pending RC */
    assert(crsf_link_set_channels(&link, channels, 16));
    busy = 1;
    assert(!crsf_link_service(&link, send_frame, &busy));
    busy = 0;
    assert(crsf_link_service(&link, send_frame, &busy));
    assert(sent_slot == 0 && sent_generation == first);
    assert(sent.size == 26 && sent.bytes[0] == 0xee && sent.bytes[2] == 0x16);
    assert(channel(0) == 192 && channel(1) == 992 && channel(2) == 1792);
    assert(channel(3) == 0 && channel(4) == 1984 && channel(5) == 1392);
    for (unsigned i = 6; i < 16; i++) assert(channel(i) == 992);
    assert(crsf_frame_valid(&sent));
    for (unsigned i = 0; i < CRSF_LINK_TX_DEPTH; i++) {
        assert(crsf_link_service(&link, send_frame, &busy));
        assert(sent.bytes[2] == 0x2c && sent.bytes[5] == i);
    }
    assert(!crsf_link_service(&link, send_frame, &busy));
    assert(crsf_link_can_push(&link));
    /* FIFO wraps repeatedly without silently overwriting requests. */
    for (unsigned i = 0; i < 20; i++) {
        assert(crsf_link_push(&link, 0x28, ping, 2));
        assert(crsf_link_service(&link, send_frame, &busy));
    }
    assert(crsf_link_set_channels(&link, channels, 4));
    assert(crsf_link_service(&link, send_frame, &busy));
    assert(channel(4) == 992 && channel(15) == 992);
    for (unsigned round = 0; round < 32; round++) {
        for (unsigned i = 0; i < 16; i++)
            channels[i] = (int32_t)((round * 977 + i * 1237) % 20001) - 10000;
        assert(crsf_link_set_channels(&link, channels, 16));
        assert(crsf_link_service(&link, send_frame, &busy));
        for (unsigned i = 0; i < 16; i++)
            assert(channel(i) == (unsigned)(992 + channels[i] * 800 / 10000));
    }

    assert(crsf_frame_build(&frame, 0xea, 0x14, reply, sizeof(reply)));
    assert(!crsf_link_receive(&link, 0, first, &frame)); /* adapter handles link stats */
    uint8_t wrong_destination[] = {0xec, 0xee, 1};
    assert(crsf_frame_build(&frame, 0xea, 0x2b, wrong_destination, sizeof(wrong_destination)));
    assert(!crsf_link_receive(&link, 0, first, &frame));
    assert(crsf_frame_build(&frame, 0xea, 0x2b, reply, 1));
    assert(!crsf_link_receive(&link, 0, first, &frame)); /* truncated extended header */
    assert(crsf_frame_build(&frame, 0xea, 0x2b, reply, sizeof(reply)));
    assert(!crsf_link_receive(&link, 1, first, &frame));
    assert(!crsf_link_receive(&link, 0, first + 1, &frame));
    for (unsigned i = 0; i < CRSF_LINK_RX_DEPTH; i++)
        assert(crsf_link_receive(&link, 0, first, &frame));
    assert(!crsf_link_receive(&link, 0, first, &frame));
    for (unsigned i = 0; i < CRSF_LINK_RX_DEPTH; i++) {
        assert(crsf_link_pop(&link, &msg));
        assert(msg.type == 0x2b && msg.size == sizeof(reply));
        assert(!memcmp(msg.payload, reply, sizeof(reply)));
    }
    assert(!crsf_link_pop(&link, &msg));
    for (unsigned i = 0; i < 20; i++) {
        uint8_t item[] = {0xea, 0xee, (uint8_t)i};
        assert(crsf_frame_build(&frame, 0xea, 0x2b, item, sizeof(item)));
        assert(crsf_link_receive(&link, 0, first, &frame));
        assert(crsf_link_pop(&link, &msg) && msg.payload[2] == i);
    }
    frame.bytes[3] ^= 1;
    assert(!crsf_link_receive(&link, 0, first, &frame));
    frame.bytes[3] ^= 1;
    assert(crsf_link_receive(&link, 0, first, &frame));
    assert(crsf_link_push(&link, 0x28, ping, 2));
    assert(crsf_link_set_channels(&link, channels, 6));
    uint32_t second = crsf_link_select(&link, CRSF_SLOT_EXTERNAL);
    assert(second != first && second);
    assert(!crsf_link_pop(&link, &msg));
    assert(!crsf_link_service(&link, send_frame, &busy));
    assert(!crsf_link_receive(&link, 0, first, &frame));
    assert(crsf_link_push(&link, 0x28, ping, 2));
    busy = 1; assert(!crsf_link_service(&link, send_frame, &busy));
    busy = 0; assert(crsf_link_service(&link, send_frame, &busy));
    assert(sent_slot == 1 && sent_generation == second);
    assert(crsf_link_receive(&link, 1, second, &frame));
    assert(crsf_link_select(&link, CRSF_SLOT_EXTERNAL) != second);
    assert(!crsf_link_pop(&link, &msg)); /* reinit same module clears session */
    assert(!crsf_link_receive(&link, 1, second, &frame));
    assert(crsf_link_select(&link, CRSF_SLOT_OFF));
    assert(!crsf_link_receive(&link, -1, link.generation, &frame));
    assert(!crsf_link_can_push(&link));
    link.generation = UINT32_MAX;
    assert(crsf_link_select(&link, CRSF_SLOT_INTERNAL) == 1);
    assert(crsf_link_select(&link, -2) == 0 && link.slot == 0 && link.generation == 1);
    assert(calls > 0);
    printf("Static link memory: %u bytes\n", (unsigned)sizeof(link));
    puts("CRSF codec, two slots, busy/full queues, priority and stale sessions PASS");
    return 0;
}

/* Temporary RAM-source substitution only; never included in a Flash loader. */
#ifndef TX15_CHAIN_SOURCE_H
#define TX15_CHAIN_SOURCE_H
#include <stdint.h>
#include "image.h"
#define TX15_CHAIN_SOURCE 0xd0200000u
#define TX15_CHAIN_READY 0x43485244u
#define TX15_CHAIN_GO 0x4348474fu
struct tx15_chain_control {
    uint32_t ready, bytes, gate, jedec;
    uint8_t original_prefix[64];
};
extern volatile struct tx15_chain_control chain_control;
static inline int tx15_chain_range(uint32_t offset,uint32_t bytes,uint32_t total) {
    return total>=64 && total<=TX15_BOOT_MAX_BYTES && offset<=total && bytes<=total-offset;
}
#endif

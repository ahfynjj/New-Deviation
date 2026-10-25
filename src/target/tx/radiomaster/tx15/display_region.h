/* Bounded label-row composition; GPL-3.0-or-later. */
#ifndef TX15_DISPLAY_REGION_H
#define TX15_DISPLAY_REGION_H
#include <stdint.h>
#define TX15_REGION_SCRATCH 0xd0300000u
#define TX15_REGION_ROWS 32u
struct tx15_region_report {
    uint32_t frames,pixels,max_draw_cycles,max_commit_cycles;
};
extern volatile struct tx15_region_report tx15_region_report;
extern unsigned tx15_region_active;
int tx15_region_begin(unsigned x,unsigned y,unsigned w,unsigned h);
void tx15_region_pixel(unsigned x,unsigned y,uint16_t color);
void tx15_region_end(void);
#endif

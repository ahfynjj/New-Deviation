/* Application-only frame ownership; GPL-3.0-or-later. */
#ifndef TX15_FRAME_SWAP_H
#define TX15_FRAME_SWAP_H
#include <stdint.h>
#define TX15_FRAME_BACK 0xd0100000u
struct tx15_frame_report {
    uint32_t state,frames,dma_errors,cpu_copies,swap_timeouts;
    uint32_t max_wait_cycles,max_copy_cycles,max_service_gap_cycles,ltdc_status;
};
extern volatile struct tx15_frame_report tx15_frame_report;
int tx15_frame_init(void);
int tx15_frame_ready(void);
uint32_t tx15_frame_draw_address(void);
uint32_t tx15_frame_visible_address(void);
void tx15_frame_set_service(void (*service)(void));
void tx15_frame_service(void);
void tx15_frame_pixel(unsigned x,unsigned y,uint16_t color);
void tx15_frame_rect(unsigned x,unsigned y,unsigned w,unsigned h,uint16_t color);
void tx15_frame_damage(void);
void tx15_frame_present(void);
#endif

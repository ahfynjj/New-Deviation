/* Native RGB565 card palette; GPL-3.0-or-later. */
#ifndef TX15_CARD_UI_H
#define TX15_CARD_UI_H
#include "gui/gui.h"
enum {TX15_CARD_BG=0x10c3,TX15_CARD_FILL=0x2146,TX15_CARD_EDGE=0x3209,
      TX15_CARD_FG=0xf7be,TX15_CARD_MUTED=0xadb8,TX15_CARD_ACCENT=0xfce6};
struct LabelDesc tx15_card_font(unsigned large);
void tx15_card_page_theme(int page);
void tx15_card_draw_label(guiLabel_t *label,const char *text);
void tx15_card_draw_plate(guiObject_t *obj,const char *text,const struct LabelDesc *font);
int PAGE_MixCardHit(unsigned x,unsigned y);
void PAGE_MixCardTap(unsigned x,unsigned y);
int PAGE_MixCardActive(void);
int PAGE_MixCardGeneration(void);
#endif

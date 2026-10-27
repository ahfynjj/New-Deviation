/* Native menu-only touch contract; GPL-3.0-or-later. */
#ifndef TX15_MENU_TOUCH_H
#define TX15_MENU_TOUCH_H
#include "ui_layout.h"
/* 0..5 rows, 6 Back, 7 Previous, 8 Next; gaps/header are not targets. */
static inline int tx15_menu_touch_hit(unsigned x,unsigned y){
    if(x>=TX15_UI_WIDTH || y>=TX15_UI_HEIGHT)return -1;
    if(y>=TX15_UI_CONTENT_Y && y<TX15_UI_CONTENT_Y+TX15_UI_LIST_ROWS*TX15_UI_ROW_HEIGHT)
        return (y-TX15_UI_CONTENT_Y)/TX15_UI_ROW_HEIGHT;
    if(y>=TX15_UI_FOOTER_Y && x>=8){
        unsigned slot=(x-8)/160;
        if(slot<3 && (x-8)%160<144)return 6+slot;
    }
    return -1;
}
void tx15_menu_touch_poll(void);
void tx15_menu_touch_suspend(void);
int PAGE_MenuTouchRow(void);
void PAGE_MenuTouchTap(unsigned x,unsigned y);
void PAGE_MenuTouchScroll(int direction);
#endif

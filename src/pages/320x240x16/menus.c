/*
 This project is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Deviation is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Deviation.  If not, see <http://www.gnu.org/licenses/>.
 */


#include "common.h"
#include "pages.h"
#include "gui/gui.h"
#include "config/model.h"
#include "config/tx.h"

#ifdef TX15_MENU_TOUCH
#include "menu_touch.h"
#ifdef TX15_CARD_UI
#include "card_ui.h"
static unsigned tx15_menu_items;
#define HEADER_HEIGHT 52
#define LINE_SPACE 104
#define LINE_HEIGHT 96
#define MENU_CONTENT_HEIGHT 208
enum {NUM_X=0,NUM_WIDTH=0,MENU_X=12,MENU_WIDTH=146};
#else
enum {NUM_X=8,NUM_WIDTH=32,MENU_X=48,MENU_WIDTH=404};
#define HEADER_HEIGHT TX15_UI_HEADER
#define LINE_SPACE TX15_UI_ROW_HEIGHT
#define LINE_HEIGHT TX15_UI_ROW_HEIGHT
#define MENU_CONTENT_HEIGHT (TX15_UI_LIST_ROWS*TX15_UI_ROW_HEIGHT)
#endif
static void tx15_menu_footer_init(void);
static guiLabel_t menu_footer[3];
#else
enum {
    NUM_X             = 0,
    NUM_WIDTH         = 16,
    MENU_X            = 20,
    MENU_WIDTH        = (LCD_WIDTH - MENU_X * 2),
};
#define HEADER_HEIGHT (LCD_HEIGHT==240 ? 37 : 40)
#define LINE_SPACE    29
#define LINE_HEIGHT   20
#endif
#include "../common/_menus.c"

static void menu_press_cb(guiObject_t *obj, s8 press_type, const void *data)
{
    (void)obj;
    if(press_type == -1) {
        long i = (long)data;
        PAGE_PushByID(i, 0);
    }
}
static int row_cb(int absrow, int relrow, int y, void *data)
{
    (void)data;
#ifdef TX15_CARD_UI
    OBJ_SET_DIRTY((guiObject_t *)&menu_footer[2],1);
    unsigned page=0,index=0;
    for(unsigned col=0;col<3;col++){
        unsigned target=absrow*3+col;
        while(1){
            menu_get_next_rowidx(&page);
            if(page>=PAGEID_LAST)return col;
            if(index==target)break;
            index++;page++;
        }
        struct LabelDesc font=tx15_card_font(1);font.style=LABEL_CARD;
        GUI_CreateLabelBox(&gui->name[relrow*3+col],12+col*155,y,146,96,
            &font,menu_name_cb,menu_press_cb,(const void *)(uintptr_t)page);
    }
    return 3;
#else
    int idx = 0;
    unsigned i = 0;
    while(1) {
        menu_get_next_rowidx(&i);
        if (i >= PAGEID_LAST)
            break;
        if (idx == absrow) {
#ifdef TX15_MENU_TOUCH
            struct LabelDesc name_font=MENU_FONT;
            name_font.font=BUTTON_FONT.font;
#else
            struct LabelDesc name_font=MENU_FONT;
#endif
            GUI_CreateLabelBox(&gui->idx[relrow], NUM_X, y,
                NUM_WIDTH, LINE_HEIGHT, &LABEL_FONT, idx_string_cb, NULL, (void *)(absrow+ 1L));
            GUI_CreateLabelBox(&gui->name[relrow], MENU_X, y,
                MENU_WIDTH, LINE_HEIGHT, &name_font, menu_name_cb, menu_press_cb, (const void *)(long)i);
            break;
        }
        idx++;
        i++;
    }
    return 1;
#endif
}
#ifdef TX15_MENU_TOUCH
#ifdef TX15_CARD_UI
static const char *tx15_menu_footer_text(guiObject_t *obj,const void *data){
    (void)obj;
    unsigned which=(uintptr_t)data;
    if(which==0)return "Back";
    if(which==1)return "Previous";
    static char caption[24];
    unsigned pages=(tx15_menu_items+5)/6;
    if(!pages)pages=1;
    unsigned page=(PAGE_MenuTouchRow()+1)/2+1;
    if(page>pages)page=pages;
    snprintf(caption,sizeof(caption),"%s %u/%u",page<pages?"Next":"End",page,pages);
    return caption;
}
#endif
static void tx15_menu_footer_init(void){
#ifndef TX15_CARD_UI
    static const char *const names[]={"Back","Previous","Next"};
#endif
    struct LabelDesc font=BUTTON_FONT;
#ifdef TX15_CARD_UI
    font=tx15_card_font(1);
#endif
    for(unsigned i=0;i<3;i++)
#ifdef TX15_CARD_UI
        GUI_CreateLabelBox(&menu_footer[i],8+i*160,TX15_UI_FOOTER_Y,144,40,
            &font,tx15_menu_footer_text,NULL,(const void *)(uintptr_t)i);
#else
        GUI_CreateLabelBox(&menu_footer[i],8+i*160,TX15_UI_FOOTER_Y,144,40,
            &font,NULL,NULL,names[i]);
#endif
}
int PAGE_MenuTouchRow(void){return GUI_ScrollableCurrentRow(&gui->scrollable);}
void PAGE_MenuTouchScroll(int direction){
    int count=gui->scrollable.item_count;
    int visible=GUI_ScrollableVisibleRows(&gui->scrollable);
    if(visible<=0)return;
#ifdef TX15_CARD_UI
    visible=2;int last=count?((count-1)/2)*2:0;
#else
    int last=count>visible?count-visible:0;
#endif
    int row=PAGE_MenuTouchRow()+(direction>0?visible:-visible);
    if(row<0)row=0;
    if(row>last)row=last;
    if(row==PAGE_MenuTouchRow())return;
    GUI_SetSelected(GUI_ShowScrollableRowOffset(&gui->scrollable,row<<8));
}
void PAGE_MenuTouchTap(unsigned x,unsigned y){
    int hit=tx15_menu_touch_hit(x,y);
    if(hit==6){PAGE_Pop();return;}
    if(hit==7 || hit==8){PAGE_MenuTouchScroll(hit==8?1:-1);return;}
    if(hit<0)return;
#ifdef TX15_CARD_UI
    int row=PAGE_MenuTouchRow()*3+hit,idx=0;
    if(hit>=6 || (unsigned)row>=tx15_menu_items)return;
    GUI_SetSelected((guiObject_t *)&gui->name[hit]);
#else
    if(hit>=GUI_ScrollableVisibleRows(&gui->scrollable))return;
    int row=PAGE_MenuTouchRow()+hit,idx=0;
#endif
    unsigned page=0;
    while(1){
        menu_get_next_rowidx(&page);
        if(page>=PAGEID_LAST)return;
        if(idx++==row){menu_press_cb(NULL,-1,(const void *)(uintptr_t)page);return;}
        page++;
    }
}
#endif

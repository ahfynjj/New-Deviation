/* P1: diagnostic only. Finger input is never dispatched to native GUI/Lua. */
#ifdef TX15_TOUCH_DIAGNOSTIC
#include "common.h"
#include "pages.h"
#include "gui/gui.h"
#include "config/display.h"
#include "ui_layout.h"
#include "../../../hardware/tx15/board/touch.h"
static guiLabel_t rows[4],probe,stop,map;
static guiRect_t preview;
static char lines[4][96];
static unsigned refreshed,shown_x,shown_y,shown_points,shown_state,shown_event;
static const char *const states[]={"Off","Probing","Ready","No GT911","Error"};
static const char *const events[]={"-","DOWN","MOVE","UP","CANCEL"};
static const char *line_text(guiObject_t *obj,const void *data){
    (void)obj;return lines[(uintptr_t)data];
}
static const char *button_text(guiObject_t *obj,const void *data){
    (void)obj;static const char *const names[]={"Probe","Stop","Map +"};return names[(uintptr_t)data];
}
static void update(unsigned redraw){
    const struct tx15_touch_report *r=&tx15_touch_report;char next[4][96];
    snprintf(next[0],sizeof(next[0]),"%s ID:%.4s @%02X %ux%u",r->state<5?states[r->state]:"Error",
        r->product,(unsigned)r->address,(unsigned)r->raw_width,(unsigned)r->raw_height);
    snprintf(next[1],sizeof(next[1]),"Raw:%u,%u  XY:%u,%u N:%u ID:%u",
        r->raw_x,r->raw_y,r->x,r->y,r->points,r->id);
    snprintf(next[2],sizeof(next[2]),"Map:%u (trial) %s Frames:%u Err:%u",r->map_flags,
        r->event<5?events[r->event]:"-",(unsigned)r->frames,(unsigned)r->errors);
    snprintf(next[3],sizeof(next[3]),"Bus:%d ST:%08X Busy:%u",(int)r->last_result,
        (unsigned)r->bus_status,(unsigned)r->busy);
    for(unsigned i=0;i<4;i++)if(strcmp(lines[i],next[i])){
        strcpy(lines[i],next[i]);if(redraw)GUI_Redraw((guiObject_t *)&rows[i]);
    }
    if(shown_x!=r->x || shown_y!=r->y || shown_points!=r->points
        || shown_state!=r->state || shown_event!=r->event){
        shown_x=r->x;shown_y=r->y;shown_points=r->points;shown_state=r->state;shown_event=r->event;
        if(redraw)GUI_Redraw((guiObject_t *)&preview);
    }
}
static void cross(unsigned x,unsigned y,unsigned color){
    LCD_DrawFastHLine(x-4,y,9,color);LCD_DrawFastVLine(x,y-4,9,color);
}
static void draw_preview(guiObject_t *obj,const void *data){
    (void)obj;(void)data; /* Miniature screen map, not a parameter hit surface. */
    LCD_DrawRect(16,148,448,124,0x7bef);
    cross(22,154,0x7bef);cross(457,154,0x7bef);
    cross(22,265,0x7bef);cross(457,265,0x7bef);cross(240,210,0x7bef);
    if(shown_state==TX15_TOUCH_READY && shown_points==1 && shown_x<480 && shown_y<320)
        cross(22+shown_x*435u/479u,154+shown_y*111u/319u,
            shown_event==TX15_TOUCH_CANCEL?0xf800:0xfd20);
}
static void action(guiObject_t *obj,s8 press,const void *data){
    (void)obj;if(press!=-1)return;
    unsigned id=(uintptr_t)data,now=CLOCK_getms();
    if(!id)tx15_touch_start(now);
    else if(id==1)tx15_touch_stop(now);
    else tx15_touch_cycle_map(now);
    update(1);
}
void PAGE_TouchTestInit(int page){
    (void)page;PAGE_SetModal(0);PAGE_ShowHeader("Touch test TOU1");
    tx15_touch_start(CLOCK_getms());memset(lines,0,sizeof(lines));update(0);
    for(unsigned i=0;i<4;i++)GUI_CreateLabelBox(&rows[i],16,44+i*24,448,23,
        &LABEL_FONT,line_text,NULL,(const void *)(uintptr_t)i);
    struct LabelDesc desc={0};desc.fill_color=desc.outline_color=0x1082;
    GUI_CreateRectCB(&preview,16,148,448,124,&desc,draw_preview,NULL);
    GUI_CreateLabelBox(&probe,8,TX15_UI_FOOTER_Y,144,TX15_UI_MIN_HIT,&MENU_FONT,button_text,action,NULL);
    GUI_CreateLabelBox(&stop,168,TX15_UI_FOOTER_Y,144,TX15_UI_MIN_HIT,&MENU_FONT,button_text,action,(const void *)1);
    GUI_CreateLabelBox(&map,328,TX15_UI_FOOTER_Y,144,TX15_UI_MIN_HIT,&MENU_FONT,button_text,action,(const void *)2);
    refreshed=CLOCK_getms();
}
void PAGE_TouchTestEvent(void){
    unsigned now=CLOCK_getms();if((unsigned)(now-refreshed)<50u)return;refreshed=now;
    struct tx15_touch_event event;while(tx15_touch_take(&event)){}
    update(1);
}
void PAGE_TouchTestExit(void){tx15_touch_stop(CLOCK_getms());}
#endif

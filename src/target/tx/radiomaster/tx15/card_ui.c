#ifdef TX15_CARD_UI
#include "common.h"
#include "pages.h"
#include "config/display.h"
#include "card_ui.h"
#include "mix_switch.h"
static struct display_settings saved;
static unsigned active;
static struct {guiObject_t *object;const char *caption;} mix_rows[5];
void tx15_card_mix_rows_reset(void){memset(mix_rows,0,sizeof(mix_rows));}
void tx15_card_mix_row(guiTextSelect_t *field,const char *caption){
    for(unsigned i=0;i<5;i++)if(!mix_rows[i].object || mix_rows[i].object==(guiObject_t *)field){
        mix_rows[i].object=(guiObject_t *)field;mix_rows[i].caption=caption;
        field->desc.style=LABEL_MIX_ROW;return;
    }
}
/* ASCII names are shortened visibly; never spill into the next touch zone. */
static void mix_text(const char *text,unsigned x,unsigned y,unsigned w,unsigned h,
        unsigned font,unsigned color,int right){
    char short_text[96];snprintf(short_text,sizeof(short_text),"%s",text);
    LCD_SetFont(font);u16 tw,th;
    LCD_GetStringDimensions((const u8 *)short_text,&tw,&th);
    if(tw>w || th>h){LCD_SetFont(LABEL_FONT.font);LCD_GetStringDimensions((const u8 *)short_text,&tw,&th);}
    unsigned n=strlen(short_text),trimmed=0;
    while(n && tw>w){short_text[--n]=0;trimmed=1;LCD_GetStringDimensions((const u8 *)short_text,&tw,&th);}
    if(trimmed && n){short_text[n-1]='~';LCD_GetStringDimensions((const u8 *)short_text,&tw,&th);}
    while(n && tw>w){short_text[--n]=0;LCD_GetStringDimensions((const u8 *)short_text,&tw,&th);}
    if(!n || th>h)return;
    LCD_SetFontColor(color);LCD_PrintStringXY(right?x+w-tw:x,y+(h-th)/2,short_text);
}
static void mix_chevron(unsigned x,unsigned y,unsigned c){
    LCD_DrawLine(x,y-4,x+6,y,c);LCD_DrawLine(x+6,y,x,y+4,c);
}
static void mix_plate(guiObject_t *obj,const char *text,const struct LabelDesc *font){
    unsigned x=obj->box.x,y=obj->box.y,w=obj->box.width,h=obj->box.height;
    unsigned editing=obj->Type==TextSelect && (((guiTextSelect_t *)obj)->enable&TX15_SWITCH_EDITING);
    unsigned focus=GUI_GetSelected()==obj;
    LCD_FillRect(x,y,w,h,TX15_CARD_BG);
    if(font->style==LABEL_MIX_TEXT){LCD_FillRect(x,y,w,h,font->fill_color);mix_text(text,x,y,w,h,font->font,font->font_color,font->align==ALIGN_RIGHT);return;}
    if(font->style==LABEL_MIX_TITLE){
        if(focus || editing)LCD_DrawRoundRect(x,y,w,h,5,TX15_CARD_ACCENT);
        mix_text(text,x+(editing?40:0),y,w-(editing?80:8),h,font->font,font->font_color,0);
    }else{
        LCD_FillRoundRect(x,y,w,h,5,font->fill_color);
        if(font->style!=LABEL_MIX_CURVE || focus || editing)
            LCD_DrawRoundRect(x,y,w,h,5,focus || editing?TX15_CARD_ACCENT:font->outline_color);
        if(editing)LCD_DrawRoundRect(x+1,y+1,w-2,h-2,4,TX15_CARD_ACCENT);
        if(font->style==LABEL_MIX_ROW){
            const char *caption="";
            for(unsigned i=0;i<5;i++)if(mix_rows[i].object==obj){caption=mix_rows[i].caption;break;}
            mix_text(caption,x+(editing?44:12),y,64,h,LABEL_FONT.font,TX15_CARD_MUTED,0);
            if(editing)mix_text("EDIT",x+110,y,30,h,LABEL_FONT.font,TX15_CARD_ACCENT,0);
            mix_text(text,x+148,y,w-148-(editing?40:36),h,font->font,font->font_color,1);
            if(!editing)mix_chevron(x+w-24,y+h/2,TX15_CARD_MUTED);
        }else if(font->style==LABEL_MIX_CURVE){
            if(!editing)mix_text("Curve",x+12,y,52,h,LABEL_FONT.font,TX15_CARD_MUTED,0);
            mix_text(text,x+(editing?40:68),y,w-(editing?80:80),h,LABEL_FONT.font,font->font_color,1);
        }else{
            LCD_SetFont(font->font);u16 tw,th;LCD_GetStringDimensions((const u8 *)text,&tw,&th);
            if(tw>w-12 || th>h-4){LCD_SetFont(LABEL_FONT.font);LCD_GetStringDimensions((const u8 *)text,&tw,&th);}
            if(tw<=w-12 && th<=h-4){LCD_SetFontColor(font->font_color);LCD_PrintStringXY(x+(w-tw)/2,y+(h-th)/2,text);}
        }
    }
    if(editing){
        LCD_DrawFastHLine(x+12,y+h/2,16,TX15_CARD_ACCENT);
        LCD_DrawFastHLine(x+w-28,y+h/2,16,TX15_CARD_ACCENT);
        LCD_DrawFastVLine(x+w-20,y+h/2-8,17,TX15_CARD_ACCENT);
    }
}
struct LabelDesc tx15_card_font(unsigned large){
    struct LabelDesc font=large?BUTTON_FONT:LABEL_FONT;
    font.style=LABEL_PANEL;font.align=ALIGN_CENTER;
    font.font_color=TX15_CARD_FG;font.fill_color=TX15_CARD_FILL;
    font.outline_color=TX15_CARD_EDGE;return font;
}
void tx15_card_draw_plate(guiObject_t *obj,const char *text,const struct LabelDesc *font){
    if(font->style>=LABEL_MIX_ROW && font->style<=LABEL_MIX_ACTION){mix_plate(obj,text,font);return;}
    unsigned x=obj->box.x,y=obj->box.y,w=obj->box.width,h=obj->box.height;
    LCD_FillRect(x,y,w,h,TX15_CARD_BG); /* Clear the previous square focus outline, including corners. */
    LCD_FillRoundRect(x,y,w,h,5,font->fill_color);
    LCD_DrawRoundRect(x,y,w,h,5,font->outline_color);
    unsigned adjusting=obj->Type==TextSelect
        && (((guiTextSelect_t *)obj)->enable&TX15_SWITCH_EDITING) && w>=120 && h>=40;
    unsigned available=w-(adjusting?88:8);
    if(adjusting){
        LCD_DrawFastHLine(x+12,y+h/2,16,TX15_CARD_ACCENT);
        LCD_DrawFastHLine(x+w-28,y+h/2,16,TX15_CARD_ACCENT);
        LCD_DrawFastVLine(x+w-20,y+h/2-8,17,TX15_CARD_ACCENT);
    }
    LCD_SetFont(font->font);u16 tw,th;
    LCD_GetStringDimensions((const u8 *)text,&tw,&th);
    if(tw>available || th>h-4){LCD_SetFont(LABEL_FONT.font);LCD_GetStringDimensions((const u8 *)text,&tw,&th);}
    if(tw>available || th>h-4)return;
    LCD_SetFontColor(font->font_color);
    LCD_PrintStringXY(font->align==ALIGN_LEFT?x+6:x+(w-tw)/2,y+(h-th)/2,text);
}
void tx15_card_page_theme(int page){
    int on=page==PAGEID_MENU || page==PAGEID_MODELMNU || page==PAGEID_TXMENU || page==PAGEID_MIXTEMPL || page==PAGEID_MIXER;
    if(on && !active){saved=Display;active=1;}
    if(!on && active){Display=saved;active=0;}
    if(!on)return;
    Display.background.drawn_background=1;
    Display.background.bg_color=Display.background.hd_color=TX15_CARD_BG;
    Display.select_color=TX15_CARD_ACCENT;Display.select_width=2;
    for(unsigned i=0;i<NUM_LABELS;i++)Display.font[i].font_color=TX15_CARD_FG;
    Display.xygraph.bg_color=TX15_CARD_FILL;Display.xygraph.fg_color=TX15_CARD_ACCENT;
    Display.xygraph.grid_color=TX15_CARD_EDGE;Display.xygraph.axis_color=TX15_CARD_MUTED;
    Display.xygraph.point_color=TX15_CARD_ACCENT;Display.xygraph.outline_color=TX15_CARD_EDGE;
}
void tx15_card_draw_label(guiLabel_t *label,const char *text){
    guiObject_t *obj=(guiObject_t *)label;
    unsigned x=obj->box.x,y=obj->box.y,w=obj->box.width,h=obj->box.height;
    LCD_FillRect(x,y,w,h,TX15_CARD_BG);
    unsigned c=GUI_GetSelected()==obj?TX15_CARD_ACCENT:TX15_CARD_MUTED;
    LCD_FillRoundRect(x,y,w,h,7,TX15_CARD_FILL);
    LCD_DrawRoundRect(x,y,w,h,7,TX15_CARD_EDGE);
    unsigned ix=x+w/2-20,iy=y+14;
    unsigned page=(uintptr_t)label->cb_data;
    if(page==PAGEID_MODELMNU){
        LCD_DrawLine(ix+20,iy,ix+15,iy+14,c);LCD_DrawLine(ix+20,iy,ix+25,iy+14,c);
        LCD_DrawLine(ix+15,iy+14,ix,iy+24,c);LCD_DrawLine(ix+25,iy+14,ix+40,iy+24,c);
        LCD_DrawLine(ix,iy+24,ix+17,iy+21,c);LCD_DrawLine(ix+40,iy+24,ix+23,iy+21,c);
        LCD_DrawLine(ix+17,iy+21,ix+17,iy+34,c);LCD_DrawLine(ix+23,iy+21,ix+23,iy+34,c);
        LCD_DrawLine(ix+10,iy+34,ix+30,iy+34,c);
    }else if(page==PAGEID_TXMENU){
        LCD_DrawRoundRect(ix+2,iy+8,36,28,4,c);
        LCD_DrawLine(ix+16,iy+8,ix+24,iy,c);
        LCD_DrawRect(ix+7,iy+16,10,10,c);LCD_DrawRect(ix+24,iy+16,10,10,c);
    }else{
        /* Resource-free icon for tools: screen with three controls. */
        LCD_DrawRoundRect(ix,iy+2,40,30,4,c);
        for(unsigned i=0;i<3;i++){
            LCD_DrawFastVLine(ix+10+i*10,iy+9,17,c);
            LCD_DrawFastHLine(ix+7+i*10,iy+13+i*4,7,c);
        }
    }
    LCD_SetFont(label->desc.font);u16 tw,th;
    LCD_GetStringDimensions((const u8 *)text,&tw,&th);
    if(tw>w-8){LCD_SetFont(LABEL_FONT.font);LCD_GetStringDimensions((const u8 *)text,&tw,&th);}
    if(tw>w-8)return; /* Never draw across the adjacent touch target. */
    LCD_SetFontColor(TX15_CARD_FG);LCD_PrintStringXY(x+(w-tw)/2,y+65,text);
}
#endif

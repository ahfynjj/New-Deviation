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
#include "../pages.h"

#include "../../common/advanced/_mixer_curves.c"
#ifdef TX15_CARD_UI
#include "card_ui.h"
#include "mix_switch.h"
static guiLabel_t tx15_curve_actions[2],tx15_curve_title;
static const char *tx15_curve_caption(guiObject_t *o,const void *data){(void)o;return data?"OK":"Cancel";}
static void tx15_curve_action(guiObject_t *o,s8 press,const void *data){
    if(press==-1){tx15_mix_switch_forget(GUI_GetSelected());okcancel_cb(o,data);}
}
static u8 tx15_curve_point(s16 *x,s16 *y,u8 pos,void *data){
    (void)data;if(pos)return 0;u8 type=CURVE_TYPE(&edit->curve);
    int n=edit->pointnum<0?0:edit->pointnum;
    *x=type>=CURVE_3POINT?CHAN_MIN_VALUE+n*(CHAN_MAX_VALUE-CHAN_MIN_VALUE)/((type-CURVE_3POINT)*2+2):0;
    if(edit->reverse)*x=-*x;
    *y=show_curve_cb(*x,NULL);return 1;
}
static void tx15_curve_cards(void){
    tx15_mix_touch_begin(PAGEID_EDITCURVE);
    struct LabelDesc f=tx15_card_font(1),title=f;title.style=LABEL_MIX_TEXT;title.fill_color=TX15_CARD_BG;
    GUI_CreateLabelBox(&tx15_curve_title,12,0,456,40,&title,NULL,NULL,"Curve editor");
    guiTextSelect_t *fields[]={&gui->name,&gui->smooth,&gui->point,&gui->value};
    const char *captions[]={"Curve","Smooth","Point","Value"};
    const char *(*values[])(guiObject_t *,int,void *)={set_curvename_cb,set_smooth_cb,
        CURVE_TYPE(&edit->curve)>=CURVE_3POINT?set_pointnum_cb:set_expopoint_cb,set_value_cb};
    for(unsigned i=0;i<4;i++){
        GUI_CreateTextSelectPlate(fields[i],12,44+i*44,292,40,&f,NULL,values[i],NULL);
        tx15_mix_value_register(fields[i]);tx15_card_mix_row(fields[i],captions[i]);
    }
    u8 type=CURVE_TYPE(&edit->curve);
    GUI_SetHidden((guiObject_t *)&gui->smooth,type<CURVE_3POINT);
    GUI_SetHidden((guiObject_t *)&gui->point,type<CURVE_EXPO);
    GUI_CreateXYGraph(&gui->graph,320,60,144,176,CHAN_MIN_VALUE,CHAN_MIN_VALUE,CHAN_MAX_VALUE,CHAN_MAX_VALUE,
        PCT_TO_RANGE(50),PCT_TO_RANGE(50),show_curve_cb,tx15_curve_point,touch_cb,&edit->curve);
    tx15_mix_touch_add((guiObject_t *)&gui->graph);
    f.style=LABEL_MIX_ACTION;
    GUI_CreateLabelBox(&tx15_curve_actions[0],12,280,216,40,&f,tx15_curve_caption,tx15_curve_action,NULL);
    f.fill_color=TX15_CARD_ACCENT;f.font_color=TX15_CARD_BG;
    GUI_CreateLabelBox(&tx15_curve_actions[1],252,280,216,40,&f,tx15_curve_caption,tx15_curve_action,(void *)1);
}
#endif

static const int ADDITIONAL_H = (LCD_HEIGHT - 240); // additional space for the bigger Devo12-screen

void PAGE_EditCurvesInit(int page)
{
    (void)page;
    struct Curve *curve = edit->curveptr;
    u8 type = CURVE_TYPE(curve);
    edit->pointnum = 0;
    edit->reverse = MIXER_SRC_IS_INV(pagemem.u.mixer_page.cur_mixer->src);
    if ((type == CURVE_EXPO || type == CURVE_DEADBAND)
        && curve->points[0] == curve->points[1])
    {
        edit->pointnum = -1;
    }
    edit->curve = *curve;
#ifdef TX15_CARD_UI
    tx15_curve_cards();return;
#endif
    GUI_CreateTextSelect(&gui->name, 8, 8, TEXTSELECT_96, NULL, set_curvename_cb, NULL);
    PAGE_CreateCancelButton(LCD_WIDTH-160, 4, okcancel_cb);
    PAGE_CreateOkButton(LCD_WIDTH-56, 4, okcancel_cb);
    int y = 40;
    if (type >= CURVE_3POINT) {
        GUI_CreateLabelBox(&gui->smoothlbl, 8, y, 96, 0, &LABEL_FONT, GUI_Localize, NULL, _tr_noop("Smooth"));
        GUI_CreateTextSelect(&gui->smooth, 8, y+16, TEXTSELECT_96, NULL, set_smooth_cb, NULL);
        y += 40;
        GUI_CreateLabelBox(&gui->pointlbl, 8, y, 96, 0, &LABEL_FONT, GUI_Localize, NULL, _tr_noop("Point"));
        GUI_CreateTextSelect(&gui->point, 8, y+16, TEXTSELECT_96, NULL, set_pointnum_cb, NULL);
    } else if(type == CURVE_DEADBAND || type == CURVE_EXPO) {
        GUI_CreateLabelBox(&gui->pointlbl, 8, y, 96, 0, &LABEL_FONT, GUI_Localize, NULL, _tr_noop("Pos/Neg"));
        GUI_CreateTextSelect(&gui->point, 8, y+16, TEXTSELECT_96, NULL, set_expopoint_cb, NULL);
    }
    y += 40;
    GUI_CreateLabelBox(&gui->valuelbl, 8, y, 96, 0, &LABEL_FONT, GUI_Localize, NULL, _tr_noop("Value"));
    GUI_CreateTextSelect(&gui->value, 8, y+16, TEXTSELECT_96, NULL, set_value_cb, NULL);
    GUI_CreateXYGraph(&gui->graph, LCD_WIDTH-208-ADDITIONAL_H, 36, 200+ADDITIONAL_H, 200+ADDITIONAL_H,
                              CHAN_MIN_VALUE, CHAN_MIN_VALUE,
                              CHAN_MAX_VALUE, CHAN_MAX_VALUE,
                              CHAN_MAX_VALUE / 4, CHAN_MAX_VALUE / 4,
                              show_curve_cb, NULL, touch_cb, &edit->curve);
}

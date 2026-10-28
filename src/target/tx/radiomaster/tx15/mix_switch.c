/* Explicit Mix field editing, using existing controls/analog samples.
 * GPL-3.0-or-later. */
#include "common.h"
#define ENABLE_GUIOBJECT
#include "gui/gui.h"
#include "pages.h"
#include "config/tx.h"
#include "mix_switch.h"
#include "knob_capture.h"
extern volatile u32 tx15_analog_status;
static guiTextSelect_t *editing;
static struct tx15_switch_capture capture;
static struct tx15_knob_capture knobs;
static buttonAction_t action;
static unsigned long_handled,exit_consumed;

void tx15_mix_switch_register(guiTextSelect_t *field) {field->enable|=TX15_SWITCH_FIELD;}
void tx15_mix_source_register(guiTextSelect_t *field) {field->enable|=TX15_SOURCE_FIELD;}
void tx15_mix_value_register(guiTextSelect_t *field) {field->enable|=TX15_VALUE_FIELD;}
static int read_knobs(int armed,int values[2]) {
    values[0]=CHAN_ReadInput(INP_S1);values[1]=CHAN_ReadInput(INP_S2);
    return tx15_knob_capture_step(&knobs,values,tx15_analog_status==4,armed);
}
static guiTextSelect_t *selected_field(void) {
    if(PAGE_GetID()!=PAGEID_MIXTEMPL || GUI_IsModal())return NULL;
    guiObject_t *obj=GUI_GetSelected();
    if(!obj || obj->Type!=TextSelect || !OBJ_IS_USED(obj) || OBJ_IS_HIDDEN(obj))return NULL;
    guiTextSelect_t *field=(guiTextSelect_t *)obj;
    return (field->enable&(TX15_SWITCH_FIELD|TX15_SOURCE_FIELD|TX15_VALUE_FIELD))
        && (field->enable&1) && field->ValueCB
        && ((field->enable&TX15_VALUE_FIELD) || field->InputValueCB)?field:NULL;
}
static void end_edit(void) {
    if(editing) {editing->enable&=~TX15_SWITCH_EDITING;GUI_Redraw((guiObject_t *)editing);}
    editing=NULL;tx15_switch_capture_step(&capture,&tx15_controls,0);
    knobs.seeded=0;
}
void tx15_mix_switch_forget(guiObject_t *object) {
    /* Called before an object is unlinked or its page storage is reused. */
    if((guiObject_t *)editing==object)end_edit();
}
static unsigned buttons(u32 keys,unsigned flags,void *data) {
    (void)data;
    if(exit_consumed && CHAN_ButtonIsPressed(keys,BUT_EXIT)) {
        if(flags&BUTTON_RELEASE)exit_consumed=0;
        return 1;
    }
    guiTextSelect_t *field=selected_field();
    if(editing && editing!=field)end_edit();
    if(!field) {long_handled=0;return 0;}
    if(CHAN_ButtonIsPressed(keys,BUT_ENTER)) {
        if((flags&BUTTON_LONGPRESS) && !long_handled) {
            long_handled=1;
            if(field->SelectCB)field->SelectCB((guiObject_t *)field,field->cb_data);
        }
        if(flags&BUTTON_RELEASE) {
            if(!long_handled && !(flags&BUTTON_HAD_LONGPRESS)) {
                if(editing)end_edit();
                else {
                    editing=field;editing->enable|=TX15_SWITCH_EDITING;
                    tx15_switch_capture_step(&capture,&tx15_controls,0);
                    tx15_switch_capture_step(&capture,&tx15_controls,1);
                    int values[2];knobs.seeded=0;read_knobs(1,values);
                    GUI_Redraw((guiObject_t *)field);
                }
            }
            long_handled=0;
        }
        return 1;
    }
    if(editing && CHAN_ButtonIsPressed(keys,BUT_EXIT)) {
        exit_consumed=!(flags&BUTTON_RELEASE);end_edit();return 1;
    }
    if(editing) {
        int dir=CHAN_ButtonIsPressed(keys,BUT_UP) || CHAN_ButtonIsPressed(keys,BUT_LEFT)?-1:1;
        if((flags&(BUTTON_PRESS|BUTTON_LONGPRESS)) && field->ValueCB) {
            field->ValueCB((guiObject_t *)field,(flags&BUTTON_LONGPRESS)?2*dir:dir,field->cb_data);
            GUI_Redraw((guiObject_t *)field);
        }
        return 1;
    }
    return 0;
}
void tx15_mix_switch_init(void) {
    end_edit();long_handled=exit_consumed=0;
    BUTTON_RegisterCallback(&action,CHAN_ButtonMask(BUT_ENTER)|CHAN_ButtonMask(BUT_EXIT)|
        CHAN_ButtonMask(BUT_UP)|CHAN_ButtonMask(BUT_DOWN)|CHAN_ButtonMask(BUT_LEFT)|CHAN_ButtonMask(BUT_RIGHT),
        BUTTON_PRESS|BUTTON_RELEASE|BUTTON_LONGPRESS|BUTTON_PRIORITY,buttons,NULL);
}
void tx15_mix_field_touch(guiObject_t *field){
    if(editing && (guiObject_t *)editing!=field)end_edit();
    GUI_SetSelected(field);
    (void)buttons(CHAN_ButtonMask(BUT_ENTER),BUTTON_RELEASE,NULL);
}
void tx15_mix_field_step(guiObject_t *field,int direction){
    if((direction!=1 && direction!=-1) || !editing
        || field!=(guiObject_t *)editing || selected_field()!=editing)return;
    editing->ValueCB(field,direction,editing->cb_data);
    /* ValueCB may rebuild the template or enter another page. */
    if((guiObject_t *)editing==field && selected_field()==editing)GUI_Redraw(field);
}
void tx15_mix_switch_poll(void) {
    if(!editing)return;
    if(editing!=selected_field()) {end_edit();return;}
    if(editing->enable&TX15_VALUE_FIELD)return; /* Numeric fields never capture hardware sources. */
    unsigned source;int value=CHAN_MAX_VALUE;
    if(editing->enable&TX15_SOURCE_FIELD) {
        int values[2];int event=read_knobs(1,values);
        if(!event)return;
        source=event==1?INP_S1:INP_S2;value=values[event-1];
    } else {
        int event=tx15_switch_capture_step(&capture,&tx15_controls,1);
        if(!event)return;
        static const unsigned first[]={INP_SWA0,INP_SWB0,INP_SWC0,INP_SWD0,INP_SWE0,INP_SWF0};
        source=first[(event-1)/3]+(event-1)%3;
    }
    if(Transmitter.ignore_src&(1u<<source))return;
    editing->InputValueCB((guiObject_t *)editing,source,value,editing->cb_data);
    GUI_Redraw((guiObject_t *)editing);
}

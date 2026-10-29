/* Native limit editor; original live-edit/Revert semantics are intentional. */
static unsigned tx15_limit_bank;
static guiLabel_t tx15_limit_actions[4];
static guiTextSelect_t *tx15_limit_field(unsigned i){
    guiTextSelect_t *fields[]={&gui->reverse,&gui->failsafe,&gui->safety,&gui->safeval,&gui->min,
        &gui->max,&gui->scaleneg,&gui->scale,&gui->subtrim,&gui->speed};return fields[i];
}
static const char *tx15_limit_caption(guiObject_t *o,const void *data){
    (void)o;switch((uintptr_t)data){case 0:return "Back";case 1:return tx15_limit_bank?"Page 2/2":"Page 1/2";
    case 2:return "Revert";default:return mp->limit->flags&CH_FAILSAFE_EN?"FS: On":"FS: Off";}
}
static void tx15_limit_visibility(void){
    for(unsigned i=0;i<10;i++)GUI_SetHidden((guiObject_t *)tx15_limit_field(i),i/5!=tx15_limit_bank);
}
static void tx15_limit_action(guiObject_t *o,s8 press,const void *data){
    if(press!=-1)return;tx15_mix_switch_forget(GUI_GetSelected());tx15_mix_touch_changed();
    switch((uintptr_t)data){case 0:PAGE_Pop();return;
    case 1:tx15_limit_bank^=1;tx15_limit_visibility();GUI_SetSelected((guiObject_t *)tx15_limit_field(tx15_limit_bank*5));GUI_Redraw(&tx15_limit_actions[1]);break;
    case 2:revert_cb(o,NULL);break;
    case 3:toggle_failsafe_cb(o,NULL);GUI_Redraw(&gui->failsafe);GUI_Redraw(&tx15_limit_actions[3]);break;}
}
static void tx15_limit_title(void){
    tx15_mix_touch_begin(PAGEID_EDITLIMIT);tx15_limit_bank=0;
    struct LabelDesc f=tx15_card_font(1);f.style=LABEL_MIX_TEXT;f.fill_color=TX15_CARD_BG;
    GUI_CreateLabelBox(&gui->title,12,0,292,40,&f,MIXPAGE_ChanNameProtoCB,NULL,(void *)(uintptr_t)mp->channel);
    f.style=LABEL_MIX_ACTION;
    for(unsigned i=0;i<4;i++)GUI_CreateLabelBox(&tx15_limit_actions[i],i==3?328:12+i*156,i==3?0:280,i==3?140:144,40,
        &f,tx15_limit_caption,tx15_limit_action,(void *)(uintptr_t)i);
}
static void tx15_limit_cards(void){
    const char *captions[]={"Reverse","Fail-safe","Safety","Safe value","Min limit","Max limit","Scale -","Scale +","Subtrim","Speed"};
    const char *(*values[])(guiObject_t *,int,void *)={reverse_cb,set_failsafe_cb,set_source_cb,set_safeval_cb,set_limits_cb,
        set_limits_cb,set_limitsscale_cb,set_limitsscale_cb,set_trimstep_cb,set_limits_cb};
    void *data[]={(void *)(uintptr_t)mp->channel,NULL,&mp->limit->safetysw,NULL,&mp->limit->min,
        &mp->limit->max,&mp->limit->servoscale_neg,&mp->limit->servoscale,&mp->limit->subtrim,&mp->limit->speed};
    struct LabelDesc f=tx15_card_font(1);
    for(unsigned i=0;i<10;i++){
        guiTextSelect_t *field=tx15_limit_field(i);
        if(i==2){GUI_CreateTextSourcePlate(field,12,44+(i%5)*44,456,40,&f,sourceselect_cb,values[i],set_input_source_cb,data[i]);tx15_mix_switch_register(field);}
        else{GUI_CreateTextSelectPlate(field,12,44+(i%5)*44,456,40,&f,i==0?toggle_reverse_cb:i==1?toggle_failsafe_cb:NULL,values[i],data[i]);tx15_mix_value_register(field);}
        tx15_card_mix_row(field,captions[i]);
    }
    update_safe_val_state();tx15_limit_visibility();
}

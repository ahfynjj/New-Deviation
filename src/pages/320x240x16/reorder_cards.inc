static guiLabel_t tx15_order_actions[9],tx15_order_title;
static void tx15_order_action(guiObject_t *obj,s8 press,const void *data){
    if(press!=-1)return;tx15_mix_switch_forget(GUI_GetSelected());tx15_mix_touch_changed();
    unsigned a=(uintptr_t)data;
    if(a==SAVE){okcancel_cb(obj,(void *)1);return;}
    if(a==6){okcancel_cb(obj,NULL);return;}
    if(a==7 || a==8){
        int row=GUI_ScrollableCurrentRow(&gui->scrollable)+(a==7?-5:5);
        int last=rl.max>5?rl.max-5:0;if(row<0)row=0;if(row>last)row=last;
        GUI_SetSelected(GUI_ShowScrollableRowOffset(&gui->scrollable,row<<8));return;
    }
    press_button_cb(obj,data);
}
static const char *tx15_order_caption(guiObject_t *obj,const void *data){
    switch((uintptr_t)data){case 6:return "Cancel";case 7:return "Previous";case 8:return "Next";default:return _show_button_cb(obj,data);}
}
static void tx15_order_select(guiObject_t *o,s8 press,const void *data){
    (void)o;if(press!=-1 || (uintptr_t)data>=rl.count)return;
    tx15_mix_switch_forget(GUI_GetSelected());rl.selected=(uintptr_t)data;redraw();
}
static int tx15_order_row(int row,int relative,int y,void *data){
    (void)data;struct LabelDesc f=tx15_card_font(0);f.style=LABEL_MIX_ACTION;
    GUI_CreateLabelBox(&gui->name[relative],316,y,144,40,&f,list_cb,tx15_order_select,(void *)(uintptr_t)row);return 1;
}
static void tx15_order_cards(int requested){
    tx15_mix_touch_begin(PAGEID_REORDER);
    struct LabelDesc f=tx15_card_font(1),title=f;title.style=LABEL_MIX_TEXT;title.fill_color=TX15_CARD_BG;
    GUI_CreateLabelBox(&tx15_order_title,12,0,292,40,&title,NULL,NULL,"Mixer order");
    GUI_CreateTextSelectPlate(&gui->value,12,44,292,40,&f,NULL,value_val_cb,NULL);
    GUI_CreateTextSelectPlate(&gui->copy,12,88,292,40,&f,NULL,copy_val_cb,NULL);
    tx15_mix_value_register(&gui->value);tx15_mix_value_register(&gui->copy);
    tx15_card_mix_row(&gui->value,"Selected");tx15_card_mix_row(&gui->copy,"Copy to");
    f.style=LABEL_MIX_ACTION;
    const unsigned xs[]={12,164,12,12,164,328,12,168,324};
    const unsigned ys[]={140,140,184,228,228,0,280,280,280};
    for(unsigned i=0;i<9;i++){
        if((i==INSERT || i==REMOVE) && !requested)continue;
        struct LabelDesc button=f;if(i==SAVE){button.fill_color=TX15_CARD_ACCENT;button.font_color=TX15_CARD_BG;}
        GUI_CreateLabelBox(&tx15_order_actions[i],xs[i],ys[i],i==APPLY?292:i>=6?144:140,40,&button,
            tx15_order_caption,tx15_order_action,(void *)(uintptr_t)i);
    }
    GUI_CreateScrollable(&gui->scrollable,316,44,164,220,44,rl.max,tx15_order_row,NULL,NULL,NULL);
}

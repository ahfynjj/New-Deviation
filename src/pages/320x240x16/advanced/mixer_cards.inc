/* TX15 Complex editor: existing Deviation callbacks and data, native geometry.
 * Included after the common mixer implementation; GPL-3.0-or-later. */
static unsigned tx15_mix_card_more,tx15_mix_card_generation,tx15_mix_expo_rate;
static void tx15_mix_expo_visibility(void);
static guiLabel_t tx15_mix_expo_link[2],tx15_mix_expo_note,tx15_mix_preview_title;
static guiLabel_t tx15_mix_card_footer[3],tx15_mix_card_trim,tx15_mix_card_curve_edit;
static guiLabel_t tx15_mix_card_position;
static guiLabel_t tx15_mix_card_empty;
static guiLabel_t tx15_mix_card_panel,tx15_mix_card_output_label,tx15_mix_card_output;
/* Clip only the preview; the real mixer and its +/-125% evaluation stay intact. */
static s32 tx15_mix_card_plot_cb(s32 x,void *data){
    s32 y=eval_mixer_cb(x,data);
    return y>CHAN_MAX_VALUE?CHAN_MAX_VALUE:y<CHAN_MIN_VALUE?CHAN_MIN_VALUE:y;
}
static u8 tx15_mix_card_point_cb(s16 *x,s16 *y,u8 pos,void *data){
    if(!curpos_cb(x,y,pos,data))return 0;
    if(*y>CHAN_MAX_VALUE)*y=CHAN_MAX_VALUE;
    if(*y<CHAN_MIN_VALUE)*y=CHAN_MIN_VALUE;
    return 1;
}
static const char *tx15_mix_card_output_cb(guiObject_t *obj,const void *data){
    (void)obj;(void)data;
    snprintf(tempstring,sizeof(tempstring),"%+ld %%",(long)(eval_chan_cb(NULL)*100/CHAN_MAX_VALUE));
    return tempstring;
}
static const char *tx15_mix_card_percent_cb(guiObject_t *obj,int dir,void *data){
    set_number100_cb(obj,dir,data);
    snprintf(tempstring,sizeof(tempstring),"%d %%",*(s8 *)data);return tempstring;
}
static const char *tx15_mix_card_template_cb(guiObject_t *obj,int dir,void *data){
    const char *name=templatetype_cb(obj,dir,data);
    if(dir)return name;
    char template_name[32];snprintf(template_name,sizeof(template_name),"%s",name);
    const char *channel=MIXPAGE_ChanNameProtoCB(NULL,(const void *)(uintptr_t)mp->cur_mixer->dest);
    static char title[80];snprintf(title,sizeof(title),"%s / %s",channel,template_name);return title;
}
static const char *tx15_mix_card_position_cb(guiObject_t *o,const void *data){
    (void)o;(void)data;
    if(mp->cur_template==MIXERTEMPLATE_EXPO_DR)return tx15_mix_expo_rate==0?"High rate":tx15_mix_expo_rate==1?"Mid rate":"Low rate";
    if(!mp->num_mixers)return "No mixer";
    snprintf(tempstring,sizeof(tempstring),"Mix %u/%u",(unsigned)(mp->cur_mixer-mp->mixer)+1,mp->num_mixers);
    return tempstring;
}
static const char *tx15_mix_card_caption(guiObject_t *o,const void *data){
    (void)o;
    switch((uintptr_t)data){case 7:return "Cancel";case 8:
        return mp->cur_template==MIXERTEMPLATE_EXPO_DR?"Next rate":mp->cur_template==MIXERTEMPLATE_SIMPLE?"Edit curve":mp->cur_template==MIXERTEMPLATE_NONE?"Template":tx15_mix_card_more?"Basic 2/2":"More 1/2";
        case 9:return "OK";default:return "Edit curve";}
}
static void tx15_mix_card_visibility(void){
    guiObject_t *primary[]={
        (guiObject_t *)&gui3->srclbl,(guiObject_t *)&gui3->src,
        (guiObject_t *)&gui3->swlbl,(guiObject_t *)&gui3->sw,
        (guiObject_t *)&gui3->muxlbl,(guiObject_t *)&gui3->mux,
        (guiObject_t *)&gui3->scalelbl,(guiObject_t *)&gui3->scale,
        (guiObject_t *)&gui3->offsetlbl,(guiObject_t *)&gui3->offset};
    for(unsigned i=0;i<sizeof(primary)/sizeof(*primary);i++)GUI_SetHidden(primary[i],!(i&1) || tx15_mix_card_more);
    GUI_SetHidden((guiObject_t *)&gui3->nummixlbl,1);
    GUI_SetHidden((guiObject_t *)&gui3->nummix,!tx15_mix_card_more);
    GUI_SetHidden((guiObject_t *)&gui3->pagelbl,1);
    GUI_SetHidden((guiObject_t *)&gui3->page,!tx15_mix_card_more);
    GUI_SetHidden((guiObject_t *)&tx15_mix_card_trim,!tx15_mix_card_more
        || !MIXER_SourceHasTrim(MIXER_SRC(mp->mixer[0].src)));
}
static void tx15_mix_card_more_cb(guiObject_t *obj,s8 press,const void *data){
    (void)obj;(void)data;if(press!=-1)return;
    tx15_mix_switch_forget(GUI_GetSelected());
    tx15_mix_touch_changed();
    if(mp->cur_template==MIXERTEMPLATE_EXPO_DR){tx15_mix_expo_rate=(tx15_mix_expo_rate+1)%3;tx15_mix_expo_visibility();GUI_Redraw(&tx15_mix_card_position);GUI_SetSelected((guiObject_t *)&gui2->src);return;}
    if(mp->cur_template==MIXERTEMPLATE_NONE){tx15_mix_field_touch((guiObject_t *)&gui->tmpl);return;}
    if(mp->cur_template==MIXERTEMPLATE_SIMPLE){curveselect_cb((guiObject_t *)&gui1->curve,&mp->mixer[0]);return;}
    tx15_mix_card_more^=1;tx15_mix_card_generation++;
    tx15_mix_card_visibility();
    GUI_Redraw(&tx15_mix_card_footer[1]);
    GUI_SetSelected((guiObject_t *)(tx15_mix_card_more?&gui3->nummix:&gui3->src));
}
static void tx15_mix_card_action(guiObject_t *obj,s8 press,const void *data){
    if(press!=-1)return;
    unsigned action=(uintptr_t)data;
    tx15_mix_switch_forget(GUI_GetSelected());
    if(action==7 || action==9)okcancel_cb(obj,(const void *)(uintptr_t)(action==9));
    else if(action==10){toggle_trim_cb(obj,NULL);GUI_Redraw(&tx15_mix_card_trim);}
    else if(action==11){
        if(mp->cur_template==MIXERTEMPLATE_EXPO_DR){
            unsigned r=tx15_mix_expo_rate;
            if(r && (!MIXER_SRC(mp->mixer[r].sw) || (mp->link_curves&r)))return;
            curveselect_cb((guiObject_t *)(r?&gui2->curve[r-1]:&gui2->curvehi),&mp->mixer[r]);
        }
        else curveselect_cb((guiObject_t *)(mp->cur_template==MIXERTEMPLATE_SIMPLE?&gui1->curve:&gui3->curve),mp->cur_mixer);
    }
}
static void tx15_mix_card_label(guiLabel_t *obj,unsigned y,const char *text){
    struct LabelDesc font=tx15_card_font(0);font.align=ALIGN_LEFT;
    GUI_CreateLabelBox(obj,12,y,96,40,&font,NULL,NULL,text);
}
static void tx15_mix_card_header(void){
    tx15_mix_touch_begin(PAGEID_MIXTEMPL);
    tx15_mix_card_more=tx15_mix_expo_rate=0;tx15_mix_card_generation++;
    struct LabelDesc font=tx15_card_font(1);
    GUI_CreateLabelBox(&gui->chan,12,0,80,40,&font,MIXPAGE_ChanNameProtoCB,NULL,
        (const void *)(uintptr_t)mp->cur_mixer->dest);
    GUI_CreateTextSelectPlate(&gui->tmpl,100,0,220,40,&font,NULL,templatetype_cb,(void *)(uintptr_t)mp->channel);
    {
        GUI_SetHidden((guiObject_t *)&gui->chan,1);
        gui->tmpl.header.box=(struct guiBox){12,0,292,40};
        gui->tmpl.desc.style=LABEL_MIX_TITLE;gui->tmpl.ValueCB=tx15_mix_card_template_cb;
    }
    tx15_mix_value_register(&gui->tmpl);
    struct LabelDesc small=tx15_card_font(0);
    {small.style=LABEL_MIX_TEXT;small.align=ALIGN_RIGHT;small.fill_color=TX15_CARD_BG;}
    GUI_CreateLabelBox(&tx15_mix_card_position,328,0,140,40,&small,tx15_mix_card_position_cb,NULL,NULL);
    for(unsigned i=0;i<3;i++){
        struct LabelDesc f=font;
        f.style=LABEL_MIX_ACTION;
        if(i==2){f.fill_color=TX15_CARD_ACCENT;f.font_color=TX15_CARD_BG;}
        GUI_CreateLabelBox(&tx15_mix_card_footer[i],12+i*156,280,144,40,&f,tx15_mix_card_caption,
            i==1?tx15_mix_card_more_cb:tx15_mix_card_action,(const void *)(uintptr_t)(7+i));
    }
}
static void tx15_mix_complex_cards(int page_change){
    (void)page_change;tx15_mix_card_generation++;
    tx15_mix_touch_changed();
    tx15_card_mix_rows_reset();
    struct LabelDesc font=tx15_card_font(1);
    if(!mp->firstObj){
        mp->firstObj=(guiObject_t *)&gui3->nummixlbl;
        tx15_mix_card_label(&gui3->nummixlbl,44,"Mixers");
        GUI_CreateTextSelectPlate(&gui3->nummix,12,44,292,40,&font,NULL,set_nummixers_cb,NULL);
        tx15_mix_value_register(&gui3->nummix);
        tx15_mix_card_label(&gui3->pagelbl,88,"Mixer");
        GUI_CreateTextSelectPlate(&gui3->page,12,88,292,40,&font,reorder_cb,set_mixernum_cb,NULL);
        tx15_mix_value_register(&gui3->page);
    }else GUI_RemoveHierObjects((guiObject_t *)&gui3->swlbl);
    /* swlbl is the first replaceable object, as in the legacy callback lifecycle. */
    tx15_mix_card_label(&gui3->swlbl,88,"Switch");
    GUI_CreateTextSourcePlate(&gui3->sw,12,88,292,40,&font,sourceselect_cb,set_drsource_cb,
        set_input_switch_cb,&mp->cur_mixer->sw);tx15_mix_switch_register(&gui3->sw);
    tx15_mix_card_label(&gui3->srclbl,44,"Source");
    GUI_CreateTextSourcePlate(&gui3->src,12,44,292,40,&font,sourceselect_cb,set_source_cb,
        set_input_source_cb,&mp->cur_mixer->src);tx15_mix_source_register(&gui3->src);
    tx15_mix_card_label(&gui3->muxlbl,132,"Mux");
    GUI_CreateTextSelectPlate(&gui3->mux,12,132,292,40,&font,NULL,set_mux_cb,NULL);tx15_mix_value_register(&gui3->mux);
    tx15_mix_card_label(&gui3->scalelbl,176,"Scale");
    GUI_CreateTextSelectPlate(&gui3->scale,12,176,292,40,&font,NULL,tx15_mix_card_percent_cb,&mp->cur_mixer->scalar);tx15_mix_value_register(&gui3->scale);
    tx15_mix_card_label(&gui3->offsetlbl,220,"Offset");
    GUI_CreateTextSelectPlate(&gui3->offset,12,220,292,40,&font,NULL,tx15_mix_card_percent_cb,&mp->cur_mixer->offset);tx15_mix_value_register(&gui3->offset);
    tx15_card_mix_row(&gui3->src,"Source");tx15_card_mix_row(&gui3->sw,"Switch");
    tx15_card_mix_row(&gui3->mux,"Mux");tx15_card_mix_row(&gui3->scale,"Scale");tx15_card_mix_row(&gui3->offset,"Offset");
    GUI_CreateLabelBox(&tx15_mix_card_panel,316,44,152,172,&font,NULL,NULL,"");
    GUI_CreateXYGraph(&gui3->graph,328,92,128,88,CHAN_MIN_VALUE,CHAN_MIN_VALUE,
        CHAN_MAX_VALUE,CHAN_MAX_VALUE,PCT_TO_RANGE(50),PCT_TO_RANGE(50),tx15_mix_card_plot_cb,tx15_mix_card_point_cb,touch_cb,mp->cur_mixer);
    struct LabelDesc curve_font=font;curve_font.style=LABEL_MIX_CURVE;
    GUI_CreateTextSelectPlate(&gui3->curve,320,48,144,40,&curve_font,curveselect_cb,set_curvename_cb,mp->cur_mixer);tx15_mix_value_register(&gui3->curve);
    struct LabelDesc output_font=tx15_card_font(0);output_font.style=LABEL_MIX_TEXT;
    GUI_CreateLabelBox(&tx15_mix_card_output_label,328,184,52,28,&output_font,NULL,NULL,"Output");
    output_font.font=font.font;output_font.align=ALIGN_RIGHT;
    GUI_CreateLabelBox(&tx15_mix_card_output,384,184,72,28,&output_font,tx15_mix_card_output_cb,NULL,NULL);
    font.style=LABEL_MIX_ACTION;
    GUI_CreateLabelBox(&tx15_mix_card_curve_edit,316,224,152,40,&font,tx15_mix_card_caption,tx15_mix_card_action,(const void *)11);
    GUI_CreateLabelBox(&tx15_mix_card_trim,12,132,292,40,&font,show_trim_cb,tx15_mix_card_action,(const void *)10);
    tx15_card_mix_row(&gui3->nummix,"Mixers");tx15_card_mix_row(&gui3->page,"Mixer");
    GUI_SetHidden((guiObject_t *)&gui3->nummixlbl,1);GUI_SetHidden((guiObject_t *)&gui3->pagelbl,1);
    tx15_mix_card_visibility();
}
static const char *tx15_mix_expo_link_text(guiObject_t *obj,const void *data){
    (void)obj;return mp->link_curves&(1u<<(uintptr_t)data)?"Curve: Linked":"Curve: Independent";
}
static void tx15_mix_expo_link_cb(guiObject_t *obj,s8 press,const void *data){
    if(press==-1){toggle_link_cb(obj,data);GUI_Redraw(&tx15_mix_expo_link[(uintptr_t)data]);tx15_mix_touch_changed();}
}
static void tx15_mix_expo_visibility(void){
    unsigned r=tx15_mix_expo_rate;
    GUI_SetHidden((guiObject_t *)&tx15_mix_card_curve_edit,r && (!MIXER_SRC(mp->mixer[r].sw) || (mp->link_curves&r)));
    GUI_SetHidden((guiObject_t *)&gui2->sw1,r!=1);GUI_SetHidden((guiObject_t *)&gui2->sw2,r!=2);
    GUI_SetHidden((guiObject_t *)&tx15_mix_expo_note,r!=0);
    for(unsigned i=0;i<3;i++){
        int enabled=i==0 || MIXER_SRC(mp->mixer[i].sw);
        guiObject_t *curve=(guiObject_t *)(i?&gui2->curve[i-1]:&gui2->curvehi);
        guiObject_t *scale=(guiObject_t *)(i?&gui2->scale[i-1]:&gui2->scalehi);
        guiObject_t *graph=(guiObject_t *)(i?&gui2->graph[i-1]:&gui2->graphhi);
        GUI_SetHidden(curve,i!=r || !enabled || (i && (mp->link_curves&i)));
        GUI_SetHidden(scale,i!=r || !enabled);GUI_SetHidden(graph,i!=r || !enabled);
        if(i)GUI_SetHidden((guiObject_t *)&tx15_mix_expo_link[i-1],i!=r || !enabled);
    }
}
static void tx15_mix_expo_cards(void){
    sync_mixers();tx15_mix_card_generation++;
    struct LabelDesc f=tx15_card_font(1);
    mp->firstObj=GUI_CreateLabelBox(&gui2->srclbl,12,44,96,40,&f,NULL,NULL,"");
    GUI_SetHidden(mp->firstObj,1);
    GUI_CreateTextSourcePlate(&gui2->src,12,44,292,40,&f,sourceselect_cb,set_source_cb,set_input_source_cb,&mp->mixer[0].src);
    tx15_mix_source_register(&gui2->src);tx15_card_mix_row(&gui2->src,"Source");
    GUI_CreateLabelBox(&tx15_mix_expo_note,12,88,292,40,&f,NULL,NULL,"High rate: always available");
    for(unsigned i=0;i<3;i++){
        guiTextSelect_t *curve=i?&gui2->curve[i-1]:&gui2->curvehi;
        guiTextSelect_t *scale=i?&gui2->scale[i-1]:&gui2->scalehi;
        guiXYGraph_t *graph=i?&gui2->graph[i-1]:&gui2->graphhi;
        if(i){
            guiTextSelect_t *sw=i==1?&gui2->sw1:&gui2->sw2;
            GUI_CreateTextSourcePlate(sw,12,88,292,40,&f,sourceselect_cb,set_drsource_cb,set_input_switch_cb,&mp->mixer[i].sw);
            tx15_mix_switch_register(sw);tx15_card_mix_row(sw,"Switch");
            GUI_CreateLabelBox(&tx15_mix_expo_link[i-1],12,220,292,40,&f,tx15_mix_expo_link_text,tx15_mix_expo_link_cb,(const void *)(uintptr_t)(i-1));
        }
        GUI_CreateTextSelectPlate(curve,12,132,292,40,&f,curveselect_cb,set_curvename_cb,&mp->mixer[i]);
        tx15_mix_value_register(curve);tx15_card_mix_row(curve,"Curve");
        GUI_CreateTextSelectPlate(scale,12,176,292,40,&f,NULL,tx15_mix_card_percent_cb,&mp->mixer[i].scalar);
        tx15_mix_value_register(scale);tx15_card_mix_row(scale,"Scale");
        GUI_CreateXYGraph(graph,328,60,128,144,CHAN_MIN_VALUE,CHAN_MIN_VALUE,CHAN_MAX_VALUE,CHAN_MAX_VALUE,
            PCT_TO_RANGE(50),PCT_TO_RANGE(50),tx15_mix_card_plot_cb,curpos_cb,touch_cb,&mp->mixer[i]);
    }
    f.style=LABEL_MIX_ACTION;
    GUI_CreateLabelBox(&tx15_mix_card_curve_edit,316,224,152,40,&f,tx15_mix_card_caption,tx15_mix_card_action,(const void *)11);
    tx15_mix_expo_visibility();
}
static void tx15_mix_simple_cards(void){
    tx15_mix_card_generation++;
    struct LabelDesc font=tx15_card_font(1);
    mp->firstObj=(guiObject_t *)&gui1->srclbl;
    tx15_mix_card_label(&gui1->srclbl,44,"Source");
    GUI_CreateTextSourcePlate(&gui1->src,12,44,292,40,&font,sourceselect_cb,set_source_cb,
        set_input_source_cb,&mp->mixer[0].src);tx15_mix_source_register(&gui1->src);
    tx15_mix_card_label(&gui1->curvelbl,88,"Curve");
    GUI_CreateTextSelectPlate(&gui1->curve,12,88,292,40,&font,curveselect_cb,set_curvename_cb,&mp->mixer[0]);tx15_mix_value_register(&gui1->curve);
    tx15_mix_card_label(&gui1->scalelbl,132,"Scale");
    GUI_CreateTextSelectPlate(&gui1->scale,12,132,292,40,&font,NULL,set_number100_cb,&mp->mixer[0].scalar);tx15_mix_value_register(&gui1->scale);
    tx15_mix_card_label(&gui1->offsetlbl,176,"Offset");
    GUI_CreateTextSelectPlate(&gui1->offset,12,176,292,40,&font,NULL,set_number100_cb,&mp->mixer[0].offset);tx15_mix_value_register(&gui1->offset);
    tx15_card_mix_row(&gui1->src,"Source");tx15_card_mix_row(&gui1->curve,"Curve");
    tx15_card_mix_row(&gui1->scale,"Scale");tx15_card_mix_row(&gui1->offset,"Offset");
    GUI_SetHidden((guiObject_t *)&gui1->srclbl,1);GUI_SetHidden((guiObject_t *)&gui1->curvelbl,1);
    GUI_SetHidden((guiObject_t *)&gui1->scalelbl,1);GUI_SetHidden((guiObject_t *)&gui1->offsetlbl,1);
    GUI_CreateLabelBox(&tx15_mix_card_panel,316,44,152,172,&font,NULL,NULL,"");
    struct LabelDesc small=tx15_card_font(0);small.style=LABEL_MIX_TEXT;
    GUI_CreateLabelBox(&tx15_mix_preview_title,328,48,128,32,&small,NULL,NULL,"Preview");
    GUI_CreateXYGraph(&gui1->graph,328,92,128,88,CHAN_MIN_VALUE,CHAN_MIN_VALUE,
        CHAN_MAX_VALUE,CHAN_MAX_VALUE,PCT_TO_RANGE(50),PCT_TO_RANGE(50),tx15_mix_card_plot_cb,tx15_mix_card_point_cb,touch_cb,&mp->mixer[0]);
    GUI_CreateLabelBox(&tx15_mix_card_output,328,184,128,28,&small,tx15_mix_card_output_cb,NULL,NULL);
    font.style=LABEL_MIX_ACTION;
    GUI_CreateLabelBox(&tx15_mix_card_curve_edit,316,224,152,40,&font,tx15_mix_card_caption,tx15_mix_card_action,(const void *)11);
}
static void tx15_mix_none_cards(void){
    tx15_mix_card_generation++;
    struct LabelDesc font=tx15_card_font(0);
    mp->firstObj=GUI_CreateLabelBox(&tx15_mix_card_empty,12,64,456,80,&font,NULL,NULL,"Choose a template above");
}
int PAGE_MixCardActive(void){return PAGE_GetID()==PAGEID_MIXTEMPL
    && (mp->cur_template>=MIXERTEMPLATE_NONE);}
int PAGE_MixCardGeneration(void){return tx15_mix_card_generation;}
static int tx15_mix_card_base_hit(unsigned x,unsigned y){
    if(!PAGE_MixCardActive() || x>=480 || y>=320)return -1;
    if(mp->cur_template==MIXERTEMPLATE_NONE && y>=40 && y<280)return -1;
    if(x>=12 && x<304 && y>=44 && y<260){
        unsigned row=(y-44)/44;
        if((y-44)%44>=40)return -1;
        if(mp->cur_template==MIXERTEMPLATE_SIMPLE)return row<4?(int)row:-1;
        if(tx15_mix_card_more && (row>2 || (row==2 && !MIXER_SourceHasTrim(MIXER_SRC(mp->mixer[0].src)))))return -1;
        return row;
    }
    if(mp->cur_template==MIXERTEMPLATE_COMPLEX && x>=316 && x<468 && y>=44 && y<88)return 5;
    if(x>=(mp->cur_template==MIXERTEMPLATE_COMPLEX?12:100) && x<(mp->cur_template==MIXERTEMPLATE_COMPLEX?304:320) && y<40)return 6;
    if(x>=316 && x<468 && y>=224 && y<264)return 11;
    if(x>=12 && y>=280){unsigned c=(x-12)/156;if(c<3 && (x-12)%156<144)return 7+c;}
    return -1;
}
static guiTextSelect_t *tx15_mix_card_field(int hit){
    if(hit==6)return &gui->tmpl;
    if(mp->cur_template==MIXERTEMPLATE_SIMPLE){
        guiTextSelect_t *rows[]={&gui1->src,&gui1->curve,&gui1->scale,&gui1->offset};
        return hit>=0 && hit<4?rows[hit]:NULL;
    }
    if(hit==5)return &gui3->curve;
    if(tx15_mix_card_more)return hit==0?&gui3->nummix:hit==1?&gui3->page:NULL;
    guiTextSelect_t *rows[]={&gui3->src,&gui3->sw,&gui3->mux,&gui3->scale,&gui3->offset};
    return hit>=0 && hit<5?rows[hit]:NULL;
}
int PAGE_MixCardHit(unsigned x,unsigned y){
    int hit=tx15_mix_card_base_hit(x,y);
    if(hit<0 || hit>6)return hit;
    guiTextSelect_t *field=tx15_mix_card_field(hit);
    if(field && (field->enable&TX15_SWITCH_EDITING)){
        struct guiBox *box=&field->header.box;
        if(x>=box->x && x<box->x+40)return 100+hit*2;
        if(x>=box->x+box->width-40 && x<box->x+box->width)return 101+hit*2;
    }
    return hit;
}
void PAGE_MixCardTap(unsigned x,unsigned y){
    int hit=PAGE_MixCardHit(x,y);
    if(hit<0)return;
    if(hit>=100){
        guiTextSelect_t *field=tx15_mix_card_field((hit-100)/2);
        if(field)tx15_mix_field_step((guiObject_t *)field,hit&1?1:-1);
        return;
    }
    if(hit==8){tx15_mix_card_more_cb(NULL,-1,NULL);return;}
    if(hit>=7){tx15_mix_card_action(NULL,-1,(const void *)(uintptr_t)hit);return;}
    if(mp->cur_template==MIXERTEMPLATE_COMPLEX && tx15_mix_card_more && hit==2){
        tx15_mix_card_action(NULL,-1,(const void *)10);return;
    }
    guiTextSelect_t *field=tx15_mix_card_field(hit);
    if(field)tx15_mix_field_touch((guiObject_t *)field);
}

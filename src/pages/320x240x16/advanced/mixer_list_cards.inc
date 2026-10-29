/* Five-row native Mixer list, using existing channel and template callbacks. */
static guiLabel_t tx15_mixer_list_edit[5],tx15_mixer_list_footer[3],tx15_mixer_list_tools[2];
static unsigned tx15_mixer_list_channel(unsigned row){
    return row<Model.num_channels?row:row+NUM_OUT_CHANNELS-Model.num_channels;
}
static const char *tx15_mixer_list_summary(guiObject_t *obj,const void *data){
    (void)obj;unsigned ch=(uintptr_t)data;
    char source[48]="None";
    struct Mixer *mix=MIXER_GetAllMixers();
    for(unsigned i=0;i<NUM_MIXERS;i++)if(mix[i].src && mix[i].dest==ch){
        INPUT_SourceName(source,mix[i].src);break;
    }
    snprintf(tempstring,sizeof(tempstring),"%s / %s",MIXER_TemplateName(MIXER_GetTemplate(ch)),source);
    return tempstring;
}
static const char *tx15_mixer_list_caption(guiObject_t *obj,const void *data){
    (void)obj;
    switch((uintptr_t)data){case 10:return "Back";case 11:return "Previous";case 12:return "Next";
        case 13:return "Monitor";default:return "Order";}
}
static void tx15_mixer_list_action(guiObject_t *obj,s8 press,const void *data){
    (void)obj;if(press!=-1)return;
    switch((uintptr_t)data){
    case 10:PAGE_Pop();break;
    case 11:PAGE_MixerTouchScroll(-1);break;
    case 12:PAGE_MixerTouchScroll(1);break;
    case 13:show_chantest_cb(NULL,NULL);break;
    case 14:reorder_cb(NULL,NULL);break;
    }
}
static void tx15_mixer_list_name(guiObject_t *obj,s8 press,const void *data){
    if(press!=-1)return;
    unsigned ch=(uintptr_t)data;
    if(ch<NUM_OUT_CHANNELS)limitselect_cb(obj,data);
    else if(!_is_virt_cyclic(ch))virtname_cb(obj,data);
}
static void tx15_mixer_list_template(guiObject_t *obj,s8 press,const void *data){
    if(press==-1)templateselect_cb(obj,data);
}
static int tx15_mixer_list_row(int row,int relative,int y,void *data){
    (void)data;
    unsigned ch=tx15_mixer_list_channel(row);
    struct LabelDesc font=tx15_card_font(1);
    font.style=LABEL_MIX_ACTION;
    int named=ch<NUM_OUT_CHANNELS || !_is_virt_cyclic(ch);
    GUI_CreateLabelBox(&gui->name[relative].lbl,12,y,88,40,&font,MIXPAGE_ChanNameProtoCB,
        named?tx15_mixer_list_name:NULL,(const void *)(uintptr_t)ch);
    GUI_CreateLabelBox(&tx15_mixer_list_edit[relative],108,y,352,40,&font,tx15_mixer_list_summary,
        tx15_mixer_list_template,(const void *)(uintptr_t)ch);
    return named?2:1;
}
static void tx15_mixer_list_title(void){
    memset(gui,0,sizeof(*gui));PAGE_ShowHeader("Mixer");
    struct LabelDesc font=tx15_card_font(1);
    for(unsigned i=0;i<2;i++)GUI_CreateLabelBox(&tx15_mixer_list_tools[i],256+i*112,0,100,40,&font,
        tx15_mixer_list_caption,tx15_mixer_list_action,(const void *)(uintptr_t)(13+i));
    for(unsigned i=0;i<3;i++)GUI_CreateLabelBox(&tx15_mixer_list_footer[i],12+i*156,280,144,40,&font,
        tx15_mixer_list_caption,tx15_mixer_list_action,(const void *)(uintptr_t)(10+i));
}
static void tx15_mixer_list_page(void){
    GUI_CreateScrollable(&gui->scrollable,0,44,480,220,44,Model.num_channels+NUM_VIRT_CHANNELS,
        tx15_mixer_list_row,NULL,NULL,NULL);
    PAGE_SetScrollable(&gui->scrollable,&current_selected);
}
int PAGE_MixerTouchRow(void){return GUI_ScrollableCurrentRow(&gui->scrollable);}
int PAGE_MixerTouchHit(unsigned x,unsigned y){
    if(x>=480 || y>=320)return -1;
    if(y<40){if(x>=256 && x<356)return 13;if(x>=368 && x<468)return 14;}
    if(y>=44 && y<264){
        unsigned r=(y-44)/44;
        if((y-44)%44>=40 || (unsigned)PAGE_MixerTouchRow()+r>=gui->scrollable.item_count)return -1;
        if(x>=12 && x<100){
            unsigned ch=tx15_mixer_list_channel(PAGE_MixerTouchRow()+r);
            if(ch>=NUM_OUT_CHANNELS && _is_virt_cyclic(ch))return -1;
            return r*2;
        }
        if(x>=108 && x<460)return r*2+1;
    }
    if(y>=280 && x>=12){unsigned c=(x-12)/156;if(c<3 && (x-12)%156<144)return 10+c;}
    return -1;
}
void PAGE_MixerTouchScroll(int direction){
    int row=PAGE_MixerTouchRow()+(direction>0?5:-5);
    int last=gui->scrollable.item_count>5?gui->scrollable.item_count-5:0;
    if(row<0)row=0;if(row>last)row=last;
    if(row==PAGE_MixerTouchRow())return;
    GUI_SetSelected(GUI_ShowScrollableRowOffset(&gui->scrollable,row<<8));
}
void PAGE_MixerTouchTap(unsigned x,unsigned y){
    int hit=PAGE_MixerTouchHit(x,y);if(hit<0)return;
    if(hit>=10){tx15_mixer_list_action(NULL,-1,(const void *)(uintptr_t)hit);return;}
    unsigned r=hit/2,ch=tx15_mixer_list_channel(PAGE_MixerTouchRow()+r);
    guiObject_t *obj=hit&1?(guiObject_t *)&tx15_mixer_list_edit[r]:(guiObject_t *)&gui->name[r].lbl;
    GUI_SetSelected(obj);
    if(hit&1)templateselect_cb(obj,(const void *)(uintptr_t)ch);
    else tx15_mixer_list_name(obj,-1,(const void *)(uintptr_t)ch);
}

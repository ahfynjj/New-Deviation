/* A single physical control per widget, with bounded dirty-panel updates.
 * Uses Deviation GUI objects and drawing primitives; GPL-3.0-or-later. */
#include "common.h"
#include "gui/gui.h"
#include "config/display.h"
#include "config/model.h"
#include "input_dashboard.h"
#include "../../../../../hardware/tx15/board/controls.h"
#include "../../../../../hardware/tx15/board/analog.h"
#include "../../../../../hardware/tx15/board/inputs.h"
enum {BG=0x10c4,CARD=0x2126,EDGE=0x39e9,TEXT=0xef9d,MUTED=0x9cd3,
      ACCENT=0x05da,PRESSED=0xfdc0,INVALID=0xfaaa};
struct panel {u16 x,y,w,h;};
static const struct panel panels[TX15_DASHBOARD_TILES]={
    {8,38,72,44},{86,38,72,44},{164,38,72,44},
    {242,38,72,44},{320,38,72,44},{398,38,72,44},
    {8,90,156,134},{172,90,156,134},
    {336,90,136,63},{336,161,136,63},
    {8,232,111,44},{126,232,111,44},{244,232,111,44},{362,232,110,44},
    {8,284,464,24}
};
static struct tx15_dashboard_state shown;
static guiRect_t widgets[TX15_DASHBOARD_TILES],background,diagnostic;
static unsigned details,last_refresh;

void tx15_dashboard_collect(struct tx15_dashboard_state *s) {
    memset(s,0,sizeof(*s));
    s->analog_valid=tx15_analog_status==4;
    for(unsigned i=0;i<6;i++) {
        int pct=RANGE_TO_PCT(CHAN_ReadInput(i+1));
        s->percent[i]=pct<-100?-100:pct>100?100:pct;
        s->position[i]=(tx15_controls.valid&(1u<<i)) && tx15_controls.position[i]<3
            ?tx15_controls.position[i]:-1;
    }
    s->selected=(tx15_controls.valid&(1u<<6)) && tx15_controls.position[6]<6
        ?tx15_controls.position[6]:-1;
    s->buttons=tx15_controls.buttons;
    s->trim_pressed=(tx15_inputs_state()>>4)&255;
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<NUM_TRIMS;j++) {
        const struct Trim *t=&Model.trims[j];
        if(t->src && (t->pos==2+2*i || t->neg==1+2*i || t->pos==1+2*i || t->neg==2+2*i)) {
            s->trim_bound|=1u<<i;s->trim[i]=MIXER_GetTrimValue(j)/10;break;
        }
    }
    s->raw[0]=tx15_controls_raw[0];s->raw[1]=tx15_controls_raw[1];
}

static void text(unsigned x,unsigned y,const char *s,unsigned color,int tiny) {
    LCD_SetFont(tiny?TINY_FONT.font:DEFAULT_FONT.font);
    LCD_SetFontColor(color);LCD_PrintStringXY(x,y,s);
}
static void signed_percent(char *out,unsigned n,int value) {
    unsigned magnitude=value<0?-value:value;
    snprintf(out,n,"%c%u.%u",value<0?'-':'+',magnitude/10,magnitude%10);
}
void tx15_dashboard_draw(unsigned tile,const struct tx15_dashboard_state *s) {
    if(tile>=TX15_DASHBOARD_TILES)return;
    const struct panel *p=&panels[tile];char buf[32];
    LCD_FillRect(p->x,p->y,p->w,p->h,CARD);
    if(tile<6) {
        snprintf(buf,sizeof(buf),"S%c",'A'+tile);text(p->x+5,p->y+4,buf,TEXT,0);
        for(unsigned k=0;k<3;k++) {
            unsigned color=s->position[tile]==(int)k?ACCENT:EDGE;
            LCD_FillRect(p->x+5+k*22,p->y+27,18,10,color);
        }
        if(s->position[tile]<0)text(p->x+48,p->y+4,"--",INVALID,0);
        else {snprintf(buf,sizeof(buf),"%d",s->position[tile]);text(p->x+52,p->y+4,buf,ACCENT,0);}
    } else if(tile<8) {
        int left=tile==6;unsigned hx=left?3:0,vy=left?1:2;
        text(p->x+7,p->y+5,left?"LEFT STICK":"RIGHT STICK",TEXT,0);
        unsigned gx=p->x+32,gy=p->y+29,gw=92,gh=76;
        LCD_FillRect(gx,gy,gw,gh,BG);LCD_DrawRect(gx,gy,gw,gh,EDGE);
        LCD_DrawFastHLine(gx,gy+gh/2,gw,EDGE);LCD_DrawFastVLine(gx+gw/2,gy,gh,EDGE);
        if(s->analog_valid) {
            unsigned x=gx+4+(s->percent[hx]+100)*(gw-9)/200;
            unsigned y=gy+4+(100-s->percent[vy])*(gh-9)/200;
            LCD_FillRect(x-3,y-3,7,7,ACCENT);
            snprintf(buf,sizeof(buf),"H:%d V:%d",s->percent[hx],s->percent[vy]);
        } else strcpy(buf,"H:-- V:--");
        text(p->x+6,p->y+114,buf,s->analog_valid?TEXT:INVALID,0);
    } else if(tile<10) {
        unsigned i=tile-8;snprintf(buf,sizeof(buf),"S%u",i+1);text(p->x+8,p->y+6,buf,TEXT,0);
        if(s->analog_valid)snprintf(buf,sizeof(buf),"%d%%",s->percent[4+i]);else strcpy(buf,"--");
        text(p->x+51,p->y+6,buf,s->analog_valid?ACCENT:INVALID,0);
        LCD_FillRect(p->x+8,p->y+36,p->w-16,12,BG);
        if(s->analog_valid) {
            unsigned width=(s->percent[4+i]+100)*(p->w-16)/200;
            if(width)LCD_FillRect(p->x+8,p->y+36,width,12,ACCENT);
        }
        LCD_DrawFastVLine(p->x+p->w/2,p->y+34,16,MUTED);
    } else if(tile<14) {
        unsigned i=tile-10;static const char *const names[]={"LV","RV","LH","RH"};
        text(p->x+5,p->y+4,names[i],MUTED,0);
        if(s->trim_bound&(1u<<i))signed_percent(buf,sizeof(buf),s->trim[i]);else strcpy(buf,"--");
        text(p->x+35,p->y+4,buf,TEXT,0);
        for(unsigned k=0;k<2;k++) {
            unsigned color=(s->trim_pressed&(1u<<(2*i+k)))?PRESSED:EDGE;
            LCD_FillRect(p->x+5+k*53,p->y+27,48,12,color);
            text(p->x+25+k*53,p->y+29,k?"+":"-",TEXT,1);
        }
    } else {
        text(p->x+5,p->y+5,"KEYS",MUTED,0);
        for(unsigned i=0;i<6;i++) {
            unsigned x=p->x+70+i*63;
            LCD_FillRect(x,p->y+2,54,20,(s->buttons&(1u<<i))?PRESSED:BG);
            if(s->selected==(int)i)LCD_DrawRect(x,p->y+2,54,20,ACCENT);
            snprintf(buf,sizeof(buf),"%u",i+1);text(x+22,p->y+4,buf,TEXT,0);
        }
    }
}

static void draw_tile(guiObject_t *obj,const void *data) {
    (void)obj;tx15_dashboard_draw((unsigned)(long)data,&shown);
}
static void draw_background(guiObject_t *obj,const void *data) {
    (void)obj;(void)data;
    text(10,312,"ENTER: DIAGNOSTICS     EXIT: BACK",MUTED,1);
}
static void draw_diagnostic(guiObject_t *obj,const void *data) {
    (void)obj;(void)data;char buf[80];
    text(16,48,"MON1  INPUT DIAGNOSTICS",TEXT,0);
    snprintf(buf,sizeof(buf),"74:%04X  75:%04X",shown.raw[0],shown.raw[1]);text(16,82,buf,ACCENT,0);
    snprintf(buf,sizeof(buf),"Trim keys: %02X   Front keys: %02X",shown.trim_pressed,shown.buttons);
    text(16,110,buf,TEXT,0);
    for(unsigned i=0;i<6;i++) {
        if(shown.position[i]<0)snprintf(buf,sizeof(buf),"S%c: --",'A'+i);
        else snprintf(buf,sizeof(buf),"S%c: %d / 3",'A'+i,shown.position[i]);
        text(16+(i%3)*150,151+(i/3)*31,buf,TEXT,0);
    }
    text(16,236,"Raw contacts; no pin mapping changes.",MUTED,0);
    text(16,270,"Trim values show tenths of a percent.",MUTED,0);
    text(10,312,"ENTER: CONTROLS        EXIT: BACK",MUTED,1);
}
static unsigned dashboard_button(u32 buttons,unsigned flags,void *data) {
    (void)buttons;(void)data;
    if(flags&BUTTON_PRESS) {
        details=!details;
        for(unsigned i=0;i<TX15_DASHBOARD_TILES;i++)GUI_SetHidden((guiObject_t *)&widgets[i],details);
        GUI_SetHidden((guiObject_t *)&diagnostic,!details);
        GUI_Redraw((guiObject_t *)&background);
    }
    return 1;
}
void tx15_input_dashboard_init(buttonAction_t *action) {
    struct LabelDesc desc={0};desc.fill_color=desc.outline_color=BG;
    details=0;last_refresh=CLOCK_getms();tx15_dashboard_collect(&shown);
    GUI_CreateRectCB(&background,0,32,LCD_WIDTH,LCD_HEIGHT-32,&desc,draw_background,NULL);
    for(unsigned i=0;i<TX15_DASHBOARD_TILES;i++) {
        const struct panel *p=&panels[i];
        GUI_CreateRectCB(&widgets[i],p->x,p->y,p->w,p->h,&desc,draw_tile,(void *)(long)i);
    }
    GUI_CreateRectCB(&diagnostic,0,32,LCD_WIDTH,LCD_HEIGHT-32,&desc,draw_diagnostic,NULL);
    GUI_SetHidden((guiObject_t *)&diagnostic,1);
    /* ENTER belongs to this page, including holds; custom trim bindings resume
     * after PAGE_ChantestExit unregisters this scoped action. */
    BUTTON_RegisterCallback(action,CHAN_ButtonMask(BUT_ENTER),
        BUTTON_PRESS|BUTTON_RELEASE|BUTTON_LONGPRESS|BUTTON_PRIORITY,dashboard_button,NULL);
}
void tx15_input_dashboard_event(void) {
    unsigned now=CLOCK_getms();if((u32)(now-last_refresh)<50)return;last_refresh=now;
    struct tx15_dashboard_state next;tx15_dashboard_collect(&next);
    if(details) {
        if(memcmp(&shown,&next,sizeof(next)))GUI_Redraw((guiObject_t *)&diagnostic);
    } else for(unsigned i=0;i<TX15_DASHBOARD_TILES;i++) {
        int changed;
        if(i<6)changed=shown.position[i]!=next.position[i];
        else if(i<8) {
            unsigned h=i==6?3:0,v=i==6?1:2;
            changed=shown.analog_valid!=next.analog_valid || shown.percent[h]!=next.percent[h] || shown.percent[v]!=next.percent[v];
        } else if(i<10)changed=shown.analog_valid!=next.analog_valid || shown.percent[i-4]!=next.percent[i-4];
        else if(i<14) {
            unsigned t=i-10,mask=3u<<(2*t);
            changed=shown.trim[t]!=next.trim[t] || ((shown.trim_bound^next.trim_bound)&(1u<<t)) || ((shown.trim_pressed^next.trim_pressed)&mask);
        } else changed=shown.buttons!=next.buttons || shown.selected!=next.selected;
        if(changed)GUI_Redraw((guiObject_t *)&widgets[i]);
    }
    shown=next;
}

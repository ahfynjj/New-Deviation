/* Dispatch only adapted native menus, never legacy parameter hit boxes.
 * Called by GUI loop only, not hardware service/watchdog callbacks. */
#ifdef TX15_MENU_TOUCH
#include "common.h"
#include "pages.h"
#include "menu_touch.h"
#ifdef TX15_CARD_UI
#include "card_ui.h"
#endif
#include "../../../../../hardware/tx15/board/touch.h"
static unsigned owned,mapped,active,moved;
static int owner,first_row,hit;
static uint32_t activated,down_ms;
static unsigned down_x,down_y;
static int eligible(int page){
#ifdef TX15_CARD_UI
    if(page==PAGEID_MIXTEMPL)return PAGE_MixCardActive();
#endif
    return page==PAGEID_MENU || page==PAGEID_MODELMNU || page==PAGEID_TXMENU;
}
static int position(void){
#ifdef TX15_CARD_UI
    if(PAGE_GetID()==PAGEID_MIXTEMPL)return PAGE_MixCardGeneration();
#endif
    return PAGE_MenuTouchRow();
}
static int target(unsigned x,unsigned y){
#ifdef TX15_CARD_UI
    if(PAGE_GetID()==PAGEID_MIXTEMPL)return PAGE_MixCardHit(x,y);
#endif
    return tx15_menu_touch_hit(x,y);
}
void tx15_menu_touch_suspend(void){
    active=0;
    if(owned){
        struct tx15_touch_event event;
        tx15_touch_stop(CLOCK_getms());
        while(tx15_touch_take(&event)){}
    }
    owned=mapped=0;
}
void tx15_menu_touch_poll(void){
    if(GUI_IsModal()){tx15_menu_touch_suspend();return;}
    int page=PAGE_GetID();
    if(owned && owner!=page)tx15_menu_touch_suspend();
    if(!eligible(page)){if(owned)tx15_menu_touch_suspend();return;} /* Diagnostic owns its own queue. */
    uint32_t now=CLOCK_getms();
    if(!owned){
        owned=1;owner=page;activated=now;tx15_touch_start(now);
        tx15_touch_require_release(now);
    }
    if(tx15_touch_report.state!=TX15_TOUCH_READY){active=0;return;}
    if(!mapped){tx15_touch_set_map(0,now);mapped=1;}
    struct tx15_touch_event event;
    while(tx15_touch_take(&event)){
        if(event.kind==TX15_TOUCH_CANCEL){active=0;continue;}
        if(event.kind==TX15_TOUCH_DOWN){
            active=(uint32_t)(event.ms-activated)>=100u;
            down_ms=event.ms;down_x=event.x;down_y=event.y;moved=0;
            first_row=position();hit=target(down_x,down_y);
            continue;
        }
        if(!active)continue;
        int dx=(int)event.x-(int)down_x,dy=(int)event.y-(int)down_y;
        unsigned ax=dx<0?-dx:dx,ay=dy<0?-dy:dy;
        if(ax>=12 || ay>=12)moved=1;
        if(position()!=first_row){active=0;continue;}
        if(event.kind!=TX15_TOUCH_UP)continue;
        active=0; /* callbacks may change page and stop this sampler */
        if((uint32_t)(event.ms-down_ms)>500u)continue;
        if(!moved && hit>=0 && hit==target(event.x,event.y)){
#ifdef TX15_CARD_UI
            if(page==PAGEID_MIXTEMPL){PAGE_MixCardTap(event.x,event.y);return;}
#endif
            PAGE_MenuTouchTap(event.x,event.y);return;
        }
        if(hit>=0 && hit<6 && ay>=24 && ay>ax){
#ifdef TX15_CARD_UI
            if(page==PAGEID_MIXTEMPL)return;
#endif
            PAGE_MenuTouchScroll(dy<0?1:-1);return;
        }
    }
}
#endif

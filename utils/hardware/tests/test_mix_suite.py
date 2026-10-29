import unittest
import test_card_ui
import test_switch_upgrade as helper
import test_mix_cards

class MixSuiteTests(unittest.TestCase):
    run_c=helper.SwitchUpgradeTests.run_c
    def test_child_page_router_cancels_rebuild_and_duplicate_release(self):
        class Adapted(test_card_ui.CardUITests):
            def run_c(case,code,sources):
                code=code.replace('int tx15_mix_touch_active(void){return 0;}','int tx15_mix_touch_active(void){return page==PAGEID_EDITCURVE;}')
                code=code.replace('int tx15_mix_touch_generation(void){return 0;}','int tx15_mix_touch_generation(void){return generation;}')
                code=code.replace('(void)x;(void)y;return -1;','return x<300 && y>=44 && y<84?0:-1;')
                code=code.replace('(void)x;(void)y;assert(0);','(void)x;(void)y;taps++;')
                code=code.replace('return 0;\n}',r'''
 page=PAGEID_EDITCURVE;ms=900;tx15_menu_touch_poll();tx15_touch_report.state=TX15_TOUCH_READY;
 event(TX15_TOUCH_DOWN,60,1020);event(TX15_TOUCH_UP,60,1040);assert(taps==3);
 event(TX15_TOUCH_UP,60,1050);assert(taps==3);
 event(TX15_TOUCH_DOWN,60,1100);generation++;event(TX15_TOUCH_UP,60,1120);assert(taps==3);
 return 0;
}''')
                return helper.SwitchUpgradeTests.run_c(case,code,sources)
        Adapted('test_mix_router_cancels_rebuild_swipe_and_legacy_template').test_mix_router_cancels_rebuild_swipe_and_legacy_template()

    def test_expo_rate_off_and_linked_visibility(self):
        class Adapted(test_mix_cards.MixCardsTests):
            def run_c(case,code,sources):
                code=code.replace('mp->cur_template=MIXERTEMPLATE_EXPO_DR;assert(PAGE_MixCardActive());',r'''
 mp->cur_template=MIXERTEMPLATE_EXPO_DR;mp->firstObj=NULL;mp->link_curves=0;
 tx15_mix_expo_rate=0;tx15_mix_expo_cards();
 assert(gui2->src.header.box.width==292);
 assert(!OBJ_IS_HIDDEN((guiObject_t *)&gui2->curvehi));
 tx15_mix_expo_rate=1;mp->mixer[1].sw=0;tx15_mix_expo_visibility();
 assert(!OBJ_IS_HIDDEN((guiObject_t *)&gui2->sw1));
 assert(OBJ_IS_HIDDEN((guiObject_t *)&gui2->curve[0]));
 assert(OBJ_IS_HIDDEN((guiObject_t *)&tx15_mix_card_curve_edit));
 mp->mixer[1].sw=INP_SWA1;tx15_mix_expo_visibility();
 assert(!OBJ_IS_HIDDEN((guiObject_t *)&gui2->curve[0]));
 assert(!OBJ_IS_HIDDEN((guiObject_t *)&tx15_mix_card_curve_edit));
 mp->link_curves=1;tx15_mix_expo_visibility();
 assert(OBJ_IS_HIDDEN((guiObject_t *)&tx15_mix_card_curve_edit));
 assert(OBJ_IS_HIDDEN((guiObject_t *)&gui2->curve[0]));
 assert(!OBJ_IS_HIDDEN((guiObject_t *)&gui2->scale[0]));
 assert(OBJ_IS_HIDDEN((guiObject_t *)&gui2->curvehi));
''')
                return helper.SwitchUpgradeTests.run_c(case,code,sources)
        Adapted('test_dense_geometry_more_page_and_touch_callbacks').test_dense_geometry_more_page_and_touch_callbacks()

    def test_reorder_remove_preserves_buffer_guard(self):
        self.run_c(r'''
#include <assert.h>
#include "common.h"
#include "pages.h"
struct _gui_objs gui_objs;
void _GUI_Redraw(guiObject_t *o){(void)o;}
#include "src/pages/common/_reorder_list.c"
int main(void){
 u8 list[]={1,2,0xa5};rl.list=list;rl.count=rl.max=2;rl.selected=0;
 press_button_cb(NULL,(void *)REMOVE);
 assert(rl.count==1 && list[0]==2 && list[1]==0 && list[2]==0xa5);
 return 0;
}''',[])

    def test_target_registry_page_hidden_disabled_and_graph_edges(self):
        class Adapted(test_card_ui.CardUITests):
            def run_c(case,code,sources):
                code=code.replace('struct display_settings Display;',r'''
struct display_settings Display;
static int page=PAGEID_EDITCURVE,steps,touched,gx,gy;
int PAGE_GetID(void){return page;}
void tx15_mix_field_touch(guiObject_t *o){(void)o;touched++;}
void tx15_mix_field_step(guiObject_t *o,int d){(void)o;steps+=d;}
void tx15_mix_switch_forget(guiObject_t *o){(void)o;}
void GUI_SetSelected(guiObject_t *o){(void)o;}
void _GUI_Redraw(guiObject_t *o){(void)o;}
static u8 graph_touch(s16 x,s16 y,void *d){(void)d;gx=x;gy=y;return 1;}
''')
                code=code.replace('guiLabel_t label={0};',r'''
 tx15_mix_touch_begin(PAGEID_EDITCURVE);
 field.header.flags=1;field.enable=1;tx15_mix_touch_add((guiObject_t *)&field);
 assert(tx15_mix_touch_active());int gen=tx15_mix_touch_generation();
 tx15_mix_touch_tap(200,60);assert(touched==1);
 field.enable|=TX15_SWITCH_EDITING;
 tx15_mix_touch_tap(110,60);tx15_mix_touch_tap(300,60);assert(steps==0);
 field.header.flags|=2;assert(tx15_mix_touch_hit(200,60)==-1);
 field.header.flags=1;field.enable=0;assert(tx15_mix_touch_hit(200,60)==-1);
 guiXYGraph_t graph={0};graph.header.Type=XYGraph;graph.header.flags=1;
 graph.header.box=(struct guiBox){320,90,140,140};graph.min_x=graph.min_y=-10000;
 graph.max_x=graph.max_y=10000;graph.touch_cb=graph_touch;
 tx15_mix_touch_add((guiObject_t *)&graph);tx15_mix_touch_tap(459,229);
 assert(gx==10000 && gy==-10000);
 tx15_mix_touch_changed();assert(tx15_mix_touch_generation()!=gen);
 guiLabel_t extra[45]={0};for(unsigned i=0;i<45;i++){extra[i].header.flags=1;extra[i].header.Type=Label;tx15_mix_touch_add((guiObject_t *)&extra[i]);}
 assert(mix_count==40);
 page=PAGEID_MAIN;assert(!tx15_mix_touch_active());
 return 0;
 guiLabel_t label={0};''')
                return helper.SwitchUpgradeTests.run_c(case,code,sources)
        Adapted('test_actual_plate_draw_and_scoped_palette_restore').test_actual_plate_draw_and_scoped_palette_restore()

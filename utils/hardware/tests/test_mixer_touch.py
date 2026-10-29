import unittest
import test_switch_capture
import test_switch_upgrade as helper
import test_mix_cards

class MixerTouchTests(unittest.TestCase):
    def test_simple_and_complex_touch_step_zones(self):
        class Adapted(test_mix_cards.MixCardsTests):
            def run_c(case,code,sources):
                code=code.replace('static unsigned fields,labels,graphs,sources,values,touches,saves,changes;',
                    'static unsigned fields,labels,graphs,sources,values,touches,saves,changes;\nstatic int steps;')
                code=code.replace('void tx15_mix_field_step(guiObject_t *o,int d){(void)o;(void)d;}',
                    'void tx15_mix_field_step(guiObject_t *o,int d){assert(o==selected);steps+=d;}')
                code=code.replace('mp->cur_template=MIXERTEMPLATE_EXPO_DR;assert(PAGE_MixCardActive());',r'''
 tx15_mix_card_more_cb(NULL,-1,NULL); /* back to Basic */
 selected=(guiObject_t *)&gui3->scale;gui3->scale.enable=1|TX15_SWITCH_EDITING;
 assert(PAGE_MixCardHit(24,190)==106 && PAGE_MixCardHit(300,190)==107);
 assert(PAGE_MixCardHit(210,190)==3);
 PAGE_MixCardTap(300,190);assert(steps==1);
 PAGE_MixCardTap(24,190);assert(steps==0);
 mp->cur_template=MIXERTEMPLATE_SIMPLE;mp->firstObj=NULL;
 tx15_mix_simple_cards();assert(PAGE_MixCardActive());
 assert(PAGE_MixCardHit(30,55)==0 && PAGE_MixCardHit(30,235)==-1);
 selected=(guiObject_t *)&gui1->offset;gui1->offset.enable=1|TX15_SWITCH_EDITING;
 assert(PAGE_MixCardHit(300,190)==107);PAGE_MixCardTap(300,190);assert(steps==1);
 mp->cur_template=MIXERTEMPLATE_NONE;tx15_mix_none_cards();assert(PAGE_MixCardActive());
 assert(PAGE_MixCardHit(200,100)==-1 && PAGE_MixCardHit(200,20)==6);
 assert(PAGE_MixCardHit(200,300)==8); /* template footer */
 mp->cur_template=MIXERTEMPLATE_EXPO_DR;assert(PAGE_MixCardActive());
''')
                return helper.SwitchUpgradeTests.run_c(case,code,sources)
        Adapted('test_dense_geometry_more_page_and_touch_callbacks').test_dense_geometry_more_page_and_touch_callbacks()

    def test_touch_step_only_while_armed_and_focus_matches(self):
        class Adapted(test_switch_capture.SwitchCaptureTests):
            def run_c(case,code,sources):
                code=code.replace('int PAGE_GetID(void){return page;}',
                    'int PAGE_GetID(void){return page;}\nvoid GUI_SetSelected(guiObject_t *o){selected=o;}')
                code=code.replace('assert(redraws>0);return 0;',r'''
 page=PAGEID_MIXTEMPL;selected=(guiObject_t *)&field;
 field.enable=1;field.InputValueCB=NULL;field.SelectCB=NULL;tx15_mix_value_register(&field);
 u8 old=field_value;tx15_mix_field_step(selected,1);assert(field_value==old);
 tx15_mix_field_touch(selected);assert(field.enable&TX15_SWITCH_EDITING);
 tx15_mix_field_step(selected,1);assert(field_value!=old);
 old=field_value;selected=(guiObject_t *)&source;
 tx15_mix_field_step((guiObject_t *)&field,1);assert(field_value==old);
 tx15_mix_switch_poll();assert(!(field.enable&TX15_SWITCH_EDITING));
 assert(redraws>0);return 0;
''')
                return helper.SwitchUpgradeTests.run_c(case,code,sources)
        Adapted('test_real_button_flow_arms_confirms_cancels_and_preserves_manual_inversion').test_real_button_flow_arms_confirms_cancels_and_preserves_manual_inversion()

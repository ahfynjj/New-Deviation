"""UI05 actual renderer and native Complex geometry, no device/emulator."""
import unittest
import test_card_ui
import test_mix_cards
import test_switch_upgrade as helper


class ComplexUITests(unittest.TestCase):
    def test_row_value_caption_edit_and_long_name_bounds(self):
        class Adapted(test_card_ui.CardUITests):
            def run_c(case, code, sources):
                code = code.replace('static unsigned font,prints,clears;',
                    'static unsigned font,prints,clears; static char textlog[16][96]; static unsigned left[16],right[16];')
                code = code.replace('prints++;}',
                    'assert(prints<16);snprintf(textlog[prints],96,"%s",s);left[prints]=x;right[prints]=x+w;prints++;}')
                code = code.replace('guiLabel_t label={0};', r'''
 tx15_card_mix_rows_reset();field.header.box=(struct guiBox){12,44,292,40};
 tx15_card_mix_row(&field,"Source");
 field.enable=1;prints=0;
 GUI_DrawTextSelect((guiObject_t *)&field);
 assert(prints==2 && !strcmp(textlog[0],"Source") && !strcmp(textlog[1],"100%"));
 assert(left[0]>=24 && right[0]<left[1] && right[1]<=268);
 field.enable|=TX15_SWITCH_EDITING;prints=0;
 GUI_DrawTextSelect((guiObject_t *)&field);
 assert(prints==3 && !strcmp(textlog[1],"EDIT"));
 assert(right[1]<=left[2] && right[2]<=264);
 prints=0;tx15_card_draw_plate((guiObject_t *)&field,
   "A_source_name_that_is_far_too_long_for_this_field",&field.desc);
 assert(prints==3 && right[2]<=264); /* bounded visible truncation */
 return 0;
 guiLabel_t label={0};
''')
                return helper.SwitchUpgradeTests.run_c(case, code, sources)
        Adapted('test_actual_plate_draw_and_scoped_palette_restore').test_actual_plate_draw_and_scoped_palette_restore()

    def test_complex_full_rows_and_curve_panel_hit(self):
        class Adapted(test_mix_cards.MixCardsTests):
            def run_c(case, code, sources):
                code = code.replace('(void)p;return x;','(void)p;return x*2;')
                code = code.replace('assert(fields==8', r'''
 assert(tx15_mix_card_plot_cb(CHAN_MAX_VALUE,NULL)==CHAN_MAX_VALUE);
 assert(tx15_mix_card_plot_cb(CHAN_MIN_VALUE,NULL)==CHAN_MIN_VALUE);
 assert(gui3->src.header.box.x==12 && gui3->src.header.box.width==292);
 assert(OBJ_IS_HIDDEN((guiObject_t *)&gui3->srclbl));
 assert(PAGE_MixCardHit(400,55)==5 && PAGE_MixCardHit(400,190)==-1);
 assert(tx15_mix_card_output.header.box.y==184);
 assert(fields==8''')
                return helper.SwitchUpgradeTests.run_c(case, code, sources)
        Adapted('test_dense_geometry_more_page_and_touch_callbacks').test_dense_geometry_more_page_and_touch_callbacks()

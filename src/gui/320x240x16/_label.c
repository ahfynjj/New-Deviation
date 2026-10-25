/*
 This project is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Deviation is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Deviation.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifdef TX15_STATUS_REGIONS
#include "target/tx/radiomaster/tx15/display_region.h"
/* Legacy labels may intentionally overflow their box. Compose only when all
 * text fits, so the bounded scratch region cannot clip existing menu content. */
static int label_region_fits(u16 x, u16 y, u16 w, u16 h, u16 text_w,
        u16 text_h, u16 offset, const struct LabelDesc *desc, u8 selected)
{
    int inner_x=x, inner_w=w, text_x, text_y;
    if (h < text_h || x + w > 480 || y + h > 320)
        return 0;
    if (desc->style != LABEL_LISTBOX && desc->fill_color != desc->outline_color) {
        if (w < 4)
            return 0;
        inner_x += 2;
        inner_w -= 4;
    }
    if (desc->align == ALIGN_RIGHT)
        text_x = inner_x + inner_w - text_w - (selected ? Display.select_width : 0);
    else if (inner_w > text_w && desc->align != ALIGN_LEFT)
        text_x = inner_x + 1 + (inner_w - text_w + 1) / 2;
    else
        text_x = inner_x + 1 + (selected ? Display.select_width : 0);
    text_y = y + offset + (h - text_h + 1) / 2;
    return text_x >= x && text_y >= y
        && text_x + text_w <= x + w && text_y + text_h <= y + h;
}
#endif
void GUI_DrawLabelHelper(u16 obj_x, u16 obj_y, u16 obj_w, u16 obj_h, const char *str,
        const struct LabelDesc *desc, u8 is_selected)
{
    u16 txt_w, txt_h;
    u16 txt_x, txt_y;
    // This is used to align text vertically
    u16 offset = (desc->font==NARROW_FONT.font) ? 1 : 0;
    LCD_SetFont(desc->font);
    LCD_GetStringDimensions((const u8 *)str, &txt_w, &txt_h); txt_w++;
    if (obj_w == 0)
        obj_w = txt_w;
    if (obj_h == 0)
        obj_h = txt_h;
#ifdef TX15_STATUS_REGIONS
    int region = label_region_fits(obj_x, obj_y, obj_w, obj_h,
            txt_w, txt_h, offset, desc, is_selected)
        && tx15_region_begin(obj_x, obj_y, obj_w, obj_h);
#endif
    if (desc->style == LABEL_LISTBOX) {
        LCD_FillRect(obj_x, obj_y, obj_w, obj_h, is_selected ? Display.listbox.bg_select : Display.listbox.bg_color);
    } else if (desc->style == LABEL_FILL) {
        LCD_FillRect(obj_x, obj_y, obj_w, obj_h, desc->fill_color);
    } else {
        GUI_DrawBackground(obj_x, obj_y, obj_w, obj_h);
    }
    if (desc->style != LABEL_LISTBOX && desc->fill_color != desc->outline_color) {
        LCD_DrawRect(obj_x, obj_y, obj_w, obj_h, desc->outline_color);
        obj_x+=2; obj_w-=4;
    }

    if (desc->align == ALIGN_RIGHT) {
        txt_x = obj_x + obj_w - txt_w - (is_selected ? Display.select_width : 0);
    } else if (obj_w > txt_w && !(desc->align == ALIGN_LEFT)) {
        txt_x = obj_x + 1 + (obj_w - txt_w + 1) / 2;
    } else {
        txt_x = obj_x + 1 + (is_selected ? Display.select_width : 0);
    }
    txt_y = obj_y + offset + (obj_h - txt_h + 1) / 2;

    if (desc->style == LABEL_UNDERLINE) {
        LCD_DrawFastHLine(obj_x, txt_y + txt_h - 1, obj_w, desc->font_color);
    }

    if (desc->style == LABEL_LISTBOX) {
        LCD_SetFontColor(is_selected ? Display.listbox.fg_select : Display.listbox.fg_color);
    } else {
        if (desc->style != LABEL_FILL && is_selected) {
            LCD_SetFontColor(~desc->font_color);
        } else {
            LCD_SetFontColor(desc->font_color);
        }
    }
    LCD_PrintStringXY(txt_x, txt_y, str);
#ifdef TX15_STATUS_REGIONS
    if(region)tx15_region_end();
#endif
}


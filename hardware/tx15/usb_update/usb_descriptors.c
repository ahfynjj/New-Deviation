/* Experimental USB identity; GPL-3.0-or-later. */
#include "tusb.h"
#include "usb_hw.h"
#ifndef TX15_USB_VID
#define TX15_USB_VID 0xcafe
#endif
#ifndef TX15_USB_PID
#define TX15_USB_PID 0x4015
#endif
static const tusb_desc_device_t device={
    .bLength=sizeof(tusb_desc_device_t),.bDescriptorType=TUSB_DESC_DEVICE,.bcdUSB=0x0200,
    .bDeviceClass=TUSB_CLASS_MISC,.bDeviceSubClass=MISC_SUBCLASS_COMMON,.bDeviceProtocol=MISC_PROTOCOL_IAD,
    .bMaxPacketSize0=64,.idVendor=TX15_USB_VID,.idProduct=TX15_USB_PID,.bcdDevice=0x0100,
    .iManufacturer=1,.iProduct=2,.iSerialNumber=3,.bNumConfigurations=1
};
const uint8_t *tud_descriptor_device_cb(void) { return (const uint8_t *)&device; }
static const uint8_t configuration[]={
    TUD_CONFIG_DESCRIPTOR(1,2,0,TUD_CONFIG_DESC_LEN+TUD_CDC_DESC_LEN,0,100),
    TUD_CDC_DESCRIPTOR(0,4,0x81,8,0x02,0x82,64)
};
const uint8_t *tud_descriptor_configuration_cb(uint8_t index)
{ return index?NULL:configuration; }
const uint16_t *tud_descriptor_string_cb(uint8_t index,uint16_t language)
{
    (void)language;static uint16_t result[64];static const char *strings[]={
        "", "New Deviation", "New Deviation TX15 Updater", "", "Native Update"
    };
    unsigned n=0;
    if (!index) { result[1]=0x0409;n=1; }
    else if (index==3) {
        uint8_t uid[12];tx15_usb_hw_uid(uid);const char hex[]="0123456789abcdef";
        for (unsigned i=0;i<12;i++) { result[1+i*2]=hex[uid[i]>>4];result[2+i*2]=hex[uid[i]&15]; }
        n=24;
    } else {
        if (index>=sizeof(strings)/sizeof(strings[0])) return NULL;
        const char *p=strings[index];while (*p && n<63) result[++n]=(uint8_t)*p++;
    }
    result[0]=(uint16_t)((TUSB_DESC_STRING<<8)|(2*n+2));return result;
}

/* New Deviation TX15 USB board registers; GPL-3.0-or-later. */
#ifndef TX15_USB_HW_H
#define TX15_USB_HW_H
#include <stdint.h>
int tx15_usb_hw_init(uint32_t budget);
int tx15_usb_hw_session(uint64_t *session,uint32_t budget);
int tx15_usb_hw_vbus(void);
int tx15_usb_hw_sync(void);
void tx15_usb_hw_uid(uint8_t out[12]);
#endif

/* New Deviation USB CDC interface; GPL-3.0-or-later. */
#ifndef TX15_USB_BOARD_H
#define TX15_USB_BOARD_H
#include <stddef.h>
#include <stdint.h>
int tx15_usb_init(void);
void tx15_usb_poll(void);
size_t tx15_usb_read(uint8_t*,size_t);
size_t tx15_usb_write(const uint8_t*,size_t);
void tx15_usb_stop(void);
uint32_t tx15_usb_ms(void);
int tx15_usb_new_session(uint64_t*);
uint32_t tx15_usb_epoch(void);
int tx15_usb_connected(void);
int tx15_usb_synchronized(void);
#endif

/* Fixed application-owned PLL2 media clock; GPL-3.0-or-later. */
#ifndef TX15_MEDIA_CLOCK_H
#define TX15_MEDIA_CLOCK_H
/* PLL2R=196607910Hz; SD kernel/(2*246)=399609.6Hz. */
#define TX15_MEDIA_SD_DIVIDER 246u
int tx15_media_clock_init(void); /* idempotent; no waiting */
int tx15_media_clock_ready(void); /* -1 invalid,0 locking,1 ready */
/* Clock intentionally remains on through Audio/Storage page exit. */
#endif

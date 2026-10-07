/* Versioned model and transmitter input snapshot; GPL-3.0-or-later. */
#ifndef TX15_SETTINGS_SNAPSHOT_H
#define TX15_SETTINGS_SNAPSHOT_H
#include <stdint.h>
#define TX15_SNAPSHOT_MAGIC 0x534e4432u
struct tx15_snapshot_header { uint32_t magic,version,model_bytes,mode;uint16_t cal[6][3]; };
static inline int tx15_snapshot_valid(const struct tx15_snapshot_header *h,unsigned bytes) {
 if(h->magic!=TX15_SNAPSHOT_MAGIC || h->version!=1 || h->model_bytes!=bytes || h->mode<1 || h->mode>4)return 0;
 for(unsigned i=0;i<6;i++) {
  unsigned hi=h->cal[i][0],lo=h->cal[i][1],mid=h->cal[i][2];
  if(!hi && !lo && !mid)continue; /* Old uncalibrated models remain loadable. */
  if(!(lo<mid && mid<hi && hi<=4095))return 0;
 }return 1;
}
#endif

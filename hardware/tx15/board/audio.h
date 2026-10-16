/* Native A0 manual audio diagnostic; GPL-3.0-or-later. */
#ifndef TX15_AUDIO_H
#define TX15_AUDIO_H
#include <stdint.h>
enum {TX15_AUDIO_OFF,TX15_AUDIO_RESET,TX15_AUDIO_SETUP,TX15_AUDIO_READY,TX15_AUDIO_ERROR};
struct tx15_audio_report {
    uint32_t state,volume,steps,errors,tests,dma_irqs,underruns,frames;
};
extern volatile struct tx15_audio_report tx15_audio_report;
int tx15_audio_hw_init(void);
int tx15_audio_hw_test(unsigned now);
void tx15_audio_hw_poll(unsigned now);
void tx15_audio_hw_volume(unsigned level);
void tx15_audio_hw_stop(void);
void tx15_audio_reset_pin(unsigned high);
int tx15_audio_transport_init(void);
int tx15_audio_transport_ready(void);
void tx15_audio_transport_start(void);
void tx15_audio_transport_stop(void);
void tx15_audio_transport_poll(unsigned now);
int tx15_audio_transport_tone(unsigned frames);
#endif

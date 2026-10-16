/* Streaming mono PCM to signed16/32kHz. No allocation/I/O. GPL-3.0-or-later. */
#ifndef ND_AUDIO_PCM_H
#define ND_AUDIO_PCM_H
#include "wav.h"
#define ND_PCM_INPUT_LIMIT 512u
#define ND_PCM_OUTPUT_LIMIT 256u
enum {ND_PCM_MORE=0,ND_PCM_DONE=1,ND_PCM_FORMAT=-1,ND_PCM_TRUNCATED=-2};
struct nd_pcm {
    uint32_t frames,read,emitted;
    int32_t previous,next;
    int status;
    unsigned bits,ratio,phase,have_previous,have_pair,low,have_low;
};
int nd_pcm_init(struct nd_pcm *,const struct nd_wav_format *);
/* Retains a split 16-bit sample and pending interpolation across calls.
 * Stops at declared data end; no padding consumed. Zero output capacity
 * consumes no input. Last sample is held to preserve exact duration. */
int nd_pcm_process(struct nd_pcm *,const uint8_t *,size_t,size_t *used,
                   int16_t *,size_t,size_t *written);
/* At EOF, reject missing source samples. If all source is read but output
 * remains, returns MORE: drain using process(NULL,0,...). */
int nd_pcm_finish(struct nd_pcm *);
#endif

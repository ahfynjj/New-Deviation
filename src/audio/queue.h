/* Cooperative bounded request queue, no I/O or playback. GPL-3.0-or-later. */
#ifndef ND_AUDIO_QUEUE_H
#define ND_AUDIO_QUEUE_H
#include <stdint.h>
#define ND_AUDIO_QUEUE_CAPACITY 16u
#define ND_AUDIO_PATH_CAPACITY 128u
enum {ND_AUDIO_LUA,ND_AUDIO_NORMAL,ND_AUDIO_TIMER,ND_AUDIO_ALERT};
struct nd_audio_request {char path[ND_AUDIO_PATH_CAPACITY];uint32_t event_id;unsigned priority;};
struct nd_audio_queue {
    struct nd_audio_request items[ND_AUDIO_QUEUE_CAPACITY];
    unsigned count,peak,rejected,evicted,merged;
};
void nd_audio_queue_init(struct nd_audio_queue *);
/* Copies path. Nonzero event_id coalesces; zero requests remain distinct.
 * Queue validates length only; storage must validate/normalize the path
 * before use. Two capacity slots are reserved for alarms. Acceptance is
 * NOT evidence of a file existing, playback, or a Lua playFile API result. */
int nd_audio_queue_push(struct nd_audio_queue *,const char *path,unsigned priority,uint32_t event_id);
int nd_audio_queue_pop(struct nd_audio_queue *,struct nd_audio_request *);
/* Discards queued requests, retains statistics; does not stop DMA. */
void nd_audio_queue_clear(struct nd_audio_queue *);
#endif

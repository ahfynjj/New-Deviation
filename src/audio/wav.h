/* Bounded RIFF/WAVE header scanner, no allocation or I/O. GPL-3.0-or-later. */
#ifndef ND_AUDIO_WAV_H
#define ND_AUDIO_WAV_H
#include <stdint.h>
#include <stddef.h>
#define ND_WAV_FEED_LIMIT 512u
enum {ND_WAV_MORE=0,ND_WAV_DATA=1,ND_WAV_BAD_RIFF=-1,
      ND_WAV_FORMAT=-2,ND_WAV_LENGTH=-3,ND_WAV_TRUNCATED=-4};
struct nd_wav_format {
    uint32_t rate,frames,data_bytes,data_offset;
    uint16_t bits,align;
};
struct nd_wav {
    struct nd_wav_format format;
    uint32_t file_bytes,end,pos,skip,chunk_bytes;
    int status;
    unsigned have,need,phase,fmt_seen;
    uint8_t header[18];
};
void nd_wav_init(struct nd_wav *,uint32_t actual_file_bytes);
/* Consumes <=512 bytes and stops exactly at the first validated data body.
 * Caller retains all unconsumed bytes and bounds subsequent PCM reads to
 * format.data_bytes. DATA validates header/ranges, not the future I/O. */
int nd_wav_feed(struct nd_wav *,const uint8_t *,size_t,size_t *used);
/* Call at end of header input: MORE becomes TRUNCATED. */
int nd_wav_finish(struct nd_wav *);
#endif

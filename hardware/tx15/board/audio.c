/* Register values derived from TI TAS2505 SLAU472, not an EdgeTX runtime.
 * MCLK=8.192MHz, NDAC=2 MDAC=1 DOSR=128 -> 32kHz, PRB_P3 (RC4).
 * I2S 16-bit stereo, left channel routed to speaker. GPL-3.0-or-later. */
#include "audio.h"
#include "audio_memory.h"
#include "controls.h"
volatile struct tx15_audio_report tx15_audio_report;
static unsigned deadline,next,step,volume_dirty,pending_test,started,last_poll;
/* Delays apply after the write. One register transaction per poll at most.
 * Driver remains muted until DMA is running and all routing is ready. */
static const uint8_t setup[][3]={
    {0,1,0},{2,0,0}, /* 1.8V LDO / level shifters; headphone remains off. */
    {122,5,45},      /* Force reference, allow 40ms stabilization. */
    {1,0x10,0},{10,0,0},
    {45,0,0},{48,0,0},{46,127,0},
    {0,0,0},{4,0,0}, /* Codec uses MCLK directly, internal PLL stays off. */
    {11,0x82,0},{12,0x81,0},{13,0,0},{14,128,0},
    {27,0,0},{28,0,0},{60,3,0},
    {64,0x0c,0},{65,0xf4,0}, /* DAC muted; -6dB digital. */
    {63,0x90,10}, /* Power DAC, left channel; soft stepping. */
    {0,1,0},{46,56,0},{48,0x10,0},{45,2,0},
    {0,0,0},{64,4,0},{0,1,0}
};
int tx15_audio_hw_init(void) {
    tx15_audio_report=(struct tx15_audio_report){.volume=3};
    if(tx15_audio_memory_init()) {tx15_audio_report.reason=TX15_AUDIO_MEMORY;tx15_audio_report.state=TX15_AUDIO_ERROR;tx15_audio_report.errors++;return -1;}
    return 0;
}
void tx15_audio_hw_stop(void) {
    tx15_audio_reset_pin(0); /* Hardware mute does not depend on I2C success. */
    tx15_audio_transport_stop();tx15_audio_report.state=TX15_AUDIO_OFF;volume_dirty=pending_test=0;
}
static void fail(unsigned reason) {
    tx15_audio_report.reason=reason;
    tx15_audio_hw_stop();tx15_audio_report.state=TX15_AUDIO_ERROR;tx15_audio_report.errors++;
}
static int codec_write(unsigned reg,unsigned value) {
    tx15_audio_report.last_reg=reg;tx15_audio_report.last_value=value;
    int result=tx15_controls_audio_write(reg,value);
    tx15_audio_report.i2c_status=tx15_controls_audio_status();return result;
}
int tx15_audio_hw_test(unsigned now) {
    if(tx15_audio_report.state==TX15_AUDIO_READY) {
        if(pending_test || volume_dirty)return 0;
        if(!tx15_audio_transport_tone(9600))return 0;
        tx15_audio_report.tests++;return 1;
    }
    if(tx15_audio_report.state==TX15_AUDIO_RESET || tx15_audio_report.state==TX15_AUDIO_SETUP)return 0;
    tx15_audio_report.reason=0;tx15_audio_report.steps=0;
    tx15_audio_report.last_reg=tx15_audio_report.last_value=tx15_audio_report.i2c_status=0;
    tx15_audio_report.dma_flags=tx15_audio_report.spi_status=0;
    tx15_audio_report.elapsed=tx15_audio_report.max_gap=0;started=last_poll=now;
    if(tx15_audio_memory_init()) {fail(TX15_AUDIO_MEMORY);return 0;}
    tx15_audio_reset_pin(0);
    if(tx15_audio_transport_init()) {fail(TX15_AUDIO_OWNER);return 0;}
    deadline=now+500;next=now+2;step=0;pending_test=1;
    tx15_audio_report.state=TX15_AUDIO_RESET;return 1;
}
void tx15_audio_hw_volume(unsigned level) {
    /* Keep amplifier gain fixed; volume adjusts speaker attenuation only. */
    if(level>5)level=5;
    tx15_audio_report.volume=level;volume_dirty=2;
}
void tx15_audio_hw_poll(unsigned now) {
    unsigned state=tx15_audio_report.state;
    if(state==TX15_AUDIO_OFF || state==TX15_AUDIO_ERROR)return;
    if(state!=TX15_AUDIO_READY) {
        tx15_audio_report.elapsed=now-started;
        if(now-last_poll>tx15_audio_report.max_gap)tx15_audio_report.max_gap=now-last_poll;
        last_poll=now;
    }
    tx15_audio_transport_poll(now);
    if(state==TX15_AUDIO_READY) {
        if(tx15_audio_transport_ready()<0) {fail(tx15_audio_report.reason==TX15_AUDIO_DMA?TX15_AUDIO_DMA:TX15_AUDIO_TRANSPORT);return;}
        /* Setup leaves page 1 selected; no other caller accesses the codec. */
        if(volume_dirty) {
            unsigned level=tx15_audio_report.volume;
            if(level && volume_dirty==2) {
                static const uint8_t attenuation[]={127,72,48,24,12,0};
                if(codec_write(46,attenuation[level])) {fail(TX15_AUDIO_VOLUME);return;}
                volume_dirty=1;
            } else {
                if(codec_write(48,level?0x10:0)) {fail(TX15_AUDIO_VOLUME);return;}
                volume_dirty=0;
            }
            return; /* Apply selected attenuation/mute before queuing PCM. */
        }
        if(pending_test && tx15_audio_transport_tone(9600)) {pending_test=0;tx15_audio_report.tests++;}
        return;
    }
    if((int32_t)(now-deadline)>=0) {fail(TX15_AUDIO_DEADLINE);return;}
    if((int32_t)(now-next)<0)return;
    if(state==TX15_AUDIO_RESET) {
        tx15_audio_reset_pin(1);next=now+2;tx15_audio_report.state=TX15_AUDIO_SETUP;return;
    }
    int ready=tx15_audio_transport_ready();
    if(ready<0) {fail(tx15_audio_report.reason==TX15_AUDIO_DMA?TX15_AUDIO_DMA:TX15_AUDIO_TRANSPORT);return;}
    if(!ready)return;
    if(!step) {
        tx15_audio_transport_start(); /* Supply MCLK before powering DAC. */
        uint8_t page;
        tx15_audio_report.last_reg=0;
        int result=tx15_controls_audio_read(0,&page);
        tx15_audio_report.i2c_status=tx15_controls_audio_status();
        if(result || page) {fail(TX15_AUDIO_PROBE);return;}
        step++;next=now+1;return;
    }
    unsigned i=step-1;
    if(i<sizeof(setup)/sizeof(setup[0])) {
        if(codec_write(setup[i][0],setup[i][1])) {fail(TX15_AUDIO_WRITE);return;}
        tx15_audio_report.steps++;step++;next=now+(setup[i][2]?setup[i][2]:1);return;
    }
    tx15_audio_report.state=TX15_AUDIO_READY;
    volume_dirty=2;
}

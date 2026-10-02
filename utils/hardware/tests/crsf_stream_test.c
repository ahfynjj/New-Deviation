#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "crsf_stream.h"
int main(void) {
    struct crsf_stream s={0};struct crsf_frame in,out;
    uint8_t data[60]={0xea,0xee,'T','X',0,0x45,0x4c,0x52,0x53,0,0,0,1,0,0,0,2,9,0};
    assert(crsf_frame_build(&in,0xea,0x29,data,19));
    struct crsf_device device;
    assert(crsf_device_info(&in,&device));
    assert(!strcmp(device.name,"TX") && device.serial==0x454c5253);
    assert(device.hardware==1 && device.software==2 && device.fields==9);
    assert(!crsf_stream_feed(&s,0x55,0,&out));
    assert(!crsf_stream_feed(&s,0xea,0,&out));
    assert(!crsf_stream_feed(&s,0xff,0,&out));
    for(unsigned i=0;i<in.size;i++) assert(crsf_stream_feed(&s,in.bytes[i],i+1,&out)==(i==in.size-1));
    assert(out.size==in.size && !memcmp(in.bytes,out.bytes,in.size));
    in.bytes[in.size-1]^=1;
    for(unsigned i=0;i<in.size;i++) assert(!crsf_stream_feed(&s,in.bytes[i],40,&out));
    in.bytes[in.size-1]^=1;
    for(unsigned i=0;i<in.size;i++) assert(crsf_stream_feed(&s,in.bytes[i],100,&out)==(i==in.size-1));
    assert(!crsf_stream_feed(&s,0xea,UINT32_MAX-2,&out));
    assert(!crsf_stream_feed(&s,62,UINT32_MAX-1,&out));
    /* elapsed across wrap exceeds timeout, partial packet discarded */
    for(unsigned i=0;i<in.size;i++) assert(crsf_stream_feed(&s,in.bytes[i],30,&out)==(i==in.size-1));
    data[4]='X';
    assert(crsf_frame_build(&in,0xea,0x29,data,5));
    assert(!crsf_device_info(&in,&device)); /* no name terminator / metadata */
    memset(data,'A',sizeof(data));data[0]=0xea;data[1]=0xee;data[40]=0;
    assert(crsf_frame_build(&in,0xea,0x29,data,60));
    assert(crsf_device_info(&in,&device) && strlen(device.name)==31);
    for(unsigned i=0;i<in.size;i++) assert(crsf_stream_feed(&s,in.bytes[i],100,&out)==(i==in.size-1));
    assert(out.size==64);
    puts("CRSF stream fragmentation, CRC recovery, timeout and bounded device info PASS");
}

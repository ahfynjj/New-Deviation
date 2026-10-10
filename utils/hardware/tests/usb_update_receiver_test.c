#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../../hardware/tx15/usb_update/receiver.h"
static struct tx15_update_receiver receiver;
static void frame(void *ctx, const struct tx15_frame *f)
{
    (void)ctx; struct tx15_update_reply reply;
    int ok=tx15_update_receiver_request(&receiver,f,&reply);
    printf("%d %u %u %u %u\n",ok,reply.state,reply.error,reply.received,reply.total);
}
static uint32_t word(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
int main(int argc,char **argv)
{
    if (argc!=3) return 2;
    size_t cap=(size_t)strtoul(argv[2],NULL,0); uint8_t *ram=malloc(cap+16);
    if (!ram) return 3;
    memset(ram,0xa5,cap+16);
    tx15_update_receiver_init(&receiver,ram,cap,123,1,1);
    struct tx15_frame_parser parser; tx15_update_frame_init(&parser);
    FILE *f=fopen(argv[1],"rb"); if (!f) return 4;
    uint8_t h[5];
    while (fread(h,1,5,f)==5) {
        uint32_t n=word(h+1); if (n>4096) return 5;
        uint8_t b[4096]; if (fread(b,1,n,f)!=n) return 6;
        if (h[0]==1) for (uint32_t i=0;i<n;i++) tx15_update_frame_feed(&parser,b+i,1,frame,NULL);
        else if (h[0]==2 && n==4) tx15_update_receiver_tick(&receiver,word(b));
        else return 7;
        for (unsigned i=0;i<16;i++) if (ram[cap+i]!=0xa5) return 8;
    }
    fclose(f); free(ram); return 0;
}

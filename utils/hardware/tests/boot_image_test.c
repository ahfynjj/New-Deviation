#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../../hardware/tx15/boot/image.h"
static unsigned metadata(const unsigned char *p)
{
    return (unsigned)p[0] | (unsigned)p[1]<<8 | (unsigned)p[2]<<16 | (unsigned)p[3]<<24;
}
int main(int argc, char **argv)
{
    if (argc!=3) return 2;
    FILE *f=fopen(argv[1],"rb");
    if (!f) return 3;
    fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);
    if (n<0) return 4;
    unsigned char *data=malloc((size_t)n+1);
    if (!data) return 5;
    if (fread(data,1,(size_t)n,f)!=(size_t)n) return 6;
    fclose(f);
    struct tx15_boot_image plan;
    memset(&plan,0xa5,sizeof(plan));
    int valid=tx15_boot_image_validate(data,(size_t)n,&plan);
    if (valid!=atoi(argv[2])) return 7;
    if (!valid && (plan.entry || plan.segments[0].source || plan.segments[1].source
            || plan.segments[0].destination || plan.segments[1].destination
            || plan.segments[0].length || plan.segments[1].length)) return 8;
    if (valid && (plan.segments[0].destination!=0x24010000u
            || plan.segments[1].destination!=0xd0080000u || plan.segments[0].source!=data+64)) return 9;
    if (valid && (plan.entry!=metadata(data+16) || plan.segments[0].length!=metadata(data+32)
            || plan.segments[1].length!=metadata(data+48)
            || plan.segments[1].source!=data+metadata(data+44))) return 10;
    free(data);return 0;
}

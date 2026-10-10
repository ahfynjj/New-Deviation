#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../../../hardware/tx15/usb_update/package.h"
int main(int argc, char **argv)
{
    if (argc!=3) return 2;
    FILE *f=fopen(argv[1],"rb"); if (!f) return 3;
    fseek(f,0,SEEK_END); long n=ftell(f); rewind(f); if (n<0) return 4;
    uint8_t *p=malloc((size_t)n+1); if (!p) return 5;
    if (fread(p,1,(size_t)n,f)!=(size_t)n) return 6;
    fclose(f);
    struct tx15_update_package plan, zero;
    memset(&plan,0xa5,sizeof(plan)); memset(&zero,0,sizeof(zero));
    int valid=tx15_update_package_validate(p,(size_t)n,1,1,&plan);
    if (valid!=atoi(argv[2])) return 7;
    if (!valid && memcmp(&plan,&zero,sizeof(plan))) return 8;
    if (valid && (plan.image!=p+128 || plan.image_bytes!=(size_t)n-128
        || plan.boot.entry!=0x240102c1u || plan.boot.segments[0].source!=p+192)) return 9;
    free(p); return 0;
}

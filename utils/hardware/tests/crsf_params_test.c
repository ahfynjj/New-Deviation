#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "crsf_params.h"
int main(void) {
    struct crsf_params p;
    uint8_t request[4];
    struct crsf_message m={.type=0x2b,.payload={0xea,0xee,1,1,0,9,'R','a'},.size=8};
    assert(!crsf_params_init(&p,65));
    assert(crsf_params_init(&p,2));
    assert(crsf_params_request(&p,request) && request[0]==0xee && request[1]==0xea && request[2]==1 && request[3]==0);
    assert(crsf_params_accept(&p,&m)==1);
    assert(p.chunk==1 && p.lengths[0]==4);
    assert(crsf_params_accept(&p,&m)==-1); /* duplicate first chunk */
    assert(p.lengths[0]==4);
    m.payload[2]=2;assert(crsf_params_accept(&p,&m)==0); /* wrong field */
    m.payload[2]=1;m.payload[3]=0;m.payload[4]='t';m.payload[5]='e';m.payload[6]=0;m.size=7;
    assert(crsf_params_accept(&p,&m)==2);
    assert(p.current==2 && p.lengths[0]==7 && !memcmp(p.data[0],"\0\11Rate\0",7));
    assert(crsf_params_request(&p,request) && request[2]==2 && request[3]==0);
    assert(crsf_params_accept(&p,&m)==0); /* delayed previous parameter */
    m.payload[2]=2;m.payload[3]=1;m.size=60;
    memset(m.payload+4,42,56);
    assert(crsf_params_accept(&p,&m)==1);
    crsf_params_restart(&p);
    assert(p.current==2 && p.chunk==0 && p.lengths[1]==0 && p.lengths[0]==7);
    m.payload[3]=0;
    assert(crsf_params_accept(&p,&m)==3);
    assert(p.current==3 && !crsf_params_request(&p,request));
    assert(crsf_params_accept(&p,&m)==0);
    assert(crsf_params_init(&p,1));
    m.payload[2]=1;
    for(unsigned i=0;i<9;i++) {m.payload[3]=10-i;assert(crsf_params_accept(&p,&m)==1);}
    assert(p.lengths[0]==504);
    m.payload[3]=1;assert(crsf_params_accept(&p,&m)==-1); /* no write beyond 512 */
    assert(p.lengths[0]==504);
    crsf_params_restart(&p);m.size=4;assert(crsf_params_accept(&p,&m)==-1);
    m.size=61;assert(crsf_params_accept(&p,&m)==-1);
    assert(crsf_params_init(&p,0) && !crsf_params_request(&p,request));
    puts("Parameter chunk ordering, retries, completion and capacity bounds PASS");
}

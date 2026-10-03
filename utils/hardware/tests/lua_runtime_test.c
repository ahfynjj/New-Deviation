#include "lua/runner.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static union { double align; unsigned char bytes[256*1024]; } memory;
static struct nd_lua runner;
static struct crsf_link link;
static unsigned now, texts, clears, names, requests, writes, stops, safe_text, draw_cost;
static unsigned char captured[64][512];
static unsigned captured_sizes[64], captured_count;
static uint64_t completed_fields;
static uint32_t clock_ms(void *ctx) { (void)ctx; return now; }
static void clear(void *ctx) { (void)ctx; clears++;now+=draw_cost; }
static void text(void *ctx,int x,int y,const char *s,unsigned flags,uint16_t color)
{
    (void)ctx;(void)x;(void)y;(void)flags;(void)color;texts++;
    if(!strcmp(s,"?^v?")) safe_text++;
    if (!strcmp(s,"RF Band")) names|=1;
    if (!strcmp(s,"Packet Rate")) names|=2;
    if (!strncmp(s,"> TX Power",10)) names|=4;
    if (!strcmp(s,"Max Power")) names|=8;
}
static void dimensions(void *ctx,const char *s,unsigned flags,int *w,int *h)
{ (void)ctx;(void)flags;*w=(int)strlen(s)*10;*h=21; }
static void stop(void *ctx) { (void)ctx;stops++; }
static const struct nd_lua_host host={.clock_ms=clock_ms,.clear=clear,.text=text,.size_text=dimensions,.stop=stop};
static void start(const char *source)
{
    nd_lua_close(&runner);crsf_link_init(&link);crsf_link_select(&link,CRSF_SLOT_INTERNAL);
    assert(nd_lua_start(&runner,memory.bytes,sizeof(memory.bytes),&host,&link,source,strlen(source)));
}
static void reply(unsigned type,const unsigned char *payload,unsigned size)
{
    struct crsf_frame frame;assert(crsf_frame_build(&frame,0xea,type,payload,size));
    assert(crsf_link_receive(&link,link.slot,link.generation,&frame));
}
static int send(void *ctx,int slot,uint32_t generation,const uint8_t *frame,unsigned size)
{
    (void)ctx;assert(slot==0 && generation==link.generation);assert(size<=64);
    if (frame[2]==0x28) {
        unsigned char info[]={0xea,0xee,'T','e','s','t',' ','E','L','R','S',0,
            0x45,0x4c,0x52,0x53,0,0,0,0,0,4,1,0,4,0};
        if(captured_count) info[sizeof(info)-2]=(unsigned char)captured_count;
        reply(0x29,info,sizeof(info));
    } else if (frame[2]==0x2c) {
        unsigned id=frame[5];requests++;
        static const unsigned char f1[]={0,9,'R','F',' ','B','a','n','d',0,'2','.','4','G','H','z',0,0,0,0,0,0};
        static const unsigned char f2[]={0,9,'P','a','c','k','e','t',' ','R','a','t','e',0,'1','0','0','H','z',';','2','5','0','H','z',0,1,0,1,0,0};
        static const unsigned char f3[]={0,11,'T','X',' ','P','o','w','e','r',0};
        static const unsigned char f4[]={3,9,'M','a','x',' ','P','o','w','e','r',0,'2','5','m','W',';','1','0','0','m','W',0,0,0,1,0,0};
        const unsigned char *fields[]={f1,f2,f3,f4};unsigned sizes[]={sizeof(f1),sizeof(f2),sizeof(f3),sizeof(f4)};
        if(captured_count) {
            assert(id>=1 && id<=captured_count);unsigned offset=frame[6]*48;
            assert(offset<captured_sizes[id-1]);unsigned n=captured_sizes[id-1]-offset;if(n>48)n=48;
            unsigned char data[60]={0xea,0xee,(unsigned char)id,(unsigned char)((captured_sizes[id-1]-offset-1)/48)};
            if(!data[3]) completed_fields|=(uint64_t)1<<(id-1);
            memcpy(data+4,captured[id-1]+offset,n);reply(0x2b,data,4+n);return 1;
        }
        assert(id>=1 && id<=4);unsigned char data[60]={0xea,0xee,(unsigned char)id,0};
        memcpy(data+4,fields[id-1],sizes[id-1]);reply(0x2b,data,4+sizes[id-1]);
    } else { writes++;assert(frame[2]==0x2d && frame[5]==0 && frame[6]==0); }
    return 1;
}
int main(int argc,char **argv)
{
    assert(argc==2 || argc==3);
    struct nd_arena a;assert(nd_arena_init(&a,memory.bytes,sizeof(memory.bytes)));
    unsigned char *one=nd_arena_alloc(&a,NULL,0,31),*two=nd_arena_alloc(&a,NULL,0,71),*three=nd_arena_alloc(&a,NULL,0,55);
    assert(one && two && three);memset(one,0x4a,31);memset(three,0x2b,55);
    nd_arena_alloc(&a,two,71,0);one=nd_arena_alloc(&a,one,31,100);assert(one && one[30]==0x4a);
    size_t used=a.used;assert(!nd_arena_alloc(&a,three,55,sizeof(memory.bytes)));assert(a.used==used && three[54]==0x2b);
    one=nd_arena_alloc(&a,one,100,8);assert(one && *one==0x4a);
    nd_arena_alloc(&a,one,8,0);nd_arena_alloc(&a,three,55,0);assert(a.used==0);
    /* Parameter parsing allocates many tiny tables while most blocks remain
     * live. Bound actual search work rather than relying on host wall time. */
    assert(nd_arena_init(&a,memory.bytes,sizeof(memory.bytes)));
    void *small[2000];
    for(unsigned i=0;i<2000;i++) {small[i]=nd_arena_alloc(&a,NULL,0,24);assert(small[i]);}
    assert(a.search_steps<=6000);
    for(unsigned i=0;i<2000;i+=2) nd_arena_alloc(&a,small[i],24,0);
    a.search_steps=0;
    for(unsigned i=0;i<2000;i+=2) {small[i]=nd_arena_alloc(&a,NULL,0,24);assert(small[i]);}
    assert(a.search_steps<=3000);
    for(unsigned i=0;i<2000;i++) nd_arena_alloc(&a,small[i],24,0);
    assert(a.used==0);
    void *whole=nd_arena_alloc(&a,NULL,0,sizeof(memory.bytes)-32);assert(whole);
    nd_arena_alloc(&a,whole,sizeof(memory.bytes)-32,0);
    unsigned char *live[128]={0};size_t lengths[128]={0};uint32_t random=1234567;
    for(unsigned step=0;step<20000;step++) {
        random=random*1664525u+1013904223u;unsigned id=(random>>16)%128;
        random=random*1664525u+1013904223u;size_t wanted=(random>>16)%1536;
        if((random&7)==0)wanted=0;
        for(size_t j=0;j<lengths[id];j++)assert(live[id][j]==(unsigned char)id);
        size_t before_used=a.used;
        unsigned char *resized=nd_arena_alloc(&a,live[id],lengths[id],wanted);
        if(wanted && !resized) {assert(a.used==before_used);continue;}
        size_t preserved=lengths[id]<wanted?lengths[id]:wanted;
        for(size_t j=0;j<preserved;j++)assert(resized[j]==(unsigned char)id);
        live[id]=resized;lengths[id]=wanted;
        if(wanted)memset(resized,(unsigned char)id,wanted);
        if(!(step%256))for(unsigned i=0;i<128;i++)for(unsigned j=i+1;j<128;j++)
            if(live[i] && live[j])assert((uintptr_t)live[i]+lengths[i]<=(uintptr_t)live[j]
                || (uintptr_t)live[j]+lengths[j]<=(uintptr_t)live[i]);
    }
    for(unsigned i=0;i<128;i++)nd_arena_alloc(&a,live[i],lengths[i],0);
    assert(a.used==0);whole=nd_arena_alloc(&a,NULL,0,sizeof(memory.bytes)-32);assert(whole);
    nd_arena_alloc(&a,whole,sizeof(memory.bytes)-32,0);
    start("return {init=function() assert(os==nil and io==nil and debug==nil and loadfile==nil and dofile==nil and load==nil and require==nil and coroutine==nil) end, run=function(e) assert(model.getModule(0).Type==5 and model.getModule(1).Type==0); assert(crossfireTelemetryPush()==true); return 0 end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_RUNNING);
    start("return {run=function() lcd.drawText(0,0,string.char(128,192,193,226)); return 0 end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_RUNNING && safe_text==1);
    start("return {run=function() lcd.clear(); lcd.drawText(0,0,'ok'); return 0 end}");
    draw_cost=160;assert(nd_lua_run(&runner,0)==ND_LUA_RUNNING && runner.max_ms==160 && runner.draw_ms==160);draw_cost=0;
    start("return {run=function() collectgarbage('collect'); assert(type(collectgarbage('count'))=='number'); collectgarbage('step',1); return 0 end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_RUNNING && runner.gc_calls==3 && runner.alloc_calls>0);
    start("return {run=function() lcd.clear(); return 0 end}");
    draw_cost=300;assert(nd_lua_run(&runner,0)==ND_LUA_ERROR && strstr(runner.error,"time budget"));draw_cost=0;
    crsf_link_select(&link,CRSF_SLOT_EXTERNAL);
    assert(nd_lua_run(&runner,0)==ND_LUA_ERROR); /* No silent route switch. */
    start("return {run=function() error('intentional') end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_ERROR && strstr(runner.error,"intentional"));
    start("return {run=function() while true do end end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_ERROR && strstr(runner.error,"budget"));
    start("return {run=function() while true do xpcall(function() while true do end end,function(e) return e end) end end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_ERROR && strstr(runner.error,"budget"));
    start("return {run=function() while true do pcall(function() while true do end end) end end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_ERROR && strstr(runner.error,"budget"));
    start("return {run=function() local t={} while true do t[#t+1]=string.rep('x',4096) end end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_ERROR);
    start("return {run=function() setmetatable({}, {__gc=function() while true do end end}); return 0 end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_ERROR && strstr(runner.error,"finalizer"));
    start("return {run=function() assert(not crossfireTelemetryPush(0x16,{1,2})); assert(not crossfireTelemetryPush(0x2c,{238,234,1,256})); assert(not crossfireTelemetryPush(0x2c,{238,234,1,0.5})); assert(not crossfireTelemetryPush(0x2d,{238,234,1,1})); return 0 end}");
    assert(nd_lua_run(&runner,0)==ND_LUA_RUNNING);
    start("local count=0; return setmetatable({}, {__index=function(_,k) if k=='run' then count=count+1; if count==1 then return function() return 0 end end; error('lookup failure') end end})");
    assert(nd_lua_run(&runner,0)==ND_LUA_ERROR);
    start("return {run=function() return 2 end}");assert(nd_lua_run(&runner,0)==ND_LUA_EXITED);
    nd_lua_close(&runner);assert(runner.arena.used==0);
    FILE *file=fopen(argv[1],"rb");assert(file);fseek(file,0,SEEK_END);long len=ftell(file);rewind(file);
    char *script=malloc((size_t)len+1);assert(script && fread(script,1,len,file)==(size_t)len);fclose(file);script[len]=0;
    if(argc==3) {
        FILE *capture=fopen(argv[2],"rb");assert(capture);captured_count=(unsigned)fgetc(capture);assert(captured_count<=64);
        for(unsigned i=0;i<captured_count;i++) {
            unsigned lo=(unsigned)fgetc(capture),hi=(unsigned)fgetc(capture);captured_sizes[i]=lo+hi*256;
            assert(captured_sizes[i]<=512 && fread(captured[i],1,captured_sizes[i],capture)==captured_sizes[i]);
        }
        fclose(capture);
    }
    start(script);free(script);
    for (unsigned i=0;i<2500;i++) {
        now+=10;assert(nd_lua_run(&runner,0)==ND_LUA_RUNNING);crsf_link_service(&link,send,0);
    }
    assert(requests>=4 && (names&7)==7 && texts>20 && clears>0);
    if(captured_count) assert(completed_fields==(captured_count==64?UINT64_MAX:(((uint64_t)1<<captured_count)-1)));
    nd_lua_run(&runner,ND_EVT_NEXT);nd_lua_run(&runner,ND_EVT_NEXT);nd_lua_run(&runner,ND_EVT_ENTER);
    if(!captured_count) assert(names==15); /* Official folder navigation. */
    assert(!writes); /* Read-only API also blocks linkstat 0x2d in this first bench. */
    printf("Official Lua init/run, %u fields, folder, route guards, error/budget/OOM; peak %u bytes\n",captured_count?captured_count:4,(unsigned)runner.arena.peak);
    nd_lua_close(&runner);assert(runner.arena.used==0 && stops>=5);
    return 0;
}

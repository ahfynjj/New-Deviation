#include "lua/runner.h"
#include "protocol/transport/crsf_tools.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static union { double align; unsigned char bytes[256*1024]; } memory;
static struct nd_lua runner;
static struct crsf_link link;
static unsigned now, texts, clears, names, requests, writes, stats, stops, safe_text, draw_cost, power_index;
static unsigned char captured[64][512];
static unsigned captured_sizes[64], captured_count;
static uint64_t completed_fields;
static struct crsf_tools policy;
static unsigned use_policy,busy_until,deferred_reads;
static unsigned command_mode,starts,confirms,queries,cancels,command_status,popup_seen,silent,multipart;
static void command_reply(unsigned id,unsigned status)
;
static void command_chunk(unsigned id,unsigned status,unsigned chunk);
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
    if (strstr(s,"Confirm WiFi?") || strstr(s,"Running command")) popup_seen++;
}
static void dimensions(void *ctx,const char *s,unsigned flags,int *w,int *h)
{ (void)ctx;(void)flags;*w=(int)strlen(s)*10;*h=21; }
static void stop(void *ctx) { (void)ctx;stops++; }
static const char *tool_error(void *ctx) { (void)ctx;return crsf_tools_error(&policy); }
static int authorize(void *ctx,uint8_t type,const uint8_t *data,unsigned n)
{
    (void)ctx;
    if(use_policy)return crsf_tools_kind(&policy,type,data,n)!=0;
    return type!=0x2d || (n==4 && data[0]==0xee && data[1]==0xea
        && ((!data[2] && !data[3]) || (data[2]==4 && data[3]<=1)));
}
static const struct nd_lua_host host={.clock_ms=clock_ms,.clear=clear,.text=text,.size_text=dimensions,.stop=stop,.authorize=authorize,.error=tool_error};
static void start(const char *source)
{
    nd_lua_close(&runner);crsf_link_init(&link);crsf_link_select(&link,CRSF_SLOT_INTERNAL);
    assert(nd_lua_start(&runner,memory.bytes,command_mode?160*1024:sizeof(memory.bytes),&host,&link,source,strlen(source)));
}
static void reply(unsigned type,const unsigned char *payload,unsigned size)
{
    struct crsf_frame frame;assert(crsf_frame_build(&frame,0xea,type,payload,size));
    if(use_policy) {
        struct crsf_message m={.type=(uint8_t)type,.size=size};memcpy(m.payload,payload,size);
        crsf_tools_receive(&policy,&m,now);
    }
    assert(crsf_link_receive(&link,link.slot,link.generation,&frame));
}
static int send(void *ctx,int slot,uint32_t generation,const uint8_t *frame,unsigned size)
{
    (void)ctx;assert(slot==0 && generation==link.generation);assert(size<=64);
    if(use_policy) {
        int kind=crsf_tools_kind(&policy,frame[2],frame+3,size-4);
        if(!kind) {policy.report.denied++;return 1;} /* Same queue-time recheck as the product. */
        if(crsf_tools_defer(&policy,frame[2],frame+3,size-4,now)) {deferred_reads++;return 0;}
        if(kind==CRSF_TOOL_WRITE || (kind==CRSF_TOOL_COMMAND && frame[6]==1)) {
            if(!busy_until)busy_until=now+40;
            if(now<busy_until)return 0;
            busy_until=0;
        }
        crsf_tools_sent(&policy,frame[2],frame+3,size-4,now);
    }
    if (frame[2]==0x28) {
        unsigned char info[]={0xea,0xee,'T','e','s','t',' ','E','L','R','S',0,
            0x45,0x4c,0x52,0x53,0,0,0,0,0,4,1,0,4,0};
        if(captured_count) info[sizeof(info)-2]=(unsigned char)captured_count;
        else if(command_mode)info[sizeof(info)-2]=6;
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
        if(command_mode && id>=5) {command_chunk(id,command_status,frame[6]);return 1;}
        assert(id>=1 && id<=4);unsigned char data[60]={0xea,0xee,(unsigned char)id,0};
        memcpy(data+4,fields[id-1],sizes[id-1]);
        if(id==4)data[4+sizeof(f4)-5]=(uint8_t)power_index;
        reply(0x2b,data,4+sizes[id-1]);
    } else {
        assert(frame[2]==0x2d);
        if(frame[5]==0 && frame[6]==0)stats++;
        else if(command_mode && frame[5]>=5) {
            unsigned id=frame[5],op=frame[6];
            if(op==1) {starts++;command_status=id==5?3:2;}
            else if(op==4) {confirms++;assert(command_status==3);command_status=2;queries=0;}
            else if(op==5) {cancels++;command_status=0;}
            else {assert(op==6);queries++;if(command_status==2 && queries>=2)command_status=0;}
            if(!silent)command_reply(id,command_status);
        }
        else {assert(frame[5]==4 && frame[6]<=1);power_index=frame[6];writes++;}
    }
    return 1;
}
static void command_reply(unsigned id,unsigned status)
{ command_chunk(id,status,0); }
static void command_chunk(unsigned id,unsigned status,unsigned chunk)
{
    unsigned char field[180]={0,13};
    const char *name=id==5?"WiFi":"Bind";
    unsigned at=2,n=(unsigned)strlen(name)+1;memcpy(field+at,name,n);at+=n;
    field[at++]=(unsigned char)status;field[at++]=10;
    const char *info=status==3?"Confirm WiFi?":status==2?"Running command":"";
    n=(unsigned)strlen(info);memcpy(field+at,info,n);at+=n;
    if(multipart && status) {
        const char *detail=" - a long module progress message requiring multiple CRSF parameter chunks";
        n=(unsigned)strlen(detail);memcpy(field+at,detail,n);at+=n;
    }
    field[at++]=0;
    unsigned offset=chunk*40;assert(offset<at);n=at-offset;if(n>40)n=40;
    unsigned char data[60]={0xea,0xee,(unsigned char)id,(unsigned char)((at-offset-1)/40)};
    memcpy(data+4,field+offset,n);reply(0x2b,data,n+4);
}
static void step(int event)
{
    now+=10;assert(nd_lua_run(&runner,event)==ND_LUA_RUNNING);
    crsf_tools_tick(&policy,now);
    uint8_t payload[4];struct crsf_frame frame;
    if(crsf_tools_command_chunk(&policy,payload)) {
        assert(crsf_frame_build(&frame,0xee,0x2c,payload,4));send(NULL,link.slot,link.generation,frame.bytes,frame.size);
    }
    crsf_link_service(&link,send,0);
}
static void command_start(const char *script,unsigned id)
{
    command_mode=1;starts=confirms=queries=cancels=command_status=popup_seen=0;
    silent=0;
    busy_until=0;crsf_tools_init(&policy,1);start(script);runner.allow_writes=1;
    for(unsigned i=0;i<1500;i++)step(0);
    step(ND_EVT_NEXT);step(ND_EVT_NEXT);step(ND_EVT_NEXT);
    if(id==6)step(ND_EVT_NEXT);
    step(ND_EVT_ENTER);assert(!starts && policy.report.state==CRSF_WRITE_IDLE);
    for(unsigned i=0;i<8;i++)step(0);
    assert(starts==1 && popup_seen && policy.report.state==CRSF_WRITE_WAIT);
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
    use_policy=1;crsf_tools_init(&policy,1);start(script);
    for (unsigned i=0;i<2500;i++) {
        now+=10;assert(nd_lua_run(&runner,0)==ND_LUA_RUNNING);crsf_link_service(&link,send,0);
    }
    assert(requests>=4 && (names&7)==7 && texts>20 && clears>0);
    if(captured_count) assert(completed_fields==(captured_count==64?UINT64_MAX:(((uint64_t)1<<captured_count)-1)));
    nd_lua_run(&runner,ND_EVT_NEXT);nd_lua_run(&runner,ND_EVT_NEXT);nd_lua_run(&runner,ND_EVT_ENTER);
    if(!captured_count) assert(names==15); /* Official folder navigation. */
    assert(!writes && stats>0); /* Statistics requests are not parameter writes. */
    if(!captured_count) {
        unsigned before=requests;runner.allow_writes=1;
        nd_lua_run(&runner,ND_EVT_ENTER);nd_lua_run(&runner,ND_EVT_NEXT);nd_lua_run(&runner,ND_EVT_ENTER);
        for(unsigned i=0;i<300;i++) {now+=10;assert(nd_lua_run(&runner,0)==ND_LUA_RUNNING);crsf_link_service(&link,send,0);}
        assert(writes==1 && power_index==1 && requests>before);
        assert(policy.report.verified==1); /* Official reread after a delayed UART write. */
        nd_lua_run(&runner,ND_EVT_ENTER);nd_lua_run(&runner,ND_EVT_PREV);nd_lua_run(&runner,ND_EVT_ENTER);
        for(unsigned i=0;i<300;i++) {now+=10;assert(nd_lua_run(&runner,0)==ND_LUA_RUNNING);crsf_link_service(&link,send,0);}
        assert(writes==2 && power_index==0);
        assert(policy.report.verified==2 && deferred_reads>0);
        /* Execute the unmodified official script, including real popups and
         * an actual policy/UART-backpressure boundary. */
        command_start(script,5);
        for(unsigned i=0;i<400;i++)step(0); /* Wait >3s for human confirmation. */
        assert(!confirms && !queries && policy.report.state==CRSF_WRITE_WAIT);
        step(ND_EVT_ENTER);for(unsigned i=0;i<80;i++)step(0);
        assert(confirms==1 && queries>=2 && starts==1 && policy.report.completed==1);
        command_start(script,5);step(ND_EVT_EXIT);for(unsigned i=0;i<40;i++)step(0);
        assert(cancels==1 && !confirms && policy.report.state==CRSF_WRITE_CANCELLED);
        command_start(script,6);step(ND_EVT_EXIT);for(unsigned i=0;i<40;i++)step(0);
        assert(cancels==1 && starts==1 && policy.report.state==CRSF_WRITE_CANCELLED);
        command_start(script,6);for(unsigned i=0;i<80;i++)step(0);
        assert(starts==1 && queries>=2 && policy.report.completed==1);
        multipart=1;command_start(script,5);step(ND_EVT_ENTER);for(unsigned i=0;i<100;i++)step(0);
        assert(confirms==1 && queries>=2 && starts==1 && policy.report.completed==1);multipart=0;
        command_start(script,6);silent=1;
        for(unsigned i=0;i<285;i++)step(0);
        now+=200;crsf_tools_tick(&policy,now);unsigned old_stops=stops;
        assert(nd_lua_run(&runner,0)==ND_LUA_ERROR && strstr(runner.error,"timeout") && stops==old_stops+1);
    }
    free(script);
    printf("Official Lua init/run, %u fields, folder, route guards, error/budget/OOM; peak %u bytes\n",captured_count?captured_count:4,(unsigned)runner.arena.peak);
    nd_lua_close(&runner);assert(runner.arena.used==0 && stops>=5);
    return 0;
}

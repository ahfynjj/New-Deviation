#include "runner.h"
#include "vendor/lua-5.2.4/src/lua.h"
#include "vendor/lua-5.2.4/src/lauxlib.h"
#include "vendor/lua-5.2.4/src/lualib.h"
#include <string.h>
#define INSTRUCTION_LIMIT 120000u
#define RUN_TIME_LIMIT 250u
#define INIT_TIME_LIMIT 1000u
static struct nd_lua *owner(lua_State *L)
{ void *ud;lua_getallocf(L,&ud);return ud; }
static uint32_t time_ms(struct nd_lua *r)
{ return r->host.clock_ms?r->host.clock_ms(r->host.context):0; }
static void *allocator(void *ud,void *p,size_t old,size_t size)
{
    struct nd_lua *r=ud;uint32_t started=time_ms(r);
    void *result=nd_arena_alloc(&r->arena,p,old,size);
    r->alloc_ms+=time_ms(r)-started;r->alloc_calls++;return result;
}
static int collect(lua_State *L)
{
    struct nd_lua *r=owner(L);uint32_t started=time_ms(r);
    int results=r->collector(L);
    r->gc_ms+=time_ms(r)-started;r->gc_calls++;return results;
}
static void budget(lua_State *L,lua_Debug *ar)
{
    (void)ar;struct nd_lua *r=owner(L);r->instructions+=1000;
    if (r->instructions>INSTRUCTION_LIMIT) luaL_error(L,"Lua instruction budget exceeded");
    if ((uint32_t)(time_ms(r)-r->call_started)>r->time_limit) luaL_error(L,"Lua time budget exceeded");
    if (r->host.service) {uint32_t started=time_ms(r);r->host.service(r->host.context);r->service_ms+=time_ms(r)-started;}
}
static void begin(struct nd_lua *r)
{
    r->call_started=time_ms(r);r->instructions=r->drawing_ops=0;
    r->alloc_ms=r->alloc_calls=r->gc_ms=r->gc_calls=r->draw_ms=r->service_ms=0;
    lua_sethook(r->L,budget,LUA_MASKCOUNT,1000);
}
/* A tool must not swallow a budget failure with Lua pcall/xpcall. Recheck at
 * every protected boundary, because Lua 5.2 can suppress its count hook after
 * an error thrown from that hook. The platform's outer pcall remains final. */
static void check_budget(lua_State *L)
{
    struct nd_lua *r=owner(L);
    if(r->instructions>INSTRUCTION_LIMIT) luaL_error(L,"Lua instruction budget exceeded");
    if((uint32_t)(time_ms(r)-r->call_started)>r->time_limit) luaL_error(L,"Lua time budget exceeded");
}
static int safe_pcall(lua_State *L)
{
    luaL_checkany(L,1);int status=lua_pcall(L,lua_gettop(L)-1,LUA_MULTRET,0);
    check_budget(L);lua_pushboolean(L,status==LUA_OK);lua_insert(L,1);return lua_gettop(L);
}
static int safe_xpcall(lua_State *L)
{
    luaL_checktype(L,2,LUA_TFUNCTION);
    lua_pushvalue(L,1);lua_remove(L,1);lua_insert(L,2);
    int status=lua_pcall(L,lua_gettop(L)-2,LUA_MULTRET,0);check_budget(L);
    if(status!=LUA_OK) {
        lua_pushvalue(L,1);lua_insert(L,-2);
        lua_pcall(L,1,1,0);check_budget(L);
    }
    lua_remove(L,1);lua_pushboolean(L,status==LUA_OK);lua_insert(L,1);return lua_gettop(L);
}
/* Lua 5.2 runs __gc with hooks disabled. Tools cannot install finalizers that
 * would bypass the VM budget during collection or shutdown. */
static int safe_setmetatable(lua_State *L)
{
    luaL_checktype(L,1,LUA_TTABLE);
    if(!lua_isnil(L,2)) {
        luaL_checktype(L,2,LUA_TTABLE);lua_pushliteral(L,"__gc");lua_rawget(L,2);
        if(!lua_isnil(L,-1)) return luaL_error(L,"Lua finalizers are disabled");
        lua_pop(L,1);
    }
    if(lua_getmetatable(L,1)) {
        lua_pushliteral(L,"__metatable");lua_rawget(L,-2);
        if(!lua_isnil(L,-1)) return luaL_error(L,"Protected metatable");
        lua_pop(L,2);
    }
    lua_settop(L,2);lua_setmetatable(L,1);return 1;
}
static void fail(struct nd_lua *r,const char *s)
{
    if (!s) s="Lua memory exhausted";
    size_t n=strlen(s);if(n>=sizeof(r->error)) n=sizeof(r->error)-1;
    memcpy(r->error,s,n);r->error[n]=0;r->state=ND_LUA_ERROR;
    if (r->host.stop) r->host.stop(r->host.context);
}
static int protected_call(struct nd_lua *r,int args,int results)
{
    int status=lua_pcall(r->L,args,results,0);
    uint32_t elapsed=time_ms(r)-r->call_started;
    if (r->state==ND_LUA_RUNNING) {if(elapsed>r->max_ms) r->max_ms=elapsed;}
    else r->init_ms=elapsed;
    if (status!=LUA_OK) {fail(r,lua_tostring(r->L,-1));lua_settop(r->L,0);return 0;}
    if(elapsed>r->time_limit) {fail(r,"Lua time budget exceeded");lua_settop(r->L,0);return 0;}
    return 1;
}
static int get_time(lua_State *L)
{ lua_pushnumber(L,time_ms(owner(L))/10u);return 1; }
static int get_version(lua_State *L)
{
    lua_pushliteral(L,"New Deviation Lua API 1");lua_pushliteral(L,"TX15");
    lua_pushinteger(L,2);lua_pushinteger(L,0);lua_pushinteger(L,0);lua_pushliteral(L,"Deviation");return 6;
}
static int get_module(lua_State *L)
{
    struct nd_lua *r=owner(L);int index=(int)luaL_checkinteger(L,1);
    if(index<0 || index>1) return 0;
    lua_newtable(L);lua_pushinteger(L,r->link->slot==index?5:0);lua_setfield(L,-2,"Type");return 1;
}
static int push(lua_State *L)
{
    struct nd_lua *r=owner(L);
    if(!lua_gettop(L)) {lua_pushboolean(L,crsf_link_can_push(r->link));return 1;}
    lua_Number type=luaL_checknumber(L,1);luaL_checktype(L,2,LUA_TTABLE);
    size_t n=lua_rawlen(L,2);uint8_t data[CRSF_LINK_PAYLOAD_MAX];int allowed=1;
    if(!(type==0x28 || type==0x2c || type==0x2d) || n<2 || n>sizeof(data)) allowed=0;
    if(allowed) for(size_t i=0;i<n;i++) {
        lua_rawgeti(L,2,(int)i+1);lua_Number b=lua_tonumber(L,-1);
        if(!lua_isnumber(L,-1) || !(b>=0 && b<=255) || (int)b!=b) allowed=0;
        data[i]=allowed?(uint8_t)b:0;lua_pop(L,1);
    }
    if(allowed && type==0x2d && !r->allow_writes) {r->blocked_writes++;allowed=0;}
    lua_pushboolean(L,allowed && crsf_link_push(r->link,(uint8_t)type,data,(unsigned)n));return 1;
}
static int pop(lua_State *L)
{
    struct crsf_message message;
    if(!crsf_link_pop(owner(L)->link,&message)) return 0;
    lua_pushinteger(L,message.type);lua_createtable(L,message.size,0);
    for(unsigned i=0;i<message.size;i++) {lua_pushinteger(L,message.payload[i]);lua_rawseti(L,-2,i+1);}
    return 2;
}
static int rgb(lua_State *L)
{
    unsigned c[3];for(int i=0;i<3;i++) {int n=(int)luaL_checkinteger(L,i+1);c[i]=(unsigned)(n<0?0:n>255?255:n);}
    lua_pushinteger(L,((c[0]>>3)<<11)|((c[1]>>2)<<5)|(c[2]>>3));return 1;
}
static uint16_t color(struct nd_lua *r,unsigned flags)
{ return flags&ND_CUSTOM_COLOR?r->custom_color:flags&ND_DISABLED?0x8410:0; }
static void draw_budget(lua_State *L)
{
    struct nd_lua *r=owner(L);
    if(++r->drawing_ops>256) luaL_error(L,"Lua drawing budget exceeded");
    check_budget(L);
}
static int coordinate(lua_State *L,int n)
{
    lua_Number v=luaL_checknumber(L,n);
    if(!(v>=-1024 && v<=1024)) luaL_error(L,"drawing coordinate outside bounds");
    return (int)v;
}
static const char *bounded_string(lua_State *L,int n,char out[264])
{
    size_t size;const char *s=luaL_checklstring(L,n,&size);
    if(size>256) luaL_error(L,"text outside bounds");
    /* Native utf8_to_u32 assumes valid, terminated strings and reads 5 bytes
     * ahead even for ASCII. Validate input and pad that lookahead explicitly.
     * OpenTX's legacy arrow bytes are standalone symbols, not UTF-8 leads. */
    memset(out,0,264);size_t at=0;
    for(size_t i=0;i<size && s[i];) {
        unsigned char b=(unsigned char)s[i];
        if(b<128) {out[at++]=(b<32 && b!='\n')?' ':(char)b;i++;continue;}
        if(b==192 || b==193) {out[at++]=b==192?'^':'v';i++;continue;}
        unsigned nbytes=b>=194 && b<=223?2:b>=224 && b<=239?3:b>=240 && b<=244?4:0;
        uint32_t code=b&((1u<<(7-nbytes))-1u);int valid=nbytes && i+nbytes<=size;
        for(unsigned j=1;valid && j<nbytes;j++) {
            unsigned char c=(unsigned char)s[i+j];if(c<128 || c>191) valid=0;
            else code=(code<<6)|(c&63);
        }
        valid=valid && code>=((uint32_t[]){0,0,128,2048,65536})[nbytes]
            && code<=0x10ffff && !(code>=0xd800 && code<=0xdfff);
        if(valid) {memcpy(out+at,s+i,nbytes);at+=nbytes;i+=nbytes;}
        else {out[at++]='?';i++;}
    }
    return out;
}
static void dimensions(struct nd_lua *r,const char *s,unsigned flags,int *w,int *h)
{
    *w=(int)strlen(s)*10;*h=21;
    if(r->host.size_text) {uint32_t started=time_ms(r);r->host.size_text(r->host.context,s,flags,w,h);r->draw_ms+=time_ms(r)-started;}
}
static int clear(lua_State *L)
{ struct nd_lua *r=owner(L);draw_budget(L);if(r->host.clear) {uint32_t started=time_ms(r);r->host.clear(r->host.context);r->draw_ms+=time_ms(r)-started;}return 0; }
static int set_color(lua_State *L)
{ owner(L)->custom_color=(uint16_t)luaL_checkinteger(L,2);return 0; }
static int text(lua_State *L)
{
    struct nd_lua *r=owner(L);draw_budget(L);
    char buffer[264];int x=coordinate(L,1),y=coordinate(L,2),w,h;const char *s=bounded_string(L,3,buffer);
    unsigned flags=(unsigned)luaL_optinteger(L,4,0);dimensions(r,s,flags,&w,&h);
    if(flags&ND_CENTER) x-=w/2;else if(flags&ND_RIGHT) x-=w;
    if(r->host.text) {uint32_t started=time_ms(r);r->host.text(r->host.context,x,y,s,flags,color(r,flags));r->draw_ms+=time_ms(r)-started;}
    r->last_pos=x+w;return 0;
}
static int size_text(lua_State *L)
{
    char buffer[264];int w,h;draw_budget(L);dimensions(owner(L),bounded_string(L,1,buffer),(unsigned)luaL_optinteger(L,2,0),&w,&h);
    lua_pushinteger(L,w);lua_pushinteger(L,h);return 2;
}
static int last_pos(lua_State *L) {lua_pushinteger(L,owner(L)->last_pos);return 1;}
static int rectangle(lua_State *L,int fill)
{
    struct nd_lua *r=owner(L);draw_budget(L);
    int x=coordinate(L,1),y=coordinate(L,2),w=coordinate(L,3),h=coordinate(L,4);
    unsigned flags=(unsigned)luaL_optinteger(L,5,0);
    if(w>0 && h>0 && r->host.rect) {uint32_t started=time_ms(r);r->host.rect(r->host.context,x,y,w,h,color(r,flags),fill);r->draw_ms+=time_ms(r)-started;}
    return 0;
}
static int rect(lua_State *L) {return rectangle(L,0);}
static int filled_rect(lua_State *L) {return rectangle(L,1);}
static int line(lua_State *L)
{
    struct nd_lua *r=owner(L);draw_budget(L);
    int x=coordinate(L,1),y=coordinate(L,2),x2=coordinate(L,3),y2=coordinate(L,4);
    if(r->host.line) {uint32_t started=time_ms(r);r->host.line(r->host.context,x,y,x2,y2,color(r,(unsigned)luaL_optinteger(L,6,0)));r->draw_ms+=time_ms(r)-started;}
    return 0;
}
static int popup(lua_State *L)
{
    struct nd_lua *r=owner(L);draw_budget(L);
    char title_buffer[264],info_buffer[264];
    const char *title=bounded_string(L,1,title_buffer),*info=bounded_string(L,2,info_buffer);int event=(int)luaL_checkinteger(L,3);
    if(r->host.clear) r->host.clear(r->host.context);
    if(r->host.text) {r->host.text(r->host.context,10,70,title,0,0);r->host.text(r->host.context,10,110,info,0,0);}
    if(event==ND_EVT_EXIT) lua_pushliteral(L,"CANCEL");
    else if(event==ND_EVT_ENTER) lua_pushliteral(L,"OK");else return 0;
    return 1;
}
static void global_number(lua_State *L,const char *name,int value)
{lua_pushinteger(L,value);lua_setglobal(L,name);}
static void global_function(lua_State *L,const char *name,lua_CFunction function)
{lua_pushcfunction(L,function);lua_setglobal(L,name);}
static int initialize(lua_State *L)
{
    struct nd_lua *r=owner(L);
    luaL_requiref(L,"_G",luaopen_base,1);lua_pop(L,1);
    lua_getglobal(L,"collectgarbage");r->collector=lua_tocfunction(L,-1);lua_pop(L,1);
    global_function(L,"collectgarbage",collect);
    luaL_requiref(L,LUA_TABLIBNAME,luaopen_table,1);lua_pop(L,1);
    luaL_requiref(L,LUA_STRLIBNAME,luaopen_string,1);lua_pop(L,1);
    luaL_requiref(L,LUA_MATHLIBNAME,luaopen_math,1);lua_pop(L,1);
    luaL_requiref(L,LUA_BITLIBNAME,luaopen_bit32,1);lua_pop(L,1);
    const char *removed[]={"dofile","loadfile","load","print"};
    for(unsigned i=0;i<sizeof(removed)/sizeof(*removed);i++) {lua_pushnil(L);lua_setglobal(L,removed[i]);}
    global_function(L,"getTime",get_time);global_function(L,"getVersion",get_version);
    global_function(L,"pcall",safe_pcall);global_function(L,"xpcall",safe_xpcall);
    global_function(L,"setmetatable",safe_setmetatable);
    global_function(L,"crossfireTelemetryPush",push);global_function(L,"crossfireTelemetryPop",pop);
    global_function(L,"popupConfirmation",popup);
    lua_pushliteral(L,"^");lua_setglobal(L,"CHAR_UP");
    lua_pushliteral(L,"v");lua_setglobal(L,"CHAR_DOWN");
    const luaL_Reg lcd[]={{"clear",clear},{"RGB",rgb},{"setColor",set_color},{"drawText",text},
        {"sizeText",size_text},{"getLastPos",last_pos},{"drawRectangle",rect},
        {"drawFilledRectangle",filled_rect},{"drawLine",line},{NULL,NULL}};
    luaL_newlib(L,lcd);lua_setglobal(L,"lcd");
    const luaL_Reg model[]={{"getModule",get_module},{NULL,NULL}};
    luaL_newlib(L,model);lua_setglobal(L,"model");
    const struct {const char *name;int value;} constants[]={
        {"LCD_W",480},{"LCD_H",320},{"EVT_VIRTUAL_ENTER",ND_EVT_ENTER},{"EVT_VIRTUAL_EXIT",ND_EVT_EXIT},
        {"EVT_VIRTUAL_NEXT",ND_EVT_NEXT},{"EVT_VIRTUAL_PREV",ND_EVT_PREV},{"EVT_TOUCH_TAP",100},
        {"INVERS",ND_INVERS},{"BLINK",ND_BLINK},{"BOLD",ND_BOLD},{"CENTER",ND_CENTER},{"RIGHT",ND_RIGHT},
        {"MIDSIZE",ND_MIDSIZE},{"CUSTOM_COLOR",ND_CUSTOM_COLOR},{"COLOR_THEME_DISABLED",ND_DISABLED},
        {"WHITE",65535},{"BLACK",0},{"SOLID",0}};
    for(unsigned i=0;i<sizeof(constants)/sizeof(*constants);i++) global_number(L,constants[i].name,constants[i].value);
    int status=luaL_loadbufferx(L,r->source,r->source_size,"@elrs.lua","t");
    if(status!=LUA_OK) return lua_error(L);
    lua_call(L,0,1);luaL_checktype(L,-1,LUA_TTABLE);
    lua_getfield(L,-1,"run");luaL_checktype(L,-1,LUA_TFUNCTION);lua_pop(L,1);
    lua_getfield(L,-1,"init");
    if(!lua_isnil(L,-1)) {luaL_checktype(L,-1,LUA_TFUNCTION);lua_call(L,0,0);}
    else lua_pop(L,1);
    r->script_ref=luaL_ref(L,LUA_REGISTRYINDEX);return 0;
}
int nd_lua_start(struct nd_lua *r,void *memory,size_t size,const struct nd_lua_host *host,
                 struct crsf_link *link,const char *source,size_t source_size)
{
    if(!r || !host || !link || !source || !source_size || source_size>65536) return 0;
    memset(r,0,sizeof(*r));r->host=*host;r->link=link;r->slot=link->slot;r->generation=link->generation;
    r->source=source;r->source_size=source_size;
    if(!nd_arena_init(&r->arena,memory,size)) {fail(r,"Invalid Lua arena");return 0;}
    r->L=lua_newstate(allocator,r);
    if(!r->L) {fail(r,"Lua memory exhausted");return 0;}
    r->time_limit=INIT_TIME_LIMIT;begin(r);lua_pushcfunction(r->L,initialize);
    if(!protected_call(r,0,0)) return 0;
    r->state=ND_LUA_RUNNING;r->source=NULL;r->source_size=0;return 1;
}
static int invoke_run(lua_State *L)
{
    struct nd_lua *r=owner(L);
    lua_rawgeti(L,LUA_REGISTRYINDEX,r->script_ref);lua_getfield(L,-1,"run");
    luaL_checktype(L,-1,LUA_TFUNCTION);lua_remove(L,-2);lua_pushinteger(L,r->event);
    lua_call(L,1,1);lua_Number result=luaL_checknumber(L,-1);
    if(!(result>=0 && result<=2) || (int)result!=result) luaL_error(L,"Invalid tool return value");
    return 1;
}
int nd_lua_run(struct nd_lua *r,int event)
{
    if(!r || r->state!=ND_LUA_RUNNING) return r?r->state:ND_LUA_ERROR;
    if(r->link->generation!=r->generation || r->link->slot!=r->slot) {fail(r,"Module session changed");return r->state;}
    r->time_limit=RUN_TIME_LIMIT;r->event=event;begin(r);lua_pushcfunction(r->L,invoke_run);
    if(!protected_call(r,0,1)) return r->state;
    int result=(int)lua_tointeger(r->L,-1);lua_settop(r->L,0);r->runs++;
    if(result) {r->state=ND_LUA_EXITED;if(r->host.stop) r->host.stop(r->host.context);}
    /* Script requests full collections while parsing; step otherwise. */
    return r->state;
}
void nd_lua_close(struct nd_lua *r)
{
    if(!r) return;
    if(r->L) {begin(r);lua_close(r->L);r->L=NULL;}
    if(r->state==ND_LUA_RUNNING && r->host.stop) r->host.stop(r->host.context);
    r->state=ND_LUA_IDLE;
}

/* Native Deviation Lua tool runner; GPL-3.0-or-later. */
#ifndef ND_LUA_RUNNER_H
#define ND_LUA_RUNNER_H
#include "arena.h"
#include "protocol/transport/crsf_link.h"
typedef struct lua_State lua_State;
enum { ND_EVT_ENTER=1,ND_EVT_EXIT=2,ND_EVT_NEXT=3,ND_EVT_PREV=4 };
enum { ND_INVERS=1,ND_BLINK=2,ND_BOLD=4,ND_CENTER=8,ND_RIGHT=16,ND_MIDSIZE=32,
       ND_CUSTOM_COLOR=256,ND_DISABLED=512 };
enum { ND_LUA_IDLE,ND_LUA_RUNNING,ND_LUA_EXITED,ND_LUA_ERROR };
struct nd_lua_host {
    void *context;
    uint32_t (*clock_ms)(void *);
    void (*service)(void *); /* Bounded platform service, must not reenter Lua. */
    void (*clear)(void *);
    void (*text)(void *,int,int,const char *,unsigned,uint16_t);
    void (*size_text)(void *,const char *,unsigned,int *,int *);
    void (*rect)(void *,int,int,int,int,uint16_t,int);
    void (*line)(void *,int,int,int,int,uint16_t);
    void (*stop)(void *); /* Close selected bench link on failure/exit. */
};
struct nd_lua {
    struct nd_arena arena;
    lua_State *L;
    struct nd_lua_host host;
    struct crsf_link *link;
    uint32_t generation,call_started,instructions,runs,max_ms,blocked_writes,init_ms,time_limit;
    /* Last protected call: GC includes allocator time; drawing includes size
     * queries. These counters diagnose stalls without relaxing the budget. */
    uint32_t alloc_ms,alloc_calls,gc_ms,gc_calls,draw_ms,service_ms;
    int (*collector)(lua_State *);
    int slot,state,script_ref,last_pos,event;
    uint16_t custom_color;
    unsigned drawing_ops,allow_writes;
    const char *source;
    size_t source_size;
    char error[160];
};
/* A fresh single-slot session is captured; route changes abort the tool.
 * Source-only, <=64KiB. No filesystem, dynamic loader, OS, debug or coroutine.
 * First bench is read-only; write support requires explicit allow_writes.
 * Count/time hooks bound Lua VM work. C library/GC timings need board proof.
 */
int nd_lua_start(struct nd_lua *,void *,size_t,const struct nd_lua_host *,
                 struct crsf_link *,const char *,size_t);
int nd_lua_run(struct nd_lua *,int event);
void nd_lua_close(struct nd_lua *);
#endif

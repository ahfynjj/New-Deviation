/* Bounded Lua allocator; GPL-3.0-or-later. Caller owns aligned RAM. */
#ifndef ND_LUA_ARENA_H
#define ND_LUA_ARENA_H
#include <stddef.h>
#include <stdint.h>
struct nd_arena {
    unsigned char *memory;
    size_t size,used,peak;
    unsigned search_steps;
    uint32_t bins[32];
};
int nd_arena_init(struct nd_arena *a,void *memory,size_t size);
void *nd_arena_alloc(void *ud,void *ptr,size_t old_size,size_t new_size);
#endif

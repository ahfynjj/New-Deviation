#include "arena.h"
#include <string.h>
#define ALIGN(n) (((n)+7u)&~(size_t)7u)
#define NONE UINT32_MAX
/* Fixed-width offsets keep header size identical on the board and host.
 * Low size bit marks free blocks; all payloads are aligned to eight bytes. */
struct block { uint32_t size,previous,next_free,prev_free; };
#define HEADER sizeof(struct block)
static size_t payload(const struct block *b) { return b->size&~7u; }
static struct block *block_at(struct nd_arena *a,uint32_t at)
{ return at==NONE?NULL:(struct block *)(a->memory+at); }
static uint32_t offset(struct nd_arena *a,struct block *b)
{ return (uint32_t)((unsigned char *)b-a->memory); }
static unsigned bucket(size_t size)
{ unsigned n=0;while(size>>=1)n++;return n; }
static struct block *next(struct nd_arena *a,struct block *b)
{
    unsigned char *p=(unsigned char *)b+HEADER+payload(b);
    return p<a->memory+a->size?(struct block *)p:NULL;
}
static void update_next(struct nd_arena *a,struct block *b)
{ struct block *n=next(a,b);if(n)n->previous=offset(a,b); }
static void insert(struct nd_arena *a,struct block *b)
{
    unsigned bin=bucket(payload(b));uint32_t at=offset(a,b);
    b->size|=1;b->prev_free=NONE;b->next_free=a->bins[bin];
    struct block *n=block_at(a,b->next_free);if(n)n->prev_free=at;
    a->bins[bin]=at;
}
static void remove_free(struct nd_arena *a,struct block *b)
{
    struct block *p=block_at(a,b->prev_free),*n=block_at(a,b->next_free);
    if(p)p->next_free=b->next_free;else a->bins[bucket(payload(b))]=b->next_free;
    if(n)n->prev_free=b->prev_free;
    b->size&=~1u;
}
static void release(struct nd_arena *a,struct block *b)
{
    a->used-=payload(b);
    struct block *n=next(a,b);
    if(n && (n->size&1)) {
        remove_free(a,n);b->size=(uint32_t)(payload(b)+HEADER+payload(n));
    }
    struct block *p=block_at(a,b->previous);
    if(p && (p->size&1)) {
        remove_free(a,p);p->size=(uint32_t)(payload(p)+HEADER+payload(b));b=p;
    }
    update_next(a,b);insert(a,b);
}
static void split(struct nd_arena *a,struct block *b,size_t size)
{
    size_t before=payload(b);
    if(before-size<HEADER+8)return;
    struct block *tail=(struct block *)((unsigned char *)b+HEADER+size);
    tail->size=(uint32_t)(before-size-HEADER);tail->previous=offset(a,b);
    b->size=(uint32_t)size;
    struct block *n=next(a,tail);
    if(n && (n->size&1)) {
        remove_free(a,n);tail->size+=(uint32_t)(HEADER+payload(n));
    }
    update_next(a,tail);insert(a,tail);
}
int nd_arena_init(struct nd_arena *a,void *memory,size_t size)
{
    if(!a || !memory || (uintptr_t)memory%8 || size<HEADER+8 || size>UINT32_MAX)return 0;
    memset(a,0,sizeof(*a));a->memory=memory;a->size=size&~(size_t)7;
    for(unsigned i=0;i<32;i++)a->bins[i]=NONE;
    struct block *b=memory;b->size=(uint32_t)(a->size-HEADER);b->previous=NONE;
    insert(a,b);return 1;
}
void *nd_arena_alloc(void *ud,void *ptr,size_t old_size,size_t new_size)
{
    struct nd_arena *a=ud;(void)old_size;
    struct block *old=ptr?(struct block *)((unsigned char *)ptr-HEADER):NULL;
    if(!new_size) {if(old)release(a,old);return NULL;}
    if(new_size>a->size-HEADER)return NULL;
    size_t size=ALIGN(new_size);
    if(old) {
        size_t before=payload(old);
        struct block *n=next(a,old);
        if(before<size && n && (n->size&1) && before+HEADER+payload(n)>=size) {
            remove_free(a,n);old->size=(uint32_t)(before+HEADER+payload(n));update_next(a,old);
        }
        if(payload(old)>=size) {
            split(a,old,size);a->used=a->used-before+payload(old);
            if(a->used>a->peak)a->peak=a->used;
            return ptr;
        }
    }
    /* Search free blocks only, beginning at the size class of the request.
     * Live Lua objects no longer make each subsequent allocation slower. */
    for(unsigned bin=bucket(size);bin<32;bin++) {
        for(struct block *b=block_at(a,a->bins[bin]);b;b=block_at(a,b->next_free)) {
            a->search_steps++;
            if(payload(b)<size)continue;
            remove_free(a,b);split(a,b,size);a->used+=payload(b);
            void *result=(unsigned char *)b+HEADER;
            if(old) {memcpy(result,ptr,payload(old)<new_size?payload(old):new_size);release(a,old);}
            if(a->used>a->peak)a->peak=a->used;
            return result;
        }
    }
    return NULL;
}

#include "arena.h"
#include <stdint.h>
#include <string.h>
#define ALIGN(n) (((n)+7u)&~(size_t)7u)
struct block { size_t size; size_t free; };
#define HEADER ALIGN(sizeof(struct block))
int nd_arena_init(struct nd_arena *a,void *memory,size_t size)
{
    if (!a || !memory || (uintptr_t)memory%8 || size<HEADER+8) return 0;
    *a=(struct nd_arena){memory,size&~(size_t)7,0,0};
    struct block *b=memory;b->size=a->size-HEADER;b->free=1;return 1;
}
static struct block *next(struct nd_arena *a,struct block *b)
{
    unsigned char *p=(unsigned char *)b+HEADER+b->size;
    return p<a->memory+a->size?(struct block *)p:NULL;
}
static void merge(struct nd_arena *a,struct block *b)
{
    struct block *n;
    while ((n=next(a,b)) && n->free) b->size+=HEADER+n->size;
}
static void split(struct block *b,size_t size)
{
    if (b->size>=size+HEADER+8) {
        struct block *n=(struct block *)((unsigned char *)b+HEADER+size);
        n->size=b->size-size-HEADER;n->free=1;b->size=size;
    }
}
void *nd_arena_alloc(void *ud,void *ptr,size_t old_size,size_t new_size)
{
    struct nd_arena *a=ud;(void)old_size;
    struct block *old=ptr?(struct block *)((unsigned char *)ptr-HEADER):NULL;
    if (!new_size) {
        if (old) {a->used-=old->size;old->free=1;}
        return NULL;
    }
    if (new_size>a->size-HEADER) return NULL;
    size_t size=ALIGN(new_size);
    if (old) {
        size_t before=old->size;
        size_t available=before;
        for(struct block *b=next(a,old);b && b->free;b=next(a,b)) available+=HEADER+b->size;
        if(available>=size) merge(a,old);
        if (old->size>=size) {
            split(old,size);a->used=a->used-before+old->size;
            if (a->used>a->peak) a->peak=a->used;
            return ptr;
        }
    }
    for (struct block *b=(struct block *)a->memory;b;b=next(a,b)) {
        if (!b->free) continue;
        merge(a,b);
        if (b->size<size) continue;
        split(b,size);b->free=0;a->used+=b->size;
        void *result=(unsigned char *)b+HEADER;
        if (old) {
            memcpy(result,ptr,old->size<new_size?old->size:new_size);
            a->used-=old->size;old->free=1;
        }
        if (a->used>a->peak) a->peak=a->used;
        return result;
    }
    return NULL;
}

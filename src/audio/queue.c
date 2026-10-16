#include "queue.h"
#include <string.h>
void nd_audio_queue_init(struct nd_audio_queue *q) {memset(q,0,sizeof(*q));}
void nd_audio_queue_clear(struct nd_audio_queue *q) {q->count=0;}
static void remove_at(struct nd_audio_queue *q,unsigned index) {
    q->count--;memmove(&q->items[index],&q->items[index+1],(q->count-index)*sizeof(q->items[0]));
}
int nd_audio_queue_push(struct nd_audio_queue *q,const char *path,unsigned priority,uint32_t event_id) {
    size_t length=0;
    if(!path || priority>ND_AUDIO_ALERT) {q->rejected++;return 0;}
    while(length<ND_AUDIO_PATH_CAPACITY && path[length])length++;
    if(!length || length==ND_AUDIO_PATH_CAPACITY) {q->rejected++;return 0;}
    struct nd_audio_request incoming={.event_id=event_id,.priority=priority};
    memcpy(incoming.path,path,length+1);
    if(event_id)for(unsigned i=0;i<q->count;i++)if(q->items[i].event_id==event_id) {
        if(incoming.priority<q->items[i].priority)incoming.priority=q->items[i].priority;
        q->items[i]=incoming;q->merged++;return 1;
    }
    unsigned limit=priority==ND_AUDIO_ALERT?ND_AUDIO_QUEUE_CAPACITY:ND_AUDIO_QUEUE_CAPACITY-2;
    if(q->count>=limit) {
        unsigned lowest=q->count;
        for(unsigned i=0;i<q->count;i++)
            if(q->items[i].priority<priority && (lowest==q->count || q->items[i].priority<q->items[lowest].priority))lowest=i;
        if(lowest==q->count) {q->rejected++;return 0;}
        remove_at(q,lowest);q->evicted++;
    }
    q->items[q->count++]=incoming;if(q->count>q->peak)q->peak=q->count;return 1;
}
int nd_audio_queue_pop(struct nd_audio_queue *q,struct nd_audio_request *out) {
    if(!q->count || !out)return 0;
    unsigned best=0;
    for(unsigned i=1;i<q->count;i++)if(q->items[i].priority>q->items[best].priority)best=i;
    *out=q->items[best];remove_at(q,best);return 1;
}

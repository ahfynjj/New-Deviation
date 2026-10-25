#include "touch_input.h"
int tx15_touch_map_point(const struct tx15_touch_map *m,unsigned rx,unsigned ry,uint16_t *x,uint16_t *y){
    if(!m || !x || !y || m->width<2 || m->height<2 || m->width>4096 || m->height>4096
        || rx>=m->width || ry>=m->height || m->flags>7)return -1;
    unsigned w=m->width,h=m->height;
    if(m->flags&TX15_TOUCH_SWAP){unsigned n=rx;rx=ry;ry=n;n=w;w=h;h=n;}
    unsigned px=rx*479u/(w-1u),py=ry*319u/(h-1u);
    *x=(uint16_t)((m->flags&TX15_TOUCH_FLIP_X)?479u-px:px);
    *y=(uint16_t)((m->flags&TX15_TOUCH_FLIP_Y)?319u-py:py);return 0;
}
void tx15_touch_input_reset(struct tx15_touch_input *s){*s=(struct tx15_touch_input){0};}
static void enqueue(struct tx15_touch_input *s,unsigned kind,uint32_t now){
    if(s->count==8){
        s->head=s->count=s->active=0;s->blocked=1;kind=TX15_TOUCH_CANCEL;
    }
    s->queue[(s->head+s->count)%8]=(struct tx15_touch_event){now,s->x,s->y,(uint8_t)kind};
    s->count++;
}
void tx15_touch_input_cancel(struct tx15_touch_input *s,uint32_t now){
    s->blocked=1;
    if(s->active){s->active=0;enqueue(s,TX15_TOUCH_CANCEL,now);}
}
void tx15_touch_input_frame(struct tx15_touch_input *s,const struct tx15_touch_map *m,
        unsigned count,unsigned id,unsigned rx,unsigned ry,uint32_t now){
    if(!count){
        if(s->active){s->active=0;enqueue(s,TX15_TOUCH_UP,now);}
        s->blocked=0;return;
    }
    uint16_t x,y;
    if(count!=1 || id>15 || tx15_touch_map_point(m,rx,ry,&x,&y)){
        tx15_touch_input_cancel(s,now);return;
    }
    if(s->blocked)return;
    if(s->active && s->id!=id){tx15_touch_input_cancel(s,now);return;}
    if(!s->active){
        s->active=1;s->id=(uint8_t)id;s->x=x;s->y=y;enqueue(s,TX15_TOUCH_DOWN,now);
    }else{
        unsigned dx=x>s->x?x-s->x:s->x-x,dy=y>s->y?y-s->y:s->y-y;
        if(dx>=2 || dy>=2){s->x=x;s->y=y;enqueue(s,TX15_TOUCH_MOVE,now);}
    }
}
int tx15_touch_input_take(struct tx15_touch_input *s,struct tx15_touch_event *e){
    if(!s->count || !e)return 0;
    *e=s->queue[s->head];s->head=(s->head+1)%8;s->count--;return 1;
}

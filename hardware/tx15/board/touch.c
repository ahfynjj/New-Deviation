/* Reads known GT911 register protocol only after strict identity detection.
 * One <=4-byte shared-I2C transaction per step. No GPIO/reset/config writes.
 * GT911 register facts checked against vendor programming guide and Espressif
 * esp_lcd_touch_gt911. Independent native implementation, GPL-3.0-or-later. */
#include "touch.h"
#include "i2c_bus.h"
struct tx15_touch_report tx15_touch_report;
static struct tx15_touch_input touch_input;
static struct tx15_touch_map touch_map;
static uint8_t point[8],pending_count,candidate;
static uint32_t due,progress;
enum {IDENTITY,RESOLUTION,STATUS,POINT_A,POINT_B,ACK};
static const uint8_t addresses[2]={0x5d,0x14};
static int admitted(int result,uint32_t now){
    tx15_touch_report.last_result=result;
    if(result==TX15_I2C_BUSY || result==TX15_I2C_UNAVAILABLE){
        tx15_touch_report.bus_status=0xffffffffu;tx15_touch_report.busy++;
        if((uint32_t)(now-progress)>=500u){
            tx15_touch_input_cancel(&touch_input,now);tx15_touch_report.state=TX15_TOUCH_ERROR;
        }
        return 0;
    }
    tx15_touch_report.bus_status=tx15_i2c_report.status;
    if(result==TX15_I2C_IO)tx15_touch_report.errors++;
    progress=now;return 1;
}
static void next_candidate(void){
    if(++candidate>=2)tx15_touch_report.state=TX15_TOUCH_NOT_FOUND;
    else tx15_touch_report.stage=IDENTITY;
}
void tx15_touch_start(uint32_t now){
    tx15_touch_report=(struct tx15_touch_report){0};
    tx15_touch_input_reset(&touch_input);touch_map=(struct tx15_touch_map){0};
    candidate=pending_count=0;due=progress=now;
    tx15_touch_report.state=TX15_TOUCH_PROBING;tx15_touch_report.bus_status=0xffffffffu;
}
void tx15_touch_stop(uint32_t now){
    tx15_touch_input_cancel(&touch_input,now);tx15_touch_report.state=TX15_TOUCH_OFF;
    tx15_touch_report.points=0;
}
void tx15_touch_set_map(unsigned flags,uint32_t now){
    flags&=7u;
    if(touch_map.flags==flags)return;
    if(touch_input.active)tx15_touch_input_cancel(&touch_input,now);
    touch_map.flags=flags;tx15_touch_report.map_flags=flags;
}
void tx15_touch_cycle_map(uint32_t now){
    tx15_touch_set_map(touch_map.flags+1u,now);
}
void tx15_touch_require_release(uint32_t now){
    tx15_touch_input_cancel(&touch_input,now);
}
int tx15_touch_take(struct tx15_touch_event *event){
    if(!tx15_touch_input_take(&touch_input,event))return 0;
    tx15_touch_report.event=event->kind;return 1;
}
void tx15_touch_poll(uint32_t now){
    if((tx15_touch_report.state!=TX15_TOUCH_PROBING && tx15_touch_report.state!=TX15_TOUCH_READY)
        || (int32_t)(now-due)<0)return;
    due=now+1u;
    uint8_t data[4];int result;
    unsigned stage=tx15_touch_report.stage;
    if(stage==IDENTITY){
        tx15_touch_report.address=addresses[candidate];
        result=tx15_i2c_read(addresses[candidate],0x8140,2,data,4);
        if(!admitted(result,now))return;
        if(result){next_candidate();return;}
        for(unsigned i=0;i<4;i++)tx15_touch_report.product[i]=(char)data[i];
        if(data[0]!='9' || data[1]!='1' || data[2]!='1' || (data[3]!=0 && data[3]!=' ')){
            tx15_touch_report.last_result=TX15_I2C_INVALID;next_candidate();return;
        }
        tx15_touch_report.stage=RESOLUTION;return;
    }
    unsigned address=tx15_touch_report.address;
    if(stage==RESOLUTION)result=tx15_i2c_read(address,0x8048,2,data,4);
    else if(stage==STATUS)result=tx15_i2c_read(address,0x814e,2,data,1);
    else if(stage==POINT_A)result=tx15_i2c_read(address,0x814f,2,point,4);
    else if(stage==POINT_B)result=tx15_i2c_read(address,0x8153,2,point+4,4);
    else {data[0]=0;result=tx15_i2c_write(address,0x814e,2,data,1);}
    if(!admitted(result,now))return;
    if(result){
        tx15_touch_input_cancel(&touch_input,now);tx15_touch_report.state=TX15_TOUCH_ERROR;return;
    }
    if(stage==RESOLUTION){
        touch_map.width=(uint16_t)(data[0]|((unsigned)data[1]<<8));
        touch_map.height=(uint16_t)(data[2]|((unsigned)data[3]<<8));
        tx15_touch_report.raw_width=touch_map.width;tx15_touch_report.raw_height=touch_map.height;
        if(touch_map.width<2 || touch_map.height<2 || touch_map.width>4096 || touch_map.height>4096){
            tx15_touch_report.state=TX15_TOUCH_ERROR;tx15_touch_report.last_result=TX15_I2C_INVALID;return;
        }
        /* Trial orientation only; never used to dispatch parameter clicks. */
        touch_map.flags=touch_map.width<touch_map.height?TX15_TOUCH_SWAP:0;
        tx15_touch_report.map_flags=touch_map.flags;
        tx15_touch_report.state=TX15_TOUCH_READY;tx15_touch_report.stage=STATUS;due=now+10;return;
    }
    if(stage==STATUS){
        if(!(data[0]&0x80u)){due=now+10;return;} /* No new report is NOT release. */
        pending_count=data[0]&15u;
        if(data[0]&0x60u)pending_count=6; /* palm/unknown status: cancel */
        tx15_touch_report.stage=pending_count==1?POINT_A:ACK;return;
    }
    if(stage==POINT_A){tx15_touch_report.stage=POINT_B;return;}
    if(stage==POINT_B){tx15_touch_report.stage=ACK;return;}
    /* Consume only after the status ACK succeeded. Error cannot become UP. */
    if(pending_count==1){
        tx15_touch_report.id=point[0];
        tx15_touch_report.raw_x=(uint16_t)(point[1]|((unsigned)point[2]<<8));
        tx15_touch_report.raw_y=(uint16_t)(point[3]|((unsigned)point[4]<<8));
        uint16_t x,y;
        if(!tx15_touch_map_point(&touch_map,tx15_touch_report.raw_x,tx15_touch_report.raw_y,&x,&y)){
            tx15_touch_report.x=x;tx15_touch_report.y=y;
        }
    }
    tx15_touch_report.points=pending_count;
    tx15_touch_input_frame(&touch_input,&touch_map,pending_count,tx15_touch_report.id,
        tx15_touch_report.raw_x,tx15_touch_report.raw_y,now);
    tx15_touch_report.frames++;tx15_touch_report.stage=STATUS;due=now+10;
}

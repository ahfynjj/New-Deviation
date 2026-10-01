/* New Deviation TX15; GPL-3.0-or-later.
 * Pin facts: fixed TX15 board definition used by the display driver.
 * No EXTI/timer configuration; GPIOs are covered by existing session recovery.
 */
#include "inputs.h"
#define R(a) (*(volatile uint32_t *)(a))
static struct tx15_input_filter filter;
static volatile unsigned pending;
static volatile int movement;
static void input(unsigned p,unsigned pin) {
    uint32_t b=0x58020000u+p*0x400u,s=pin*2;
    R(b+12)=(R(b+12)&~(3u<<s))|(1u<<s);
    R(b)&=~(3u<<s);
}
static unsigned keys(void) {
    unsigned a=R(0x58020010u),g=R(0x58021810u);
    return ((g&(1u<<12))?0:TX15_ENTER)|((g&8)?0:TX15_EXIT)
        |((g&128)?0:TX15_PREV)|((a&256)?0:TX15_NEXT);
}
static unsigned phase(void) {
    return ((R(0x58022010u)>>7)&1)|((R(0x58022410u)>>7)&2);
}
void tx15_inputs_init(void) {
    R(0x580244e0u)|=0x341; (void)R(0x580244e0u);
    input(6,12); input(6,3); input(6,7); input(0,8); input(8,7); input(9,8);
    pending=0; movement=0; tx15_input_filter_init(&filter,keys(),phase());
}
void tx15_inputs_tick(void) {
    struct tx15_input_event e=tx15_input_filter_step(&filter,keys(),phase());
    pending|=e.pressed;
    if((e.rotation>0 && movement<32)||(e.rotation<0 && movement>-32)) movement+=e.rotation;
}
struct tx15_input_event tx15_inputs_take(void) {
    unsigned mask; __asm volatile("mrs %0, primask\ncpsid i":"=r"(mask)::"memory");
    struct tx15_input_event e={pending,movement}; pending=0; movement=0;
    __asm volatile("msr primask, %0"::"r"(mask):"memory");
    return e;
}

unsigned tx15_inputs_state(void) { return filter.stable; }

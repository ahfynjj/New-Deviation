/* RAM application stage, after verified bootstrap. */
.syntax unified
.cpu cortex-m7
.thumb
.section .isr_vector,"a",%progbits
.balign 1024
.global app_vectors
app_vectors:
 .word _stack_top
 .word App_Reset
 .rept 13
 .word App_Fault
 .endr
 .word SysTick_Handler
 .rept 71
 .word App_Fault
 .endr
 .word USART6_IRQHandler
 .rept 88
 .word App_Fault
 .endr
.section .text.App_Reset,"ax",%progbits
.global App_Reset
.type App_Reset,%function
.thumb_func
App_Reset:
 cpsid i
 ldr r0, =_stack_bottom
 ldr r1, =_stack_top
 movs r2, #0
 movs r3, #0
1: strd r2,r3,[r0],#8
 cmp r0,r1
 blo 1b
 ldr r0, =_stack_top
 msr msp,r0
 msr control,r2
 msr basepri,r2
 msr faultmask,r2
 ldr r0, =_bss_start
 ldr r1, =_bss_end
2: cmp r0,r1
 bhs 3f
 strd r2,r3,[r0],#8
 b 2b
3: ldr r0, =0xe000ed08
 ldr r1, =app_vectors
 str r1,[r0]
 dsb
 isb
 bl App_Main
 b .

/* New Deviation Cortex-M7 RAM diagnostic startup; GPL-3.0-or-later. */
.syntax unified
.cpu cortex-m7
.thumb

.section .isr_vector,"a",%progbits
.balign 1024
.global probe_vectors
probe_vectors:
    .word _stack_top
    .word Reset_Handler
    .rept 13
    .word Probe_Fault
    .endr
    .word SysTick_Handler
    /* H750 IRQs end at 149; keep 160 entries, including reserved slots. */
    .rept 160
    .word Probe_Fault
    .endr

.section .text.Reset_Handler,"ax",%progbits
.global Reset_Handler
.type Reset_Handler,%function
.thumb_func
Reset_Handler:
    cpsid i
#ifdef TX15_BOOT_EARLY_SUPPLY
    /* Cold-start bench only; legacy RAM diagnostics retain their exact path. */
    bl tx15_boot_supply_early
    cmp r0,#0
    bne .Learly_supply_failed
#endif
    ldr r0, =_stack_bottom
    ldr r1, =_stack_top
    movs r2, #0
    movs r3, #0
    /* Initialize whole aligned AXI ECC doublewords before any C stack use. */
1:  strd r2, r3, [r0], #8
    cmp r0, r1
    blo 1b
    ldr r0, =_stack_top
    msr msp, r0
    msr control, r2
    msr basepri, r2
    msr faultmask, r2
    isb
    ldr r0, =0xe000ed08
    ldr r1, =probe_vectors
    str r1, [r0]
    dsb
    isb
    /* Disable and clear external IRQs before enabling only SysTick in C. */
    ldr r0, =0xe000e180
    ldr r1, =0xe000e280
    mvn r2, #0
    movs r3, #8
2:  str r2, [r0], #4
    str r2, [r1], #4
    subs r3, #1
    bne 2b
    ldr r0, =_bss_start
    ldr r1, =_bss_end
    movs r2, #0
    movs r3, #0
3:  cmp r0, r1
    bhs 4f
    strd r2, r3, [r0], #8
    b 3b
4:  ldr r0, =_mailbox_start
    ldr r1, =_mailbox_end
5:  strd r2, r3, [r0], #8
    cmp r0, r1
    blo 5b
    dsb
    bl Probe_Main
    b .
#ifdef TX15_BOOT_EARLY_SUPPLY
.Learly_supply_failed:
    /* Run* RAM may be unwritable; no C/mailbox/stack access on this path. */
    b .Learly_supply_failed
#endif
.size Reset_Handler, .-Reset_Handler

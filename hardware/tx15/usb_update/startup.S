/* Native internal-Flash reset entry; supply before all RAM/stack accesses. */
.syntax unified
.cpu cortex-m7
.thumb
.section .isr_vector,"a",%progbits
.balign 1024
.global boot_vectors
boot_vectors:
 .word _stack_top
 .word Boot_Reset
 .rept 13
 .word Boot_Fault
 .endr
 .word SysTick_Handler
 .rept 101
 .word Boot_Fault
 .endr
 .word OTG_FS_IRQHandler
 .rept 58
 .word Boot_Fault
 .endr
.section .text.Boot_Reset,"ax",%progbits
.global Boot_Reset
.type Boot_Reset,%function
.thumb_func
Boot_Reset:
 cpsid i
 bl tx15_boot_supply_early
 cmp r0,#0
 bne .Lfailed
 ldr r0,=_stack_bottom
 ldr r1,=_stack_top
 movs r2,#0
 movs r3,#0
.Lstack:
 strd r2,r3,[r0],#8
 cmp r0,r1
 blo .Lstack
 ldr r0,=_data_start
 ldr r1,=_data_end
 ldr r4,=_data_load
.Ldata:
 cmp r0,r1
 bhs .Lbss_prepare
 ldrd r2,r3,[r4],#8
 strd r2,r3,[r0],#8
 b .Ldata
.Lbss_prepare:
 movs r2,#0
 movs r3,#0
 ldr r0,=_bss_start
 ldr r1,=_bss_end
.Lbss:
 cmp r0,r1
 bhs .Lmailbox_prepare
 strd r2,r3,[r0],#8
 b .Lbss
.Lmailbox_prepare:
 ldr r0,=_mailbox_start
 ldr r1,=_mailbox_end
.Lmailbox:
 strd r2,r3,[r0],#8
 cmp r0,r1
 blo .Lmailbox
 ldr r0,=_stack_top
 msr msp,r0
 msr control,r2
 msr basepri,r2
 msr faultmask,r2
 ldr r0,=0xe000ed08
 ldr r1,=boot_vectors
 str r1,[r0]
 dsb
 isb
 bl Boot_Main
.Lfailed:
 b .Lfailed
.size Boot_Reset,.-Boot_Reset
.section .text.tx15_boot_jump,"ax",%progbits
.global tx15_boot_jump
.type tx15_boot_jump,%function
.thumb_func
tx15_boot_jump:
 /* r0=verified entry. No return and no stack access after MSP replacement. */
 cpsid i
 mov r1,r0
 movs r2,#0
 msr control,r2
 msr basepri,r2
 msr faultmask,r2
 ldr r0,=0x24010000
 ldr r3,=0xe000ed08
 str r0,[r3]
 ldr r0,[r0]
 dsb
 isb
 msr msp,r0
 bx r1
.size tx15_boot_jump,.-tx15_boot_jump

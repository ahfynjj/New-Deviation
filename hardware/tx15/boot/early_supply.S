/* Stackless H750 POR supply finalization, before every RAM write.
 * Independent New Deviation startup; GPL-3.0-or-later. ST RM0433 Run* rules. */
.syntax unified
.cpu cortex-m7
.thumb
.section .text.tx15_boot_supply_early,"ax",%progbits
.global tx15_boot_supply_early
.type tx15_boot_supply_early,%function
.thumb_func
tx15_boot_supply_early:
 cpsid i
 /* Assert power hold without a C prologue or AXI/DTCM stack access. */
 ldr r0,=0x580244e0
 ldr r1,[r0]
#ifdef TX15_USB_UPDATE
 orr r1,r1,#0x180 /* GPIOH hold and GPIOI status LED */
#else
 orr r1,r1,#0x80
#endif
 str r1,[r0]
 ldr r1,[r0]
 ldr r0,=0x58021c18
 movw r1,#0x1000
 str r1,[r0]
 ldr r0,=0x58021c04
 ldr r1,[r0]
 bic r1,r1,#0x1000
 str r1,[r0]
 ldr r0,=0x58021c00
 ldr r1,[r0]
 bic r1,r1,#0x03000000
 orr r1,r1,#0x01000000
 str r1,[r0]
#ifdef TX15_USB_UPDATE
 /* Immediate blue acknowledgement AFTER PH12 hold, BEFORE any stack, RAM,
  * PLL/SDRAM or LCD wait. TX15 status RGB: PI8 red, PI10 blue, PI11 green.
  * Preload color first; preserve PI7 encoder and PI9 LCD command data. */
 ldr r0,=0x58022018
 ldr r1,=0x09000400
 str r1,[r0]
 ldr r0,=0x58022004
 ldr r1,[r0]
 bic r1,r1,#0xd00
 str r1,[r0]
 ldr r0,=0x58022008
 ldr r1,[r0]
 bic r1,r1,#0xf30000
 str r1,[r0]
 ldr r0,=0x5802200c
 ldr r1,[r0]
 bic r1,r1,#0xf30000
 str r1,[r0]
 ldr r0,=0x58022000
 ldr r1,[r0]
 bic r1,r1,#0xf30000
 orr r1,r1,#0x510000
 str r1,[r0]
#endif
 /* Only finalize an already enabled LDO; never switch away from bypass. */
 ldr r0,=0x5802480c
 ldr r1,[r0]
 and r2,r1,#3
 cmp r2,#2
 bne .Lbad_supply
 tst r1,#4
 beq .Lcheck_supply
 bic r1,r1,#4
 str r1,[r0]
.Lcheck_supply:
 ldr r1,[r0]
 and r1,r1,#7
 cmp r1,#2
 bne .Lbad_supply
 ldr r0,=0x58024804
 ldr r2,=1000000
.Lwait_supply:
 ldr r1,[r0]
 tst r1,#0x2000
 bne .Lsupply_ready
 subs r2,r2,#1
 bne .Lwait_supply
 movs r0,#5
 bx lr
.Lbad_supply:
 movs r0,#1
 bx lr
.Lsupply_ready:
 dsb
 movs r0,#0
 bx lr
.size tx15_boot_supply_early,.-tx15_boot_supply_early
.ltorg

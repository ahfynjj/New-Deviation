/* AXI SRAM only. No internal/QSPI flash load regions. */
ENTRY(Reset_Handler)
MEMORY {
    CODE (rwx) : ORIGIN = 0x24000000, LENGTH = 56K
    MAILBOX (rw) : ORIGIN = 0x2400e000, LENGTH = 4K
    STACK (rw) : ORIGIN = 0x2400f000, LENGTH = 4K
}
SECTIONS {
    .isr_vector : { KEEP(*(.isr_vector)) } > CODE
    .text : { *(.text*) *(.rodata*) } > CODE
    .data : { *(.data*) } > CODE
    .bss (NOLOAD) : {
        . = ALIGN(8); _bss_start = .;
        *(.bss*) *(COMMON)
        . = ALIGN(8); _bss_end = .;
    } > CODE
    .mailbox (NOLOAD) : {
        _mailbox_start = .; KEEP(*(.mailbox)) _mailbox_end = .;
    } > MAILBOX
    .stack (NOLOAD) : {
        _stack_bottom = .; . += LENGTH(STACK); _stack_top = .;
    } > STACK
    /DISCARD/ : { *(.comment) *(.note*) *(.ARM.exidx*) *(.ARM.extab*) }
}
ASSERT(ADDR(.isr_vector) == 0x24000000, "vector base moved")
ASSERT(SIZEOF(.isr_vector) == 704, "unexpected vector count")
ASSERT(SIZEOF(.mailbox) == 128, "mailbox ABI changed")
ASSERT((_bss_start % 8) == 0 && (_bss_end % 8) == 0, "BSS ECC alignment")
ASSERT((_mailbox_start % 8) == 0 && (_mailbox_end % 8) == 0, "mailbox ECC alignment")
ASSERT(_bss_end <= ORIGIN(MAILBOX), "code/data overlap mailbox")

/* External framebuffer is runtime-owned, never a load/zero-init segment. */
_framebuffer_start = 0xd0000000;
_framebuffer_end = _framebuffer_start + 320K;
ASSERT(307200 <= 320K, "framebuffer reservation too small")

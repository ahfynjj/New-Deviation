ENTRY(Boot_Reset)
MEMORY {
 FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 128K
 RAM (rw) : ORIGIN = 0x24000000, LENGTH = 56K
 MAILBOX (rw) : ORIGIN = 0x2400e000, LENGTH = 4K
 STACK (rw) : ORIGIN = 0x2400f000, LENGTH = 4K
}
SECTIONS {
 .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
 .text : { *(.text*) *(.rodata*) . = ALIGN(8); } > FLASH
 .data : { . = ALIGN(8); _data_start = .; *(.data*) . = ALIGN(8); _data_end = .; } > RAM AT> FLASH
 _data_load = LOADADDR(.data);
 .bss (NOLOAD) : { . = ALIGN(8); _bss_start = .; *(.bss*) *(COMMON) . = ALIGN(8); _bss_end = .; } > RAM AT> RAM
 .mailbox (NOLOAD) : { _mailbox_start = .; KEEP(*(.mailbox)) _mailbox_end = .; } > MAILBOX
 .stack (NOLOAD) : { _stack_bottom = .; . += LENGTH(STACK); _stack_top = .; } > STACK
 /DISCARD/ : { *(.comment) *(.note*) *(.ARM.exidx*) *(.ARM.extab*) }
}
ASSERT(ADDR(.isr_vector)==0x08000000 && SIZEOF(.isr_vector)==704,"boot vectors")
ASSERT(SIZEOF(.mailbox)==128,"handoff ABI")
ASSERT((_bss_start%8)==0 && (_bss_end%8)==0 && (_data_start%8)==0 && (_data_end%8)==0,"ECC alignment")
ASSERT(_bss_end<=0x2400e000,"boot RAM overlaps handoff")

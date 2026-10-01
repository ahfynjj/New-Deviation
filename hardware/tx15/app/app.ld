ENTRY(App_Reset)
MEMORY {
 CODE (rwx) : ORIGIN = 0x24010000, LENGTH = 432K
 STACK (rw) : ORIGIN = 0x2407c000, LENGTH = 16K
 RESOURCE (r) : ORIGIN = 0xd0080000, LENGTH = 512K
}
SECTIONS {
 .isr_vector : { KEEP(*(.isr_vector)) } > CODE
 .text : { *(.text*) *(.rodata*) } > CODE
 .data : { *(.data*) } > CODE
 .bss (NOLOAD) : { . = ALIGN(8); _bss_start = .; *(.bss*) *(COMMON) . = ALIGN(8); _bss_end = .; } > CODE
 .resources : { *(.resources*) } > RESOURCE
 .stack (NOLOAD) : { _stack_bottom = .; . += LENGTH(STACK); _stack_top = .; } > STACK
 /DISCARD/ : { *(.comment) *(.note*) *(.ARM.exidx*) *(.ARM.extab*) }
}
ASSERT(SIZEOF(.isr_vector)==704,"vectors")
ASSERT(_bss_end<=0x2407c000,"code/BSS overlaps stack")

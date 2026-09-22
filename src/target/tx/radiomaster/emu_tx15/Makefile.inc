# Host-only target: original Deviation wide-screen pages, no MCU/flash rules.
SCREENSIZE := 320x240x16
FILESYSTEMS := common base_fonts 320x240x16 tx15
FONTS = filesystem/$(FILESYSTEM)/media/15normal.fon \
        filesystem/$(FILESYSTEM)/media/23bold.fon
LANGUAGE := devo8

include target/drivers/mcu/emu/Makefile.inc
SRC_C := $(filter-out target/drivers/mcu/emu/channels.c,$(SRC_C))

ifdef BUILD_TARGET
$(TARGET).fs_wrapper: $(LAST_MODEL)
	perl -p -i -e 's/drawn_background=0/drawn_background=1/' filesystem/$(FILESYSTEM)/media/config.ini
endif

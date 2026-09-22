# Include the real target's object list and flags; do not glob stale objects.
include Makefile

$(ODIR)/tx15_model_test.o: ../utils/tests/tx15_model_test.c
	$(CC) $(CFLAGS) $(EXTRA_CFLAGS) -c $< -o $@

tx15-input-test.exe: $(OBJS) $(ODIR)/tx15_model_test.o
	$(CXX) -o $@ $^ $(LFLAGS) $(LFLAGS2) -Wl,--wrap=main

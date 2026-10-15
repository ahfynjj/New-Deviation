/* Continuous source movement detection; GPL-3.0-or-later. */
#ifndef TX15_KNOB_CAPTURE_H
#define TX15_KNOB_CAPTURE_H
/* 1000 calibrated units = 10 percentage points, or 5% of full travel. */
#define TX15_KNOB_CAPTURE_DELTA 1000
struct tx15_knob_capture {int baseline[2];unsigned seeded;};
/* Returns 1/2 for S1/S2. Invalid/rearmed samples establish a baseline. */
int tx15_knob_capture_step(struct tx15_knob_capture *,const int values[2],int valid,int armed);
#endif

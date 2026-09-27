# TX15 MAX native power support

The application and mixer remain native Deviation. This driver uses direct STM32
register accesses for two board signals, without an EdgeTX application dependency.

## Sources and observations

- ST RM0433 / STM32H750 CMSIS register definitions: RCC_AHB4ENR 0x580244E0,
  GPIOA 0x58020000, GPIOH 0x58021C00.
- Fixed EdgeTX reference, checked 2026-09-27:
  [TX15 hal.h at 19b50d967e6e579ac5a1b3bdb014b148a6b47491](https://github.com/EdgeTX/edgetx/blob/19b50d967e6e579ac5a1b3bdb014b148a6b47491/radio/src/targets/tx15/hal.h)
  defines PH12 power hold and PA4 power button.
  [Power semantics at the same commit](https://github.com/EdgeTX/edgetx/blob/19b50d967e6e579ac5a1b3bdb014b148a6b47491/radio/src/targets/common/arm/stm32/pwr_driver.cpp)
  confirm output-high hold and pull-up, active-low button.
- The user's TX15 MAX: PH12 push-pull high observed during normal operation;
  PA4 short-press high/low/high observed; debugger-driven PH12 maintains power
  after reset-halt and button release. See docs/tx15/bench-2026-09-27.md.

## Contract and boundaries

`tx15_power_init()` preserves unrelated GPIO/clock bits, preloads PH12's latch
high before switching to output, and configures PA4 as a pull-up input.
`tx15_power_status()` separately reports output mode, output latch, input level,
button configuration and current pressed state. It avoids unclocked GPIO reads.

Only call after verifying board identity; an STM32 family ID alone is insufficient.
Button state is raw, not debounced. There is no automatic shutdown, long-press
policy, power-off API, battery management or RF power change in this increment.
The debugger still supplies power hold during image loading. Native take-over
needs a separate test starting with PH12 output disabled while the button powers
the board. Cold power-on/bootloader integration remains a separate milestone.

# TX15 MAX 实机开发：RAM 启动诊断

2026-09-23：按用户要求停止模拟器功能开发，转入实机。原生 Deviation
应用、混控和 CRSF 路线保持不变。此处是实机驱动开发的诊断入口，尚不是
完整遥控器固件，不作为 SD 卡更新包，也不是显示/射频已工作的证明。

## 本批产物

```powershell
Set-Location 'D:\DEVI移植\deviation'
.\utils\build-tx15-hardware.ps1
python -m unittest discover -s utils/hardware/tests -v
```

产物在 `local/tx15-hardware/ram-probe/`：ELF、RAM 二进制、链接 map。
构建只调用交叉编译器和 ELF 检查器，不调用探针、不访问设备。
Arm GCC 8.2.1 编译 Cortex-M7 Thumb / soft-float，不依赖模拟器、HAL 或外部固件。
测试中的本机 C 编译器仅用于检查同一份时钟/CPU 状态判断逻辑，不是遥控器模拟器。

|内容|地址/范围|
|---|---|
|代码、向量、普通数据|0x24000000～0x2400DFFF|
|诊断数据|0x2400E000，80 字节；所在 4 KiB 保留|
|栈|0x2400F000～0x2400FFFF，初始 SP=0x24010000|

这些是 **STM32H750 芯片定义的 AXI SRAM 地址**，不是从其他遥控器固件
推导的分区。ELF 校验拒绝 Flash 地址、段重叠、非 Thumb 入口和错误栈/向量。
真正装入时仍要确认探针选择了正确芯片、实际文件与本批产物一致。

程序记录 CPUID、DBGMCU ID、RCC 时钟配置、cache/MPU 状态；只检查自身
2 KiB scratch 区的两组反码模式，然后启动 SysTick 和主循环计数器。
异常时记录异常号、CFSR/HFSR/MMFAR/BFAR。并未测试所有 RAM，更没有测试
SDRAM/QSPI。状态 3 只表示计时器已配置，必须观察两个计数器实际前进。

## 实机执行条件

2026-09-26：已通过 PWLINK2 Lite / CMSIS-DAP 完成首次板上身份/状态读取，见
[实机记录](bench-2026-09-26.md)。尚未执行复位暂停或 RAM 装载。
开始运行前要获得：主板/MCU 标记、确认过的 SWD 接点、探针型号，以及
复位和暂停 CPU 时仍能维持供电的方案。不能凭旧记录猜测焊盘或电源锁存引脚。

此程序**不配置电源保持 GPIO**。如果整机依赖正在运行的程序保持电源，
reset-halt 可能导致关机；先核实供电/复位路径。调试器的参考电压检测脚
不能默认当作整机电源使用。实机原始 Flash 与用户数据备份仍是后续持久
写入前的必要步骤。

执行前使用真实硬件调试器复位并暂停在原程序执行前；核对：

- 芯片确认为 STM32H750；DBGMCU 低 12 位 `0x450` 只表示一组 H7 型号，不能独自证明 H750。
- HSI64 已就绪、系统时钟为 HSI、HSI/CPU/AHB 分频为 1。
- I/D cache、MPU 关闭；处于特权 Thread 模式，无已运行的原程序/看门狗状态。
- AXI SRAM 可写、可执行；没有未查明的读保护/调试限制。

这些条件不满足时先停在调试器中定位。程序内部也会拒绝不支持的时钟和
CPU 状态，但检查发生在入口执行之后，不能替代装载前的核对。

冷启动还需核对 SRAM 的 ECC 初始化。启动代码以 8 字节对齐的 `STRD`
清零栈、BSS 和诊断区后才进入 C；但代码/向量本身先由调试器装载，仍需
验证调试器对 AXI SRAM 的写入、ECC 初始化和回读。仅构建成功不能证明
冷启动装载可靠；首次联调记录装载方式和相关错误状态。

确认条件后，用适配 PWLINK2 Lite 的 CMSIS-DAP 调试工具装载该 **RAM ELF**，将 PC 指向
`Reset_Handler`（Thumb 状态）、SP 指向 `_stack_top`，从复位状态运行。
本批不提供自动擦写/自动复位脚本；pyOCD 0.45.1 的 DP/AP 读访问已验证，完整 GDB/RAM 装载流程待验证。
ELF 装载后的调试会修改 RAM 和 CPU 状态，不能接着恢复原程序运行；结束
后完整断电重启恢复原启动流程。

## 读取运行证据

在硬件 GDB 会话里暂停后读取：

```gdb
x/20wx 0x2400e000
dump binary memory probe-before.bin 0x2400e000 0x2400e050
```

继续运行约一秒，再暂停并保存 `probe-after.bin`。不要在两次读取之间复位
或重新装载，也不要把旧 dump 混入本次结果。

```powershell
python utils/hardware/probe_report.py probe-after.bin --previous probe-before.bin
```

检查器要求正确 magic/version、状态 3、无错误、512 个 scratch 字已检查，
且中断和主循环计数都前进；单份记录、零计数、停滞和错误状态不能通过。
它只能分析给定文件，不能证明文件来自哪一台设备；保留探针日志、芯片
标记、文件 SHA256 和本次操作时间。

错误位：1=CPU 类型、2=芯片系列、4=时钟条件、8=cache/MPU、16=scratch RAM。
状态：1=入口，2=RAM 检查通过，3=计时启动，4=前提/内存错误，5=异常。

## 本批验证记录

Arm GCC 8.2.1 构建通过，text=1292 字节、data=0、BSS/诊断区/栈=6224 字节。
9 项自动测试通过：真实 ELF 与破坏后的布局、时钟/CPU 判断、诊断记录与
停滞/错误情况。反汇编确认对齐双字清零、MSP/VTOR 设置及中断入口。
独立评审未发现阻断性代码问题；冷启动 ECC/调试器装载仍列为板上核验项。
本批未改动 Deviation 应用源码，未重复开发或验收模拟器。

## 依据与下一步

- [ST AN5342：内部存储 ECC](https://www.st.com/resource/en/application_note/an5342--how-to-use-error-correction-code-ecc-management-for-internal-memories-protection-on-stm32-mcus-stmicroelectronics.pdf)：AXI SRAM 双字宽度及部分写入行为。
- [ST DS12556：STM32H750 数据手册](https://www.st.com/resource/en/datasheet/stm32h750vb.pdf)：AXI SRAM、内部振荡器及芯片资源。
- [ST RM0433](https://www.st.com/resource/en/reference_manual/rm0433-stm32h742-stm32h743753-and-stm32h750-value-line-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)：内存映射、RCC 和 DBGMCU。
- [ST 官方设备定义](https://github.com/STMicroelectronics/cmsis-device-h7/blob/master/Include/stm32h750xx.h)：核对寄存器位置、位定义和 IRQ 范围；查阅日期 2026-09-23，本批未复制该头文件代码。

顺序：SWD/芯片识别 → RAM 程序板上运行 → 电源保持/时钟 → 外部存储与内存
→ LCD/触摸 → ADC/开关 → 接入 Deviation 应用 → UART/DMA/CRSF/ELRS。
已经完成的模拟器保留为历史产物，不再作为实机开发的前置验收。

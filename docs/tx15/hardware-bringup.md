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

2026-09-27：PWLINK2 Lite / CMSIS-DAP 的按键辅助复位暂停、PH12 电源保持、
RAM 镜像回读与实际运行已通过，见 [实机记录](bench-2026-09-27.md)。
两次现场快照的中断/主循环计数均前进，2 KiB scratch 检查通过，未记录异常。
已用板上 SWD 丝印、探针型号及电子身份/容量核对基础调试路径；不要求为此拆板拍 MCU。
本机已验证复位时按住电源键，捕获暂停后由调试器设置 PH12 高，再松开按钮。
PA4 是已实测的低有效按钮输入。该流程尚不代表其他主板修订也已核实。

首次实机通过的是 V1，PH12 由调试器设置。当前 V2 在运行环境检查后调用
原生 `tx15_power_init()`，保持 PH12 高并读取 PA4。09-27 另做独立接管测试：
撤掉调试器 PH12 输出并清低锁存，V2 自行恢复输出高；松手后两次快照推进且
power_status=0x0F，用户确认结束后原固件显示正常。该证据独立于旧 V1 记录。
直接 reset-halt 曾导致整机掉电，需使用已验证的按键辅助流程。调试器的参考电压检测脚
不能默认当作整机电源使用。实机原始 Flash 与用户数据备份仍是后续持久
写入前的必要步骤。

执行前使用真实硬件调试器复位并暂停在原程序执行前；核对：

- 核心、芯片家族、电子资源与预期一致：本机 Cortex-M7 / DEV_ID=0x450 / Flash=128 KiB 与 H750 相符。完整封装料号未知；PH12/PA4 已有源码和实机证据，其他引脚仍须逐项核对。
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
本机已用 pyOCD 0.45.1 的受限本地脚本完成 RAM 装载，脚本绑定已审核镜像哈希和
探针，尚未整理为通用仓库工具。此路径不使用 Flash 算法，也没有验证 GDB 装载。
不能从测试 PC 直接继续原程序；本次在原固件复位入口保存上下文，测试结束
关闭测试 SysTick、恢复 VTOR/完整核心寄存器并读回核对后才继续原启动入口。
用户已确认屏幕恢复正常。其他未经验证的装载流程结束后仍需完整断电重启。

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

错误位：1=CPU 类型、2=芯片系列、4=时钟条件、8=cache/MPU、16=scratch RAM、32=电源初始化。
状态：1=入口，2=RAM 检查通过，3=计时启动，4=前提/内存错误，5=异常。

V2 mailbox 仍为 80 字节，最后一字由 reserved 改为 power_status：bit0=PH12 推挽输出、
bit1=输出锁存高、bit2=引脚读回高、bit3=PA4 上拉输入、bit4=按钮按下。
解码器兼容 V1；V2 的两份快照均须满足低四位为 1，版本混用不能通过。
按键读值尚未消抖，也没有关机策略。

## 本批验证记录

初版 Arm GCC 8.2.1 构建 text=1292 字节；加入电源驱动的 V2 为 1576 字节，
data=0、BSS/诊断区/栈=6224 字节。11 项自动测试通过：真实 ELF 与破坏后的布局、时钟/CPU 判断、诊断记录与
停滞/错误情况。反汇编确认对齐双字清零、MSP/VTOR 设置及中断入口。
新增驱动测试运行真实 C 代码、在 MMIO 边界替换寄存器，验证其他引脚保持、
时钟读回、置高后切换输出及电源/按钮状态的异常分支；不用于替代实机证明。
原诊断代码独立评审未发现阻断性代码问题；09-27 热复位装载、读回、RAM 执行
和原固件恢复通过。完全断电后的 ECC 初始化仍待单独验证。
本批未改动 Deviation 应用源码，未重复开发或验收模拟器。

## 依据与下一步

- [ST AN5342：内部存储 ECC](https://www.st.com/resource/en/application_note/an5342--how-to-use-error-correction-code-ecc-management-for-internal-memories-protection-on-stm32-mcus-stmicroelectronics.pdf)：AXI SRAM 双字宽度及部分写入行为。
- [ST DS12556：STM32H750 数据手册](https://www.st.com/resource/en/datasheet/stm32h750vb.pdf)：AXI SRAM、内部振荡器及芯片资源。
- [ST RM0433](https://www.st.com/resource/en/reference_manual/rm0433-stm32h742-stm32h743753-and-stm32h750-value-line-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)：内存映射、RCC 和 DBGMCU。
- [ST 官方设备定义](https://github.com/STMicroelectronics/cmsis-device-h7/blob/master/Include/stm32h750xx.h)：核对寄存器位置、位定义和 IRQ 范围；查阅日期 2026-09-23，本批未复制该头文件代码。

顺序：SWD/芯片识别 → RAM 程序板上运行 → 电源保持/时钟 → 外部存储与内存
→ LCD/触摸 → ADC/开关 → 接入 Deviation 应用 → UART/DMA/CRSF/ELRS。
已经完成的模拟器保留为历史产物，不再作为实机开发的前置验收。

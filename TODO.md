# New Deviation — TX15 原生移植工作状态

更新：2026-09-27。仓库：[ahfynjj/New-Deviation](https://github.com/ahfynjj/New-Deviation)。本地：`D:\DEVI移植\deviation`。
`origin` 为 New Deviation，`upstream` 为 DeviationTX；当前开发分支 `dev/tx15-hardware-bringup`，主分支 `main`。

## 方向

以 Deviation 为主工程，新增 TX15 MAX 原生适配，保留复杂混控及操作体系，优先内置 ELRS 和彩屏。2026-09-26 用户明确提出参考 EdgeTX 的 TX15 适配：可以查阅其板级引脚、驱动和启动顺序，应用、模型与混控仍保持原生 Deviation。

## 已完成

- [x] 用户确认设计、开发计划和原生路线。
- [x] 保留上游 Git 历史，同步初始源码和计划到 main。
- [x] 修复进程内 Git shell 路径，取回固定 libopencm3。
- [x] 建立 Windows/MSYS2 主机及 Arm 构建环境，提供包装脚本。
- [x] 修复测试基础设施，79 项 CuTest 和 8 项工具回归通过。
- [x] 原 DEVO8 固件及 Windows 模拟器编译通过。
- [x] 完成当前代码评审并修复发现的 lint 问题。
- [x] 记录 TX15 首轮硬件、内存和 Deviation 接口差距。
- [x] 新增独立 480×320 emu_tx15 主机目标；采用 Deviation 自有宽屏页面。
- [x] 修复 Windows 64 位配置指针截断；主界面、混控列表及曲线画面捕获通过。
- [x] 提供启动脚本，原占位输入版本模型保存在 local/tx15，独立于构建模板。
- [x] 79 项 CuTest、10 项工具回归及 lint 通过；旧模拟器构建/画面捕获通过。

- [x] 本批 79 项 CuTest、12 项工具测试、真实模型/六段复杂混控集成测试通过。
- [x] 本批 TX15 三页面捕获、DEVO8 模拟器/固件回归和 lint 通过；独立评审问题已修复。

## 当前实机开发增量

- [x] 停止模拟器功能开发和人工界面验收排期，已有成果保留。
- [x] 新增 STM32H750 RAM 诊断：向量/启动、局部内存检查、SysTick/主循环、异常寄存器记录。
- [x] 新增独立 Cortex-M7 构建、ELF 地址/向量/保留区检查和双快照解码工具。
- [x] Arm 交叉编译通过；9 项硬件工具/判断逻辑测试通过，完成独立代码评审。
- [x] 2026-09-26：PWLINK2 Lite / CMSIS-DAP 以 100 kHz 成功读取板上 Cortex-M7、DBGMCU 和运行状态，未暂停/复位或写入程序。见 [实机记录](docs/tx15/bench-2026-09-26.md)。
- [x] 电子容量为 128 KiB，与 H750 配置相符；内部 Flash 两次只读备份一致，保存在本地。无需为基础联调拆板拍 MCU。
- [x] 通过按键辅助 NRST、复位暂停和调试器 PH12 置高，验证松开按钮后核心保持暂停且 SWD 可读。
- [ ] 完全断电后的 RAM/ECC 初始化、自主电源保持及完整恢复方案仍待验证。
- [x] EdgeTX TX15 源码给出 PH12 电源保持、PA4 电源按钮；实机只读及按钮动作核对一致。
- [x] 09-26 后续实测 PA4 短按低电平约 0.531 秒；按住按钮时 NRST 拉低期间仍可读 CPUID，释放复位后原固件运行。
- [x] 09-27：调整复位期间的访问顺序后，reset-halt 与 PH12 接管通过；原固件恢复且用户确认屏幕正常。
- [x] 首次 RAM 诊断实机运行通过：镜像回读一致，2 KiB scratch 检查通过，同次运行的 ticks 264→589、loops 5665038→12583422，无记录异常。已恢复原固件，未写 Flash。见 [09-27 实机记录](docs/tx15/bench-2026-09-27.md)。
- [x] 新增原生 PH12/PA4 电源驱动和 V2 诊断状态，11 项检查通过；参考硬件源码已固定到 EdgeTX 提交 19b50d967e6e579ac5a1b3bdb014b148a6b47491。
- [x] 原生独立接管实测通过：PH12 从输入/锁存低由程序恢复输出高；按住时 power_status=31，松手后两次快照均为 15，ticks 2813→3139、loops 1146619→1279167；原固件恢复且用户确认屏幕正常。

## 下一步

2026-09-28 V5 增量：原生 SDRAM 32 MHz 初始化与前 64 KiB 读写诊断已实现，
诊断区扩展到 128 字节。24 项主机检查通过；独立审查发现的初始快照时钟恢复错误分支已修复并复核。
20:29 实机等待按键超时，未复位/写入目标，V5 实机结果待取得。完整 8 MiB 容量和长期保持未验证。

20:30 重新测试通过：前 64 KiB 的 32800 次比较全部一致，ticks 221→570、loops 121603→312231，
无记录异常；FMC/GPIO/时钟/核心上下文恢复无错误，用户确认屏幕正常。
证据：`docs/tx15/evidence/2026-09-28/sdram64k/`。下一步扩展到全地址范围及跨行/跨 bank 测试，
补上保持性检查，再进入显示帧缓冲；当前不能宣称整个 8 MiB 已验证。

当前新增：原生 HSI64→HSE48 时钟驱动、V3 RAM 诊断及退出时恢复 HSI 的检查；
交叉构建与 16 项硬件工具测试通过，独立评审未发现阻塞项。16:08 实机验证通过：
HSE 已选中，ticks 263→588、loops 80830→180053；恢复 HSI 和原固件后用户确认屏幕正常。
没有配置 PLL 或外部存储。下一阶段确定 PLL/总线目标频率并分步实测，再推进外部内存。

V4 增量：新增保守 PLL128 / AHB64 / APB32 档位、PLL 与分频读回及完整时钟恢复。
不修改 PWR/Flash，20 项检查通过。20:50 实机通过：两份完整 PLL/分频读回一致，
ticks 264→599、loops 140284→317452，无记录异常；原始 RCC 配置恢复一致，用户确认屏幕正常。
独立证据位于 `docs/tx15/evidence/2026-09-27/pll128/`。当前仍为暖复位 RAM 诊断。

1. 原生电源保持、PLL128 和 SDRAM 前 64 KiB 已实测通过；下一步扩大 SDRAM 地址覆盖并验证保持性，补齐器件型号/时序核对；关机策略/按键消抖仍未实现。
2. 把已验证的本地 bench 脚本整理为可复用且有保护检查的 RAM 装载工具，补上完全断电后的 SRAM/ECC 初始化验证。
3. 完成时钟、外部存储和内存驱动；外部 Flash/用户数据备份和完整恢复方案仍须补齐。
4. 接入 LCD/触摸、ADC/开关，逐项实机验收。
5. 接入 Deviation 应用与 CRSF/ELRS，逐步进行端到端验证。

持久写入前完成原始 Flash/用户数据备份和恢复路径验证。当前产物是临时 RAM 诊断，不能通过 SD 卡固件更新，也不能代表完整遥控器固件。

## 继续工作入口

[实机联调说明](docs/tx15/hardware-bringup.md) · [当前实现计划](docs/superpowers/plans/2026-09-23-tx15-hardware-bringup.md) · [接口差距](docs/tx15/porting-map.md) · [总体设计](docs/superpowers/specs/2026-09-21-tx15-native-design.md)

```powershell
Set-Location 'D:\DEVI移植\deviation'
.\utils\build-tx15-hardware.ps1
python -m unittest discover -s utils/hardware/tests -v
```

逐条检查退出码。产物位于 `local/tx15-hardware/ram-probe`；构建和测试不访问设备。
已完成的主机工作及命令见 [历史构建说明](docs/tx15/build.md) 和 [输入阶段计划](docs/superpowers/plans/2026-09-22-tx15-inputs.md)。DEVO8 产物仅是旧平台交叉编译基线，不能刷入 TX15。

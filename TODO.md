# New Deviation — TX15 原生移植工作状态

更新：2026-09-30。仓库：[ahfynjj/New-Deviation](https://github.com/ahfynjj/New-Deviation)。本地：`D:\DEVI移植\deviation`。
`origin` 为 New Deviation，`upstream` 为 DeviationTX；当前开发分支 `dev/tx15-hardware-bringup`，主分支 `main`。

## P3 当前进度（2026-10-01，代码已构建，未上板）

- 按快速计划推进真实摇杆→原 Deviation 混控。新增 ADC1 六路轮询采样、四轴/S1/S2输入映射、原校准数据归一化与端点限幅；无DMA、无射频。
- 已核对板级参考通道，新增ADC12退出复位/时钟恢复。36项工具/适配检查通过，ARM应用最终链接通过；上板前恢复审查未发现阻断问题；实机轴向、原始值、校准/混控尚待验收。
- 当前镜像仍为调试器临时RAM应用，不能直接刷入；USB更新/日志、持久安装与独立启动尚未实现。旧装载哈希继续阻止新镜像未经检查直接上板。

## P2 当前状态（2026-10-01，交互可用，参数修改验收并入P3）

- 原生 Deviation 主页面、模型/混控菜单已实机运行；ENTER与EXIT用户确认有效，顺时针按键掩码已修正，双向滚动有效。
- 最新实测 `local/reset-halt-power-20261001-153357.json`：ticks 28537→88591，loops 5466→17341，无Fault并恢复原固件。编码器无跳态；用户反馈两个方向仍两格移动一项，明确要求暂缓优化并继续推进。
- 模型编辑仅在RAM中，未验证参数修改对真实通道的效果，合并P3验收。P2不宣称完全通过；“两格一项”作为已知交互限制，不阻塞P3。
- 字体/图标只读资源433629字节；代码位于0x24010000，资源位于0xD0080000，栈16KiB。构建：`python utils/build-tx15-app.py`。

## P1 当前进度（2026-09-30）

- 已完成：独立输入驱动、20ms 按键消抖、滚轮解码，最小 ITEM 选择/进入/返回页；输入版构建和 29 项相关检查通过，P0 独立构建保留。
- 实机：输入版运行45秒，ticks 53→45106、心跳45次，无异常，恢复流程成功；日志 `local/reset-halt-power-20260930-222352.json`。
- 实机验收：用户确认滚轮一格一项、ENTER/EXIT/PAGE 全部正常，原界面恢复；P1 通过，无当前阻塞。
- 下一动作：P2 接入原生 Deviation 主页面和混控设置入口；需新增硬件目标（现有 tx15 应用目标仅为历史模拟器），接入 LCD、按钮、时钟和最小字体资源。构建输入版：`utils/build-tx15-display.ps1 -InputDemo`。

## P0 当前进度（2026-09-29）

- 已完成：P0 实机验收通过。横屏 NEW DEVIATION、红绿蓝色块、独立递增数字显示正常，用户确认恢复原界面；修正版连续运行约 20 秒、更新 20 次，无异常。编译/ELF 检查及 28 项相关检查通过。
- 当前阻塞：P0 无阻塞；当前仍是调试器装载的 RAM 演示程序，尚未实现独立开机或 Deviation 应用页面。
- 下一动作：P1 接入按键与滚轮，实现选择、确认、返回；沿用已验证的显示和恢复路径。
- 构建：`powershell -File utils/build-tx15-display.ps1 -Python D:/DEVI移植/tools/pyocd-venv/Scripts/python.exe`。镜像位于 `local/tx15-hardware/display-demo/`，仅限现有受控 RAM 装载流程，不是可刷入固件。

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

2026-09-28 用户调整优先级：以可见功能快速推进，停止把全容量 SDRAM/长期保持测试当作屏幕开发的前置任务。

当前已实测：原生电源保持、RAM 执行、PLL128、SDRAM 前 64 KiB及原固件恢复。完整应用、显示、实际输入与 ELRS 尚未接通。

执行计划：[TX15 快速推进计划](docs/superpowers/plans/2026-09-28-tx15-fast-visible-progress.md)。此计划覆盖旧计划的执行排序。

1. 下一轮只做屏幕出图：New Deviation 字样、色块和递增数字。仅补实际帧缓冲范围的必要读写检查。
2. 按键/滚轮操作，再接 Deviation 主页面与混控页面；触摸作为同阶段后续补充。
3. 真实摇杆输入进入 Deviation 混控并显示通道结果。
4. 打通内置 ELRS，使用接收端验证通道和断链行为。
5. 完成必要存储、备份/恢复与持久安装，验证脱离调试器启动和模型保存。

全容量/长时间内存验证、最高主频、模拟器、通用装载工具重构暂缓；只做直接阻塞上述功能的最小工作。
每阶段合并验证和记录，不默认多代理审查或重复跑全部检查。当前仍是 RAM 原型，不能作为 SD 卡更新固件。

## 继续工作入口

[实机联调说明](docs/tx15/hardware-bringup.md) · [当前实现计划](docs/superpowers/plans/2026-09-23-tx15-hardware-bringup.md) · [接口差距](docs/tx15/porting-map.md) · [总体设计](docs/superpowers/specs/2026-09-21-tx15-native-design.md)

```powershell
Set-Location 'D:\DEVI移植\deviation'
.\utils\build-tx15-hardware.ps1
python -m unittest discover -s utils/hardware/tests -v
```

逐条检查退出码。产物位于 `local/tx15-hardware/ram-probe`；构建和测试不访问设备。
已完成的主机工作及命令见 [历史构建说明](docs/tx15/build.md) 和 [输入阶段计划](docs/superpowers/plans/2026-09-22-tx15-inputs.md)。DEVO8 产物仅是旧平台交叉编译基线，不能刷入 TX15。

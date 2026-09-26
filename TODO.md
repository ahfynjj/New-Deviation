# New Deviation — TX15 原生移植工作状态

更新：2026-09-23。仓库：[ahfynjj/New-Deviation](https://github.com/ahfynjj/New-Deviation)。本地：`D:\DEVI移植\deviation`。
`origin` 为 New Deviation，`upstream` 为 DeviationTX；当前开发分支 `dev/tx15-hardware-bringup`，主分支 `main`。

## 方向

以 Deviation 为主工程，新增 TX15 MAX 原生适配，保留复杂混控及操作体系，优先内置 ELRS 和彩屏。按用户最新要求，开发不再考虑 EdgeTX；除非用户明确提出需要。

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
- [ ] 确认 MCU 完整丝印、NRST 控制与复位供电保持；冷启动 RAM 装载与运行尚未验证。

## 下一步

1. 核对 TX15 MAX 主板修订、MCU 标记、SWD 接点和复位期间供电。
2. SWD 身份读取已通过；补充备份/恢复方案，确认 reset-halt 状态与调试器 SRAM/ECC 装载方式。
3. 装入 RAM 诊断，保存两次现场计数器、异常和探针记录。
4. 实现并验证电源保持、时钟、外部存储和内存，然后接入 LCD/触摸、ADC/开关。
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

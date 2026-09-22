# New Deviation — TX15 原生移植工作状态

更新：2026-09-23。仓库：[ahfynjj/New-Deviation](https://github.com/ahfynjj/New-Deviation)。本地：`D:\DEVI移植\deviation`。
`origin` 为 New Deviation，`upstream` 为 DeviationTX；当前开发分支 `dev/tx15-inputs`，主分支 `main`。

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

## 下一步

- [ ] 完成模拟器主界面、复杂混控、曲线和模型保存/加载的交互检查。
- [ ] 补齐 TX15 输入表、ADC/开关和启动装载流程审计。
- [ ] 实机阶段核实主板修订、调试接口及恢复路径；当前主机开发不以原固件信息为前提。
- [x] 细化 480×320 模拟目标首批计划。
- [x] 完成出厂控件的主机逻辑映射与旧输入名称拒绝规则；实机 GPIO/ADC 方向仍待确认。
- [x] 新增独立 local/tx15-native 模型目录，保留旧目录；严格加载失败恢复与保存保护。
- [x] 接入 28 个输入、键盘长按去重和 SF 松手/失焦复位；六段按键供高级混控使用。
- [ ] 完成整个界面的人工交互验收、六段主页控件和实体功能键导航；H7/TX15 与 ELRS 随后实施。

P1 模拟器及出厂输入配置已实现。P0 的实机核实项暂留实机阶段处理，不阻塞主机开发。没有 TX15 固件，没有执行设备写入。

## 继续工作入口

[构建命令](docs/tx15/build.md) · [验证记录](docs/tx15/baseline.md) · [开发计划](docs/superpowers/plans/2026-09-21-tx15-native-plan.md) · [硬件映射](docs/tx15/hardware-map.md) · [启动内存](docs/tx15/boot-memory.md) · [接口差距](docs/tx15/porting-map.md) · [来源许可](docs/tx15/source-provenance.md)

[TX15 模拟器运行说明与截图](docs/tx15/simulator.md) · [当前实现计划](docs/superpowers/plans/2026-09-22-tx15-inputs.md)

```powershell
Set-Location 'D:\DEVI移植\deviation'
.\utils\build-msys2.ps1 -Target emu_tx15
.\utils\run-tx15.ps1
.\utils\build-msys2.ps1 -Target tx15-test
.\utils\build-msys2.ps1 -Target runner
.\utils\build-msys2.ps1 -Target test
.\utils\build-msys2.ps1 -Target emu_devo8
.\utils\build-msys2.ps1 -Target devo8
.\utils\build-msys2.ps1 -Target lint
```

逐条执行并检查退出码，日志位于 `local/logs`。DEVO8 产物仅是交叉编译基线，不能刷入 TX15。

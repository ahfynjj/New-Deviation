# New Deviation — TX15 原生移植工作状态

更新：2026-09-22。仓库：[ahfynjj/New-Deviation](https://github.com/ahfynjj/New-Deviation)。本地：`D:\DEVI移植\deviation`。
`origin` 为 New Deviation，`upstream` 为 DeviationTX；当前开发分支 `dev/tx15-p0`，主分支 `main`。

## 方向

以 Deviation 为主工程，新增 TX15 MAX 原生适配，保留复杂混控及操作体系，优先内置 ELRS 和彩屏。EdgeTX 仅作硬件参考。

## 已完成

- [x] 用户确认设计、开发计划和原生路线。
- [x] 保留上游 Git 历史，同步初始源码和计划到 main。
- [x] 修复进程内 Git shell 路径，取回固定 libopencm3。
- [x] 建立 Windows/MSYS2 主机及 Arm 构建环境，提供包装脚本。
- [x] 修复测试基础设施，79 项 CuTest 和 8 项工具回归通过。
- [x] 原 DEVO8 固件及 Windows 模拟器编译通过。
- [x] 完成当前代码评审并修复发现的 lint 问题。
- [x] 记录 TX15 首轮硬件、内存和 Deviation 接口差距。

## 下一步

- [ ] 完成模拟器主界面、复杂混控、曲线和模型保存/加载的交互检查。
- [ ] 补齐 TX15 输入表、ADC/开关和启动装载流程审计。
- [ ] 核实实机 EdgeTX 精确版本、主板修订及恢复路径，制作恢复操作卡。
- [ ] 固定 P1 输入映射与旧模型兼容行为，细化 480×320 模拟目标计划。
- [ ] 开发 P1 模拟器；H7/TX15 和 ELRS 台架验证随后逐步实施。

P0 仍未全部完成，没有 TX15 固件，没有执行设备写入。

## 继续工作入口

[构建命令](docs/tx15/build.md) · [验证记录](docs/tx15/baseline.md) · [开发计划](docs/superpowers/plans/2026-09-21-tx15-native-plan.md) · [硬件映射](docs/tx15/hardware-map.md) · [启动内存](docs/tx15/boot-memory.md) · [接口差距](docs/tx15/porting-map.md) · [来源许可](docs/tx15/source-provenance.md)

```powershell
Set-Location 'D:\DEVI移植\deviation'
.\utils\build-msys2.ps1 -Target runner
.\utils\build-msys2.ps1 -Target test
.\utils\build-msys2.ps1 -Target emu_devo8
.\utils\build-msys2.ps1 -Target devo8
.\utils\build-msys2.ps1 -Target lint
```

逐条执行并检查退出码，日志位于 `local/logs`。DEVO8 产物仅是交叉编译基线，不能刷入 TX15。

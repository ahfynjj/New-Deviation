# New Deviation — TX15 原生移植工作状态

更新：2026-09-21。

项目仓库：https://github.com/ahfynjj/New-Deviation 。本地目录：`D:\DEVI移植\deviation`。
远端约定：`origin` 为 New Deviation；`upstream` 为 DeviationTX/deviation。开发主分支为 `main`。

## 方向

以 Deviation 为主工程，新增 TX15 原生适配，保留复杂混控及操作体系，优先内置 ELRS 和彩屏。EdgeTX 仅作为硬件实现参考。

## 文档入口

- [设计](docs/superpowers/specs/2026-09-21-tx15-native-design.md)
- [开发计划](docs/superpowers/plans/2026-09-21-tx15-native-plan.md)
- [基线检查](docs/tx15/baseline.md)

## 已完成

- [x] 确认原生 Deviation 路线。
- [x] 取回官方仓库并核对固定提交。
- [x] 审查构建入口、现有测试、CRSF 和 MCU 目录。
- [x] 记录环境缺口。
- [x] 写出设计稿、总体阶段和 P0 详细任务。
- [x] 项目定名 New Deviation，准备首次源码与计划同步。

## 当前与下一步

- [ ] 设计和计划文档审阅。
- [ ] 修复/绕开 Git shell 环境问题，取回固定 libopencm3。
- [ ] 建立可复现构建环境，运行原版测试、模拟器和固件构建。
- [ ] 审计 TX15 启动/内存/驱动及实机版本。
- [ ] 编制 P1/P2 详细实现计划，再新增模拟器和硬件目标。

当前没有可刷写的 TX15 固件；未执行任何设备写入。

## 启动方式

在 `D:\DEVI移植\deviation` 阅读上述文档，从计划 P0-1 第一个未完成项继续。现阶段没有经本机验证的构建命令；计划中的 POSIX 命令属于待执行步骤，不能报告为已通过。

# New Deviation

基于 [Deviation](https://github.com/DeviationTX/deviation) 开发的遥控器固件项目，首个目标是 **RadioMaster TX15 原生适配**。

项目仓库：[ahfynjj/New-Deviation](https://github.com/ahfynjj/New-Deviation)。

## 项目方向

- 以 Deviation 为主工程，保留其操作体系、复杂混控和模型配置语义。
- 新增 STM32H7 平台与 TX15 板级支持。
- 适配 TX15 的 480×320 彩屏、触摸和实体按键。
- 优先支持内置 ELRS，使用 CRSF 通信。
- 后续逐步加入新功能和更多遥控器目标。

EdgeTX 仅作为硬件定义与底层实现参考；本项目不在 EdgeTX 应用框架中运行。

## 当前状态

当前处于 P0：源码基线、开发环境和硬件接口审计阶段。

已建立 Windows 构建环境，通过 79 项主机测试和 8 项工具回归，完成原 DEVO8 固件及模拟器编译，并记录 TX15 首轮硬件接口审计。**尚未实现 TX15 目标，没有可刷写的 TX15 固件，也未进行实机验证。**

## 开发入口

- [设计与范围](docs/superpowers/specs/2026-09-21-tx15-native-design.md)
- [分阶段开发计划](docs/superpowers/plans/2026-09-21-tx15-native-plan.md)
- [工作状态与下一步](TODO.md)
- [源码及环境基线](docs/tx15/baseline.md)
- [Windows 构建命令](docs/tx15/build.md)
- [TX15 硬件映射](docs/tx15/hardware-map.md)
- [启动与内存审计](docs/tx15/boot-memory.md)

计划顺序：原版构建与测试 → 彩屏模拟目标 → H7/TX15 底层 → ELRS 闭环 → 首版完善。

## 源码与构建

保留 Deviation 上游 Git 历史，初始基线为 `330193b9a4185f6a2cdc3af90d654169cd210094`。libopencm3 使用原仓库固定的子模块提交。

```sh
git clone --recurse-submodules https://github.com/ahfynjj/New-Deviation.git
cd New-Deviation
```

已验证的构建入口和依赖见 [构建说明](docs/tx15/build.md)；不能把原 DEVO 固件刷入 TX15。

上游资料：[官网](https://www.deviationtx.com/)、[开发文档](https://www.deviationtx.com/wiki/development)、[Docker 构建说明](https://www.deviationtx.com/wiki/development/docker)。这些属于上游参考资料，不是本项目已验证的构建环境。

## 来源与许可

New Deviation 基于 DeviationTX/deviation，保留上游版权声明和 [许可证](LICENSE.TXT)。新增或复用的第三方代码需要保留各自来源和许可。本项目是独立开发项目，不表示获得 DeviationTX 或 RadioMaster 官方背书。

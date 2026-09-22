# New Deviation

基于 [Deviation](https://github.com/DeviationTX/deviation) 开发的遥控器固件项目，首个目标是 **RadioMaster TX15 原生适配**。

项目仓库：[ahfynjj/New-Deviation](https://github.com/ahfynjj/New-Deviation)。

## 项目方向

- 以 Deviation 为主工程，保留其操作体系、复杂混控和模型配置语义。
- 新增 STM32H7 平台与 TX15 板级支持。
- 适配 TX15 的 480×320 彩屏、触摸和实体按键。
- 优先支持内置 ELRS，使用 CRSF 通信。
- 后续逐步加入新功能和更多遥控器目标。

以 Deviation 为唯一应用主体，独立实现 TX15 适配。按用户当前要求，后续开发不考虑 EdgeTX；除非用户明确提出需要。

## 当前状态

当前进入 P1：电脑端 480×320 模拟器；实机适配仍待后续开发。

已新增 `emu_tx15` 主机模拟目标，显示原生 Deviation 主界面、混控列表与曲线页面。79 项主机测试、10 项工具回归及 lint 通过。**输入仍为电脑测试配置，尚无 TX15 硬件目标或可刷写固件，未进行实机验证。**

## 开发入口

- [设计与范围](docs/superpowers/specs/2026-09-21-tx15-native-design.md)
- [分阶段开发计划](docs/superpowers/plans/2026-09-21-tx15-native-plan.md)
- [工作状态与下一步](TODO.md)
- [源码及环境基线](docs/tx15/baseline.md)
- [Windows 构建命令](docs/tx15/build.md)
- [TX15 模拟器启动与实际画面](docs/tx15/simulator.md)
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

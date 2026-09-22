# New Deviation TX15 Native Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking. Execute locally in sequence; no automatic parallel agent dispatch.

**Goal:** 建立可复现的 Deviation 原版基线和 TX15 原生移植依据，随后按 P1～P4 分步开发。

**Architecture:** Deviation 为唯一应用主体。新增 H7/TX15 目标，通过其平台接口连接原有混控、页面、模型及 CRSF；EdgeTX 仅提供底层参考。

**Tech Stack:** C/C++、GNU Make、GNU Arm Embedded、原项目 libopencm3、CuTest、FLTK 模拟器；H7 外设库在 P0 审计后选定。

**Spec:** `docs/superpowers/specs/2026-09-21-tx15-native-design.md`

## Global Constraints

- 主工程和应用运行逻辑必须是 Deviation。
- 不把 Deviation 嵌入 EdgeTX 应用框架，不引入 EdgeTX 混控或模型作为主实现。
- EdgeTX 只作为 TX15 硬件定义、启动和外设驱动参考；任何代码复用记录来源、版本、许可及依赖。
- 首版使用内置 ELRS/CRSF；传统直连射频、多协议外置模块和完整 Lua 生态不属于首版验收范围。
- 原 Deviation 目标保持可构建；新的 H7 适配不得用全局替换方式破坏 F1/F2。
- 编译、模拟器、板上启动、射频链路、异常验证分别记录，不互相替代。

## Review Focus

1. 测试执行器自身失败或返回错误退出码：P0-2 单独核对，不能只看输出中的 OK。
2. 中文路径、缺依赖、错误工具链被误认成源码失败：P0-1 区分环境和产品问题。
3. 老模型引用 TX15 不存在的开关/射频：P1 用样本验证显式拒绝及输出禁用。
4. 高负载时序和 DMA 缓存错误：P2/P3 用仪器测量，不能只用模拟器证明。
5. 存储中断和链路异常：P3/P4 注入故障，分别验收模型完整性和接收机输出。

## 执行范围和顺序

本文件详细执行范围是 P0。P1～P4 是有验收条件的路线图，不是可以直接照写的驱动代码计划。P0 得到内存布局、工具链及接口依据后，为下一阶段补充真实文件/寄存器/命令的详细计划，禁止猜测启动地址和硬件引脚。

### P0-1：源码和开发环境基线

**Files:** 读取 `.gitmodules`、`README.md`、`src/Makefile`、`src/target/tx/other/test/Makefile.inc`、`src/target/drivers/mcu/emu/Makefile.inc`；维护 `docs/tx15/baseline.md`；成功后新增 `docs/tx15/build.md`。

**Interfaces:** 输入为固定上游提交和 gitlink；输出为可重复的工具版本、依赖版本、命令及完整日志。

- [x] 下载 Deviation 到 `D:\DEVI移植\deviation`，核对 HEAD 为 `330193b9a4185f6a2cdc3af90d654169cd210094`。
- [x] 读取构建规则、测试入口和子模块 pin，检查本机工具可用性。
- [x] 先解决 Git shell 路径问题；原始失败是 `basename` / `sed` 无法执行和 `git-sh-setup` 找不到。复测 `git submodule status`，成功后执行下面命令，不更新到子模块分支最新提交。

```powershell
Set-Location 'D:\DEVI移植\deviation'
git submodule update --init --recursive
git -C src/libopencm3 rev-parse HEAD
```

预期子模块为 `d55bbafddb9768228748f48a82967f91a910806e`。若宿主 Git 仍不可用，优先在选定构建环境中执行同样的操作，而非改上游 pin。

- [x] 选择可用的独立构建环境。优先 Linux 环境；当前 WSL 仅返回安装帮助，不视为已安装可用发行版。当前 PATH 中无 Docker。不得把“有 wsl.exe”写成“Linux 环境就绪”。
- [x] 在所选环境中安装/验证 GCC/G++、Make、Perl、Python、zlib 开发库、FLTK 1.3 开发库和 GNU Arm Embedded。先参照仓库历史构建使用的 Arm 8-2018-q4，再依据下载可用性固定实际版本；H7 编译器升级单独评估。
- [x] 记录 `gcc --version`、`g++ --version`、`make --version`、`perl -v`、`python3 --version`、`fltk-config --version` 和 `arm-none-eabi-gcc --version`。每条命令检查实际退出状态。
- [x] 先在现有路径构建；如工具确实不支持中文路径，使用有记录的 ASCII 工作副本，不移动或删除用户目录。

### P0-2：原版测试与模拟器基线

**Files:** 读取 `src/tests/test_mixer.c`、`test_model.c`、`test_pages.c`、`test_pages_advanced_mixer.c`；审查 `src/target/tx/other/test/make-tests.sh`；日志归入 `docs/tx15/baseline.md` 指向的本地产物目录。

**Interfaces:** 消费 P0-1 的工具环境；输出原版测试数量/失败项、模拟器操作记录和固件构建结果。

- [x] 在具备上述依赖的 POSIX shell 中执行，每条命令分别记录退出状态：

```sh
cd src
make -j2 test
./test.elf
make -j2 emu_devo8
make -j2 devo8
```

已执行对应入口；Windows 使用 build-msys2.ps1 包装脚本，模拟器实际目标为 win_emu_devo8。版本、兼容参数和验证结果见 docs/tx15/build.md。

- [x] 先检查测试执行器生命周期：当前生成脚本在 `CuSuiteDelete(suite)` 后读取 `suite->failCount`。核实释放实现；如确认释放后访问，单独修复并用“至少一项失败时进程必须非零退出”的检查验证，再信任测试退出码。保留原版运行结果，不把修复后的结果冒充原版。
- [ ] 启动 `emu_devo8.elf`，实际检查主界面、复杂混控编辑、曲线编辑、模型保存/加载；无显示环境时记录为未验证，不能以链接成功代替。
- [ ] 在原始混控测试上选取直通、反向、限幅、多路混控、条件切换、虚拟通道及时间相关行为，记录已覆盖项和缺口。新增测试只补语义缺口，不为文档或空目录写测试。
- [x] 将环境修复与产品逻辑变更分开记录；通过前不创建声称可用的 TX15 固件。

### P0-3：TX15 启动与驱动审计

**Files:** 新增 `docs/tx15/hardware-map.md`、`docs/tx15/boot-memory.md`、`docs/tx15/source-provenance.md`；参考 EdgeTX 固定版本 `f5c13ab13ecadf3689c5854cfba51c43646fceec` 中的 `radio/src/targets/tx15/` 和 `radio/src/boards/rm-h750/`。

**Interfaces:** 输入为已固定源码和实际板卡信息；输出为每项带文件/行号证据的接口表，不输出猜测地址的链接脚本。

- [x] 保存参考文件及许可信息，只读分析，不把 EdgeTX 作为构建主工程。
- [ ] 逐项记录 CPU、QSPI、SDRAM、LCD、触摸、ADC、按键/开关、内置模块 UART、模块供电、电源锁存、USB、存储的引脚、实例、时钟和依赖。
- [ ] 查清原启动程序做过哪些初始化，主固件入口/向量表/加载地址、外部 Flash 分区、固件封装和恢复方式；对照 TX15 实机型号及主板版本。
- [ ] 对缓存、DMA、MPU、显示帧缓冲区标出访问主体及一致性责任。
- [ ] 为每个外设选择“复用 Deviation、实现 H7 专用驱动、参考外部实现”之一，附理由和依赖。禁止未经审计引入 EdgeTX 调度器/模型/混控。
- [ ] 完成可执行的恢复操作卡之后，才把 P2 的首次写入安排到实机。

### P0-4：接口差距与下一阶段计划

**Files:** 新增 `docs/tx15/porting-map.md`；维护本计划、设计稿和 `TODO.md`。

**Interfaces:** 消费 P0-2 基线与 P0-3 硬件表，输出 P1/P2 详细实现计划。

- [ ] 从 `src/target.h` 枚举 TX15 必需接口，在使用点确认调用上下文；重点审查 `CLOCK_StartTimer`、`UART_SetDataRate`、`UART_SetDuplex` 与 ADC/LCD 接口。
- [ ] 分析 `src/Makefile` 的目标发现、`SCREENSIZE` 页面选取、对象文件同名冲突和固件打包路径。
- [ ] 为未来 `src/target/tx/radiomaster/tx15/`、模拟目标和 H7 驱动给出最小文件清单，避免先复制整个旧目标再保留失效初始化代码。
- [ ] 固定模型输入映射和兼容行为；选择一个仅用于原型的彩屏显示方案。
- [ ] 根据已核实事实补写 P1/P2 的测试、实际接口和构建命令，更新人周估算。

## 后续阶段验收路线

|阶段|开发内容|主机侧验证|实机验证|粗估工作量|
|---|---|---|---|---|
|P0|上述基线与审计|原版测试、模拟器、固件构建|设备信息和恢复方案核实|2～3 人周|
|P1|480×320 模拟目标、模型映射、原页面适配|触摸坐标、滚动、焦点、模型往返、混控输入轨迹对照|无需射频|3～6 人周|
|P2|H7 启动、存储/内存、显示、ADC、输入、电源|构建、链接布局审查|重复启动、恢复、采样、画面、关闭射频|6～12 人周|
|P3|CRSF UART/DMA、ELRS 参数及遥测|畸形/部分帧、CRC、参数分片和超时|通道顺序/端点、周期抖动、参数设置、失联|4～8 人周|
|P4|彩屏页面完善、模型可靠保存、告警和发布|全套回归、旧目标构建|长时间运行、写入中断、重启、更新回退|8～12 人周|

阶段粗估合计 23～41 人周，尚不包含全部未知问题缓冲；整体原生路线继续以 8～15 人月作为初步预算。实际顺序以依赖与证据为准，不将日历时间等同于连续工程投入。

## 当前交付状态

2026-09-22：已完成源码/子模块固定、MSYS2 与 Arm 构建基线、79 项主机测试、8 项工具回归、DEVO8 固件与模拟器编译。模拟器仅检查启动后存活 10 秒，未完成交互验收。硬件/启动/接口审计已有首轮文档，仍需补齐输入与启动装载链、实际板卡核对和恢复操作卡。P0 尚未全部完成；下一步处理 P0-2 交互检查、P0-3 剩余审计及 P0-4 的 P1 详细计划。

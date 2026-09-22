# TX15 主机模拟器第一批实现计划

> 使用 superpowers:executing-plans 顺序实施。用户已授权继续既定原生 Deviation 路线。

**Goal:** 提供可启动的 480×320 Deviation 模拟目标和可检查的实际画面。
**Architecture:** 使用 Deviation 自身 FLTK、宽屏页面和原混控；目标仅包含主机配置，不引入其他固件。输入先采用明确标注的 Deviation 测试配置，不声称对应 TX15 物理开关。
**Tech Stack:** C/C++、FLTK、MSYS2、现有 CuTest 和 Python unittest。
**Spec:** docs/superpowers/specs/2026-09-21-tx15-native-design.md，受用户 2026-09-22 最新约束覆盖：除非用户提出需要，不再考虑 EdgeTX，不把其版本或审计作为开发前提。

## Global Constraints

- 保持混控算法及模型格式不变；不执行硬件写入。
- emu_tx15 使用独立 filesystem/tx15，不覆盖原模拟器模型。
- 480×320 原生画布；复用已有宽屏页面。P1 仍包括后续输入映射、模型兼容和交互完善，本批不宣称 P1 全部完成。
- 不加入虚假的硬件 tx15 编译目标、刷写地址或 GPIO 定义。

## Review Focus

1. 点击屏幕外不能触发边缘控件；拖出屏幕后清除按下状态。
2. 触摸坐标必须匹配显示，不能将侧栏事件夹到最后一列。
3. 捕获模式必须限时完成，输出真实 framebuffer，不修改模型作为副作用。
4. 宽屏资源缺失应被实际截图检查发现；不能仅以进程存活判定 UI 成功。
5. 旧目标默认行为与测试应继续通过；新目标无设备写入代码。

### Task 1: 模拟目标与触摸输入

**Files:** 新增 target/tx/radiomaster/emu_tx15/{Makefile.inc,target_defs.h,capabilities.h,emu.h}；新增 mcu/emu/touch.h；修改 fltk.cpp；新增 utils/tests/test_emu_touch.py。
**Interfaces:** 输出原生 480×320 IMAGE_X/Y；触摸助手输入窗口坐标、画布位置和尺寸，输出命中状态及逻辑坐标。

- [x] 测试触摸四角、外部坐标、画布偏移和缩放映射，先观察缺少实现的失败。
- [x] 实现独立主机目标与触摸助手，接入 FLTK 事件。
- [x] 测试通过，编译 win_emu_tx15。

### Task 2: 运行证据与交付

**Files:** 修改 fltk.cpp 加入显式环境变量启用的限时画面捕获；修改 utils/build-msys2.*；新增运行脚本和 docs/tx15/simulator.md；更新 TODO/README。
**Interfaces:** 运行脚本可正常交互启动或捕获 PPM；输出必须是 480×320 的真实 framebuffer。

- [x] 提供可重复的构建、启动、限时捕获入口。
- [x] 捕获实际画面并检查显示；记录页面复用及输入配置限制。
- [x] 原 79 项 CuTest、工具回归、独立 lint 和旧模拟器构建通过。
- [x] 进行一次独立代码评审，修复阻塞问题，提交推送开发分支。

## 本批验证记录

2026-09-22：TX15 主界面/混控列表/曲线真实画面检查通过；曲线使用 heli_std.ini。79 项 CuTest、10 项工具回归、lint、旧 DEVO8 模拟器及画面捕获、Arm DEVO8 固件构建通过。复审发现曲线默认模型无效，已用绘图区断言复现失败并修复为标准模板。

实现选择：先交付自有宽屏页面和明确标注的虚拟输入配置。实际 TX15 输入映射仍未实现，后续需要单独迁移模型源，不能把此模拟器作为实机输入行为证据。没有刷写操作。

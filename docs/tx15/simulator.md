# TX15 彩屏模拟器：原生输入适配

这是原生 Deviation 的电脑端目标 `emu_tx15`，使用自己的 480×320 RGB565 逻辑画布、原有宽屏页面、混控与配置代码。没有硬件 tx15 编译目标，不产生可刷机文件。

## 构建与启动

先按 [构建说明](build.md) 安装工具，然后在项目根目录执行：

```powershell
.\utils\build-msys2.ps1 -Target emu_tx15
.\utils\run-tx15.ps1
```

第二条打开交互窗口。窗口左侧是 480×320 显示区，右侧是输入/输出数值。鼠标模拟触摸；箭头、Enter、Esc 操作焦点、确认与返回。点击显示区外不会被夹到边缘控件。

首次启动脚本将资源复制到 `local/tx15-native`，以后使用同一目录；重新构建只刷新 `src/filesystem/tx15` 中的开发模板，不覆盖 `local/tx15-native` 的模型。关闭窗口时可选择保存并退出或不保存退出。启动脚本不要并行运行多份，以免同一模型被多个进程保存。

不要将 `src/filesystem/tx15` 当作日常模型目录，也不要直接运行 exe 后在该模板目录保存重要数据。

## TX15 原生输入配置

输入数量和类型依据 [RadioMaster TX15 官方手册](https://cdn.shopify.com/s/files/1/0701/8066/7584/files/TX15_manual_V1.5_bee3e99d-7e1e-4d5b-bbe6-d559712e03cd.pdf?v=1789608956) 的出厂配置：4 个摇杆轴、S1/S2 两个旋钮、SA～SD 三段开关、SE 自锁按钮、SF 自复位按钮、六段按键。共 28 个逻辑输入，沿用 Deviation 每个开关位置一个输入源的表达方式。

|键|模拟输入|模型中的名称|
|---|---|---|
|q / a|增加 / 减少 Elevator|ELE|
|w / s|增加 / 减少 Rudder|RUD|
|e / d|增加 / 减少 Throttle|THR|
|r / f|增加 / 减少 Aileron|AIL|
|o / l|增加 / 减少 S1|S1|
|p / 分号|增加 / 减少 S2|S2|
|x、c、v、z|依次循环 SA、SB、SC、SD|SW A0～SW D2|
|b|切换 SE，自锁，松手保持|SW E0 / SW E1|
|n|按住 SF，松手复位|SW F0 / SW F1|
|数字 1～6|选择六段按键位置，互斥保持|6POS0～6POS5|
|Shift + Q/A、W/S、E/D、R/F|四对微调|TRIMLV、TRIMLH、TRIMRV、TRIMRH|

键盘重复事件不会让开关连续跳挡。窗口失去焦点会释放 SF、微调和触摸，保留其他自锁位置。逻辑位置 0/1/2 的电气方向尚未在实机确认；更换肩部开关后的配置也未适配。摇杆模式会影响物理操纵杆语义，以右侧监视值为准。

标准混控默认使用 SA 切换飞行模式、SB 控制陀螺仪、SC/SD 控制副翼/升降双率、SE 作油门保持。六段按键当前用于**高级复杂混控**；标准曲线页面只有两段/三段容量，不能选用六段按键，含此分配的标准模型会拒绝加载。主页旧 Toggle 控件仍只有三个图标，不能完整显示六段状态；六段状态可在右侧输入监视中查看。SYS/MDL/TELE 和实体滚轮的专用导航行为留待后续适配。

## 模型兼容与数据保护

- 通用摇杆、通道、虚拟通道和 TX15 原生输入名称可以读取；本批验证了全部 28 个输入的反向源和正向开关保存/重载。
- 旧模型含 FMODE、MIX、GEAR、RUD DR 等旧开关或额外微调名称时，明确报错；不会自动猜测映射。需要在副本中按模型用途人工确认并替换。
- 模型加载失败会恢复此前模型，并阻止模型保存，直到成功加载或主动重置。启动时加载失败显示 `Load failed`，不允许把空白模型写回原文件。
- 模板和布局加载失败会恢复此前内容。界面弹出加载错误；解析器的检查不是任意损坏 INI 文件的完整验证器。
- 自带三个含旧开关的模板和默认布局已有专门的 TX15 版本。源码中的 C 别名只服务标准混控内部接口，不是模型文件导入别名。
- 本版启动目录改为 `local/tx15-native`，首次复制新的资源；上一版 `local/tx15` 原样保留。需要保留的旧模型应先复制备份，再检查输入名称后导入新目录。

模拟器没有射频输出，串口/ELRS 接口仍是主机桩。

## 可重复画面检查

使用 Windows 原生 Python：

```powershell
python utils/capture-emulator.py --output local/logs/tx15-main.ppm
python utils/capture-emulator.py --page mixer --output local/logs/tx15-mixer.ppm
python utils/capture-emulator.py --page curve --output local/logs/tx15-curve.ppm
```

脚本为每次检查建立临时文件系统，显式开启捕获模式，等待启动后直接读取实际 framebuffer，检查尺寸、数据长度及非空内容。超时为 15 秒，退出时删除临时目录，不操作 `local/tx15-native` 的模型。PPM 是未压缩 RGB 图像。页面检查通过代码切换，不等价于鼠标完成编辑、保存、重载的交互验收。

原 320×240 背景图片没有被拉伸冒充新界面：目标启用 Deviation 自带的颜色背景绘制；部分控件仍沿用旧页面尺寸，后续再优化触摸区域和布局。

本次实际运行画面（曲线检查加载自带 `heli_std.ini` 模板）：

![主界面](images/simulator-main.png)
![混控列表](images/simulator-mixer.png)
![标准油门曲线](images/simulator-curve.png)

2026-09-23 本批验证：79 项原 CuTest、12 项工具回归、原生模型集成检查、独立 lint，TX15 三页面捕获及原 DEVO8 模拟器/固件构建均通过。新增检查命令如下：

```powershell
.\utils\build-msys2.ps1 -Target runner
.\utils\build-msys2.ps1 -Target tx15-test
```

集成检查链接实际模拟器对象，在临时文件系统中执行模型读写、失败恢复、文件保留，以及六段复杂混控通道计算。曲线捕获还检查绘图区，避免将“Invalid model ini!”错误画面算作通过。完整鼠标编辑与保存交互尚未验收。

## 本批修复范围

- 新增独立主机目标及画布，沿用 Deviation 的宽屏页面分支。
- 增加触摸边界、偏移和缩放映射检查。
- 语言容量检查器支持只有模拟器的目标。
- 修复显示/模型配置用 `long` 承载指针导致的 Windows 64 位地址截断；使用指针宽度整数计算字段偏移，以字节指针访问字段。模型字段、文件格式及混控运算不变。

后续：复杂混控与曲线的完整鼠标/键盘交互回归、六段状态显示完善，以及硬件驱动。当前开发不依赖其他固件的信息。

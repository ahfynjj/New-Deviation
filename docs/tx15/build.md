# Windows 构建基线（2026-09-22）

本页是已执行的 Deviation DEVO8/主机基线。现已加入 emu_tx15 电脑模拟器，见 [运行说明](simulator.md)。没有 TX15 硬件编译目标；生成的 DEVO8 固件不能刷入 TX15。

## 工具布局与安装

项目位于 `D:\DEVI移植\deviation`；工具位于相邻的 `tools` 目录：`msys64`、`arm8/bin/arm-none-eabi-gcc.exe`、`python-packages/cpplint.py`。原生模拟器工具链副本位于 `%TEMP%\new-deviation-ucrt64`。

已验证版本：MSYS GCC 15.3.0、GNU Make 4.4.1、Python 3.12.14、Perl 5.42.3；UCRT GCC 16.2.0、FLTK 1.4.5、PortAudio；GNU Arm Embedded 8.2.1（8-2018-q4）、cpplint 1.3.0。包仓库会更新，重装时应记录实际版本。

MSYS2 基础包来自 [官方发布](https://github.com/msys2/msys2-installer/releases/tag/2026-06-11)，所用 x86_64 tar.xz SHA256 为 `a2d047e8ee213c3c6a49a8de427eb1069df12207c0422ff1b3cbb5c905c34221`，已与发布资产摘要核对。解压初始化后，在其 Bash 中更新并安装：

```sh
pacman -Syu
pacman -S --needed gcc make perl python zlib-devel git diffutils zip \
  mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-fltk \
  mingw-w64-ucrt-x86_64-portaudio
```

更新若要求关闭终端，按提示重新打开继续。当前机器镜像超时后使用 `repo.msys2.org`；未关闭包签名校验。

Arm 包来自 [Arm 官方归档](https://armkeil.blob.core.windows.net/developer/Files/downloads/gnu-rm/8-2018q4/gcc-arm-none-eabi-8-2018-q4-major-win32.zip)。解压到 arm8；本次下载 SHA256 为 `be5e2f68549efaecb79bdc34ff03c06f27deb2fcec3badddb5729cfb5ce43d6b`（本地记录，未找到独立摘要核对）。这只是原 F1/F2 基线工具链，H7 版本另行选定。

用本机带 pip 的 Python 安装检查器，并首次建立不存在的工具链副本目录：

```powershell
python -m pip install --target 'D:\DEVI移植\tools\python-packages' cpplint==1.3.0
Copy-Item -LiteralPath 'D:\DEVI移植\tools\msys64\ucrt64' -Destination "$env:TEMP\new-deviation-ucrt64" -Recurse
Copy-Item -LiteralPath 'D:\DEVI移植\tools\arm8' -Destination "$env:TEMP\new-deviation-arm8" -Recurse
```

临时目录被清理后需重新建立，或用 `-NativeRoot` 指定保留的 ASCII 目录。原生 MinGW GCC 在本机中文安装路径下无法定位内部链接库，SUBST 也未解决；复制工具链后通过。源码保留原位置。脚本只修改子进程 PATH，并用 `-isystem` 标记工具链头文件，没有全局关闭警告。

## 构建与测试

PowerShell 中逐条运行，检查每条的 `$LASTEXITCODE`：

```powershell
Set-Location 'D:\DEVI移植\deviation'
.\utils\build-msys2.ps1 -Target runner
.\utils\build-msys2.ps1 -Target test
.\utils\build-msys2.ps1 -Target emu_devo8
.\utils\build-msys2.ps1 -Target emu_tx15
.\utils\build-msys2.ps1 -Target devo8
.\utils\build-msys2.ps1 -Target lint
```

所有目标支持 `-ToolsRoot`；模拟器支持 `-NativeRoot`，Arm 支持 `-ArmRoot`，两者均应使用 ASCII 路径。`-Rebuild` 传入 Make 的 `-B`。不要并发运行多个构建，它们共享生成文件和资源目录。

Arm 工具链原先在中文路径下首次编译通过，但其依赖文件记录了损坏的系统头文件路径，导致增量构建失败。因此 Arm 也使用 ASCII 副本。GCC 8 还会把部分项目头文件转成损坏的绝对路径：**当前中文源码目录下只支持完整 Arm 构建**。包装脚本检测到非 ASCII 源码路径时，自动删除仅属于 DEVO8 和其 F1 库的生成依赖（`src/objs/devo8/*.P`、`src/libopencm3/lib/stm32/f1/*.d`），并强制重编译全部对象，避免复用依赖不完整的缓存。ASCII 源码目录保留原 Make 行为，本次未验证该路径下的增量构建。

日志保存于 `local/logs/<目标>.log`，不纳入 Git。`runner` 当前运行 10 项工具回归；`test` 构建后以 60 秒超时运行 79 项 CuTest。缺失模块、循环依赖等诊断来自相应用例，以汇总和退出码联合判定。

`lint` 仅检查相对 main/master 的修改行，`DEVIATION_LINT_BASE` 可指定基准，无这些分支时退回 HEAD。未跟踪文件应先加入索引；`--no-fail` 供原 Makefile 非阻断检查，独立 lint 目标会返回失败。cpplint 1.3.0 有 `sre_compile` 弃用警告，不影响本次检查。

DEVO8 构建传入固定 libopencm3 的 `SRCLIBDIR`，绕开旧空白处理表达式与 Make 4.4 的兼容问题，没有更新子模块 pin。

## 验证边界

模拟器为 `src/emu_devo8.exe`，资源为 `src/filesystem/devo8`。启动工作目录为 `src`，PATH 包含 NativeRoot/bin。编译或进程存活不等于复杂混控、曲线和保存/加载完成交互验收。

本次以隐藏方式启动并观察 10 秒，进程未提前退出，随后只终止该测试进程。标准输出和错误日志为空；未声称完成界面交互检查。

`src/devo8.bin`、`.dfu`、`.elf` 只验证 DEVO8 交叉编译，没有对任何遥控器刷写。

## TX15 原生输入集成检查

```powershell
.\utils\build-msys2.ps1 -Target tx15-test
```

该命令先构建模拟器，再使用同一对象列表链接测试入口，在临时文件系统里运行真实模型读写和混控测试，不操作用户的模型目录。日常启动仍用 `run-tx15.ps1`，本版数据位于 `local/tx15-native`；之前的 `local/tx15` 不会被改写。

# 2026-09-21 原生 TX15 基线检查

## 已执行

- `git clone https://github.com/DeviationTX/deviation.git deviation`：成功。
- `git rev-parse HEAD`：`330193b9a4185f6a2cdc3af90d654169cd210094`。
- `git log -1`：2026-02-23，Improve VTX telemetry support (#1062)。
- 文档添加前 `git status --short`：空，未改上游代码。
- `git ls-tree HEAD src/libopencm3`：gitlink `d55bbafddb9768228748f48a82967f91a910806e`。
- 查到现有 CuTest、混控、模型和页面测试；原构建入口为 `make test`、`./test.elf`、`make emu_devo8`、`make devo8`。
- 未找到适用于当前目录的 AGENTS.md。

## 环境观察

当前 shell：Windows PowerShell，工作目录 `D:\DEVI移植`。

PATH 可找到 Git、CMake、Ninja、Python 和 wsl.exe；未找到 make、arm-none-eabi-gcc、docker。只说明当前命令环境未就绪，不宣称机器其他目录一定没有这些工具。

`wsl --list --verbose` 返回安装帮助，没有得到可用发行版清单；WSL 构建环境未证实。

`git submodule status` 失败：Git 的 shell 启动路径中 basename/sed 无法执行，随后找不到 git-sh-setup。主仓库 clone/rev-parse 可用不代表子模块操作正常。

## 验证状态

|项目|状态|
|---|---|
|源码取回和版本检查|完成|
|子模块取回|未完成|
|原版单元测试|未运行|
|原版模拟器构建/运行|未运行|
|原版硬件固件构建|未运行|
|TX15 新目标|未创建|
|TX15 型号/板卡/固件版本核对|未完成|
|刷写、启动、射频、恢复|未执行|

## 需要特别核实的测试基础问题

`src/target/tx/other/test/make-tests.sh` 生成代码中，先调用 `CuSuiteDelete(suite)`，再读取 `suite->failCount`。需检查释放行为并验证失败退出码；目前只作静态观察，尚未修复或执行动态验证。

## 复核命令

```powershell
Set-Location 'D:\DEVI移植\deviation'
git rev-parse HEAD
git ls-tree HEAD src/libopencm3
git status --short
git diff --check
```

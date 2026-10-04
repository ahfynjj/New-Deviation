# TX15 MAX 首次 New Deviation 独立安装清单

状态：**首次安装实机验收通过：完整读回、独立断电启动、菜单/六路输入、关机再次开机**。
2026-10-04：原始内部128KiB、外部首1MiB完整核对后，实际外部擦除/编程/读回、
未改动尾部比较及内部擦除/编程/完整读回全部通过。用户按断电启动步骤后回复
“开机了 devi系统”，确认独立启动进入Deviation。随后用户确认“所有都正常，没有闪屏了”，
菜单/六路输入、关机再次开机通过；当前独立运行未观察到先前RAM台架闪屏。
原系统恢复写入未执行。
本次未修改显示驱动，尚未定位先前台架闪屏根因；不追加显示诊断。
授权记录在本地 `human-approval-20261004T083634Z.json`。

## 本次安装结果与范围

目标：这台 TX15 MAX 的原生独立启动版，射频默认关闭。
具备已验收的Deviation页面/混控和四轴/S1/S2输入；本次先验收脱离调试器独立开机、
页面操作和电源键关机。此固定候选不含USB更新、模型/校准断电保存或可飞行ELRS输出；
已有ELRS/Lua成果后续合入持久版。

| 操作 | 地址范围（包含末地址） | 文件/大小 |
|---|---|---|
| 外部NOR擦除 | 偏移 `0x000000..0x081fff`（映射 `0x90000000..0x90081fff`） | 532480B，130个4KiB扇区 |
| 外部NOR编程 | 偏移 `0x000000..0x0815ff` | `payload.bin`，529920B，256B页 |
| 内部Flash擦除 | `0x08000000..0x0801ffff` | 131072B，唯一128KiB扇区 |
| 内部Flash编程 | `0x08000000..0x08001adf` | `boot.bin`，6880B，32B Flash字 |
| 必要时恢复外部 | 偏移 `0x000000..0x0fffff` | `original-external.bin`，1048576B |
| 必要时恢复内部 | `0x08000000..0x0801ffff` | `original-internal.bin`，131072B |

安装先比较当前内部128KiB和外部首1MiB与原备份，再擦写/完整读回外部；
外部通过才擦写内部并完整读回。外部首1MiB中未擦写的尾部也读回核对。
不会写保护/选项字节、整片NOR或TF卡。本次会替换当前启动固件，失败需要调试器恢复。
恢复严格先完整外部1MiB、再内部128KiB，两区均读回通过才允许正常重启。

## 实际冻结包与备份

目录：`D:\DEVI移植\deviation\local\tx15-hardware\install\kit\`。
绑定MCU UID `1c0039000e51333234363236`；每次操作重新检查UID、文件摘要、
实时保护/几何/CPU暂停/供电状态。原内部两次128KiB和外部两次16MiB备份已核对一致。
完整原外部备份仍在 `local/backups/tx15-external-20261003-155621/`；kit包含恢复所需首1MiB。
另存整个kit、完整备份及本仓库工具代码到另一存储位置可离线恢复。

已打包本次冻结kit和Python工具源代码：
`local/tx15-hardware/install/recovery-kit-20261004-bulk16.zip`，SHA256
`a477850769cce5cce15996c93e680320e680a2583ddf96a546c7394d747ffaf7`。
已检查ZIP完整性、六个固定文件摘要，并解压到独立目录成功运行离线清单CLI。
压缩包不含Python/pyOCD运行环境；这台电脑使用上方已安装环境，异机需另备。
此项只是恢复包软件/文件验证，不等于真实擦写恢复测试。

| 文件 | SHA256 |
|---|---|
| boot.bin | `5241eea8b1761243f3aef4be42793027d64b3dc815c8d24d99e53ae03cbb4ef1` |
| payload.bin | `085a9e98960aaa343aeb843cfa927263a48f727ba271ef8ce209c86b433e1546` |
| original-internal.bin | `984420d754587cd5561c1b3f3df49ccdd34da868ff785efbdcdc0cff09569ad0` |
| original-external.bin | `6f1afac85dd9acaa9e07522f9ace8b4124d68da88df856cb54b1c247dc08b315` |
| reader.elf | `7df17ec5959416d7ce527600309db744af76ded319d88ba5b12a7aa54a3d8265` |
| reader.bin | `d097c3f89118eab9576a27eca2d8d7a6df8c9d868ff71063344889085b8f00ad` |

## 操作命令

以下在仓库目录的**交互式PowerShell终端**执行。Codex工具必须 `tty:true`；
普通关闭stdin的管道会在探针打开前拒绝操作。

```powershell
Set-Location 'D:\DEVI移植\deviation'
$py = 'D:\DEVI移植\tools\pyocd-venv\Scripts\python.exe'
# 离线再次核对kit/显示清单，不连接设备、不代表取得许可
& $py utils/hardware/flash_install.py
```

首次安装命令，**仅在用户明确同意本清单后执行**：

```powershell
& $py utils/hardware/flash_install.py --arm --install --approval 4283f1eb9511a9d646f4215e265dc6e3c0a6bbb292fe4c6fbeefec02dc7c553d --press-window 300 --swd-frequency 500000
```

恢复原系统命令，发生首次擦写失败或明确要求恢复后使用：

```powershell
& $py utils/hardware/flash_install.py --arm --recover --approval 9f4446002472ac11203ce63f56fc4f7c06a77248cffe1491b929d0deb887c289 --press-window 300 --swd-frequency 500000
```

两条命令共用已验收RAM入口：看到 `ARMED UNDER RESET` 后按住电源**不要松开**，
保持按住并在终端输入 `HELD` 回车；代理操作时用户回复“已按住”，代理转入终端。
只有看到 `HALTED, PH12 HIGH: RELEASE POWER NOW` 才松开。接收机保持断电。
可不依赖原系统正常开机或SDRAM内容；尚未对真实损坏Flash向量做物理恢复测试。
Flash比RAM装载慢，保持电池电量和USB连接，等工具明确完成，不按键/拔线。

事务intent/dirty记录在kit目录持久保存，成功安装仍禁止执行旧PC；失败不自动重启。
若工具返回错误或连接中断，保留kit与日志，先执行恢复并验证两区，再尝试正常开机；
不要绕过未完成事务再次安装。

只有安装/恢复明确输出 `VERIFIED; CPU KEPT HALTED` 后，断开调试器USB、
断开电池5秒，再接回电池，保持调试器断开，正常开机验证对应系统。
首次原生开机确认页面、滚轮/ENTER/EXIT、六路输入、电源键关机及再次开机。

## 已获得的证据与边界

完整原生启动→独立应用RAM链：`native-chain-20261004-103806.json`，用户验收正常。
独立SWD只读后端：`native-chain-20261004-122319.json`。
恢复入口：`flash-entry-20261004-162629.json`，NRST捕获、UID、RAM读回和V8新鲜心跳、
只读几何/两区64B原前缀、最终暂停通过，Flash破坏性命令0；用户断开调试器/电池后
开机确认原界面恢复。精简结果在 [observation.json](evidence/2026-10-04/recovery-entry/observation.json)。

### 首次安装前的读取加速

旧逐字SWD读取导致完整核对耗时过长。确认事务sequence=0、两区dirty=false后，
停止旧进程并核实CPU仍暂停，未发送Flash擦写命令。新增内部连续AP读取，跨1KiB
TAR边界拆分；QSPI固定DR地址、每次最多16B，并在异常后恢复AP递增模式。
实机FIFO在30B处停顿，因此不等待32B；对应失败回归先复现再修复。

44项相关检查通过。500kHz实机只读完整比较内部128KiB和外部首1MiB，均与原备份
一致，耗时分别2.547s、102.969s，退出暂停通过，Flash破坏性命令0。
本地证据 `local/tx15-hardware/install/bulk-read-evidence.json`。
CLI默认仍50kHz；上方安装/恢复命令显式选择已验证的500kHz。
冻结镜像、许可摘要、写入范围及擦写算法没有改变。

仅使用上方bulk16恢复包；早期 `recovery-kit-20261004-bulk.zip` 含已否决的32B等待，
不能用作当前恢复工具。旧 `recovery-kit-20261004.zip` 为未加速工具的历史备份。

安装事务 `transaction-c12cf540af724836bbc253806f44d157.json` 已到 `installed`，
sequence=2316，checkpoints包含external/internal，退出CPU暂停读回通过。
日志 `local/hardware-session/flash-entry-20261004-173432.json`。
精简证据：[首次安装](evidence/2026-10-04/first-install/observation.json)、
[批量读取](evidence/2026-10-04/first-install/bulk-read.json)。
事务dirty=true表示已替换原内容，不表示安装失败；冻结manifest里的
`physical_programming_tested=false` 是生成许可摘要时的历史信息，不修改它破坏绑定。
实际当前擦写证据以上述事务和日志为准。原系统恢复写入仍未经物理测试。
真实断电启动、菜单/六路输入和关机再次开机已由脱离调试器的用户反馈验收。
当前不宣称USB更新、模型/校准断电保存或可飞行ELRS已完成；下一阶段优先USB更新/日志。

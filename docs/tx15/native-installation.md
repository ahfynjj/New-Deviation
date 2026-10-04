# TX15 原生独立启动候选与安装清单

2026-10-03：已生成候选文件，尚未进行Flash擦写或真实断电启动验收。
这是完整原生启动路线，不调用原系统的启动程序或应用框架。

## 启动路径

内部Flash向量 → 无栈PH12/LDO供电确认 → RAM/ECC初始化 → VOS1、HSE、PLL128
→ SDRAM初始化 → 单线QSPI读取完整载荷到暂存区 → 全量校验 → 应用/资源复制及
读回 → QSPI停止 → 显示初始化 → V9交接验证 → 禁用中断并切换向量/MSP
→ 应用初始化自己的BSS/栈 → 原生Deviation。

读取失败、格式/CRC/任一向量错误、复制或读回错误，都不会返回可执行入口。
应用复制使用明确的STRD双字存储初始化AXI ECC；不能把栈上STRD误当作目的地址
写入证据。交接V9记录完成阶段，不伪造旧V6的RAM诊断结果；独立应用接收后
进入V10。旧台架应用仍使用V6→V7，两种入口不能互换。

| 用途 | 地址/范围 |
| --- | --- |
| 原生启动程序 | 内部 `0x08000000..0x0801ffff`，128KiB |
| 启动工作区 | AXI `0x24000000..0x2400dfff` |
| 启动交接 | `0x2400e000`，128字节 |
| 启动栈 | `0x2400f000..0x2400ffff`，4KiB |
| 应用代码/BSS | `0x24010000..0x2407bfff` |
| 应用栈 | `0x2407c000..0x2407ffff`，16KiB |
| 帧缓冲 | `0xd0000000`，307200字节 |
| 字体/图标资源 | `0xd0080000..0xd00fffff` |
| 载荷暂存 | `0xd0100000`，最大 `0xec040` 字节 |
| 原生外部启动槽 | 外部Flash偏移0起1MiB（映射地址 `0x90000000`） |

外部槽属于New Deviation候选布局，将替换其中的原系统内容；不声称它是
原系统的空闲区。其余外部内容首版不使用。正式擦除范围由最终载荷长度及
实际芯片擦除粒度决定；目前4KiB粒度是候选，写入工具还须核对保护和几何信息。

## 独立应用首版

首版保留原生页面、四轴/S1/S2、校准和混控，射频关闭。构建拒绝与ELRS诊断、
Lua或RC开关同时启用；已有Lua/RC开发保留在台架模式，待独立启动验收后再接入。
应用不含定时返回原固件的机制。开机键须连续松开20ms后才能触发关机，之后
连续按住2秒关闭内置模块、背光和PH12保持；按键仍供电时等待释放。

模型及校准尚未断电保存，USB更新/日志、声音、触摸、开关输入和接收端验收
不属于本批交付。故障停止时不自动跳回原固件；首次安装前必须有可验证的
调试器恢复工具，不能把“有备份”当成“已验证能恢复”。

## 构建与只读打包

先清除其它TX15射频构建开关，在PowerShell执行：

```powershell
python utils/build-tx15-boot.py
$env:TX15_STANDALONE='1'
python utils/build-tx15-app.py
Remove-Item Env:TX15_STANDALONE
python utils/hardware/install_plan.py
python -m unittest discover -s utils/hardware/tests
```

独立应用输出到 `local/tx15-hardware/app-standalone`；旧台架构建输出到 `app`。
平台交接代码已改动，下一次台架装载须重建镜像并重新核对/绑定哈希；不能沿用
历史应用的哈希直接装载本批代码，也不能将独立交接镜像当成V6台架应用。
安装打包器绑定ELF/BIN、应用ELF/载荷和RF关闭构建元数据，再核对两份内部
128KiB与两份外部16MiB备份的既有哈希。它不打开设备，也没有Flash写入功能。
元数据和CRC用于排除混用/损坏，不是签名认证或写入授权。

`local/tx15-hardware/install/` 生成：

- `boot-flash.bin`：6880字节，内部写入对齐32字节；内部整个128KiB擦除范围。
- `payload-flash.bin`：529920字节，包含529872字节载荷及256字节页面对齐填充；
  当前候选外部擦除532480字节，均在1MiB槽内。
- `recovery-internal-128k.bin`：原内部完整内容。
- `recovery-external-slot-1m.bin`：原外部启动槽；完整16MiB备份仍保留。
- `install-plan.json`：范围/哈希/恢复顺序及未验收项，明确 `flash_write_authorized=false`。

本批86项检查及启动程序/独立应用ARM编译、链接、存储/RAM布局检查通过。
启动程序text6880字节、BSS4232字节（含交接/栈）；独立应用96个ARM对象。
软件检查覆盖截断/越界/格式错误、读取中断、复制失败、读回失败、入口隔离、
错误交接/模式混用、按键首次松开/长按/计时回绕和备份不一致。
以上为2026-10-03的软件证据；2026-10-04完整RAM启动链已实机通过，见下文。

## 2026-10-04 实机证据与显示问题

原生启动器7016字节和独立载荷529872字节上传读回一致；原NOR JEDEC
c84018/64字节前缀核对成功，随后由原生loader执行校验、复制读回及交接。
V10的ticks 386→75912、loops 8→13918，运行约75秒，无故障、RF关闭。
ADC/LCD/QSPI/SDRAM/PLL/VOS/CPU恢复全部通过。用户确认页面、滚轮、
ENTER、短EXIT及四轴/S1/S2正常，原界面恢复；日志
`local/hardware-session/native-chain-20261004-103806.json`。

用户确认“不操作时整屏或背光也持续闪”。当前LCD适配直接改写LTDC
正在扫描的单帧缓冲，控件先清背景再画内容，但这不能解释或证明该现象
的实际原因。背光在驱动中保持PA10高，无软件PWM；下一轮应先采集实际
背光输出、LTDC错误/欠载和扫描状态，区分数据扫描与供电/背光闪烁。
尚未修改时序或刷新代码，不宣称闪屏已修复；显示质量仍是待办。
本次通过不等于候选载荷已写入NOR，也不等于真实断电POR已通过。

## 闪屏对照工具（2026-10-04）

同一启动/应用镜像可通过 `python utils/hardware/run_native_chain.py --arm --display-diagnostic`
采集LTDC ISR/CPSR/CDSR及PA10背光模式/ODR/IDR；不清ISR、不改LCD时序、
不中断LTDC扫描。应用正常运行20秒后暂停CPU15秒，再恢复35秒；暂停时
临时将帧缓冲顶部8行（`0xd0000000` 起7680字节）设为红条，逐块读回，
结束后将原像素恢复并读回，再恢复CPU。所有图像改动仅在RAM中。

首次70个样本（20运行/15暂停/35恢复）均为PA10输出及输入高电平，
扫描位置变化，ISR未记录FIFO欠载/传输错误。该控制器证据不能代替背光
实际电压测量，也不能解释所有闪屏；状态字段依据[ST RM0433](https://www.st.com/resource/en/reference_manual/rm0433-stm32h742-stm32h743-753-and-stm32h750-value-line-advanced-armbased-32bit-mcus-stmicroelectronics.pdf)。
日志 `local/hardware-session/native-chain-20261004-110015.json`，恢复全部通过。
红条复测日志 `local/hardware-session/native-chain-20261004-111048.json`：
用户确认红条/CPU暂停期间仍闪，且为肉眼可见的整屏明暗变化。
同样70个样本无FIFO/传输错误，PA10采样为高；红条像素读回恢复及原系统恢复通过。
该结果排除“应用重绘是唯一原因”，尚不能区分面板驱动与背光实际供电。

正常原固件运行时只读快照 `local/hardware-session/original-display-20261004-111803.json`：
LTDC时序/极性/格式/行距与原生驱动一致；两种PLL配置计算得到相同的10.6667MHz
像素时钟。RGB引脚均为低速AF14。明确差异为PA10：原生GPIO恒高，而正常原系统
为AF1/TIM1_CH3 PWM，ARR100、CCR3=13，占空比13/101，约13%。差异尚未证明因果。

`--backlight-diagnostic` 沿用上述同一镜像和红条阶段，只在CPU暂停时临时配置
未使用TIM1/PA10，约990Hz、13/101占空比；结束后读回核对TIM1复位状态、
时钟门控及PA10原配置，再恢复CPU。该频率按本台架HCLK64MHz/APB2分频推导。
不改Flash、LCD时序、供电保持GPIO；恢复失败则保持CPU暂停，需要人工断电。
此开关仅用于验证背光差异，不表示已将PWM写入固件或已修复闪屏。


背光对照实机日志 `local/hardware-session/native-chain-20261004-112711.json`：
70个样本中，运行/暂停/恢复的PA10模式分别为GPIO输出/AF/GPIO输出；
PWM参数逐项读回通过，TIM1/时钟/引脚、红条像素及原系统上下文恢复全部通过，
cleanup_errors为空。V10 ticks 389→55526、loops 9→10973，无故障、射频关闭。
用户确认“变暗但仍旧闪，好像只有屏幕边缘闪”。低亮度不能消除现象，
不将GPIO恒高直接认定为根因，也不据该结果马上将PWM并入正式驱动。
软件验证：8项显示诊断检查、7项现有启动链检查通过；固件镜像未变化。

2026-10-04 用户要求暂缓闪屏，面板初始化对照不再安排。该问题保留后补，
不作为独立安装开发前置；本批转入 Flash 参数核对和受限安装事务。

## 实机存储参数与事务核心（2026-10-04）

小型RAM只读程序/自动恢复已实测通过：SFDP确认16MiB、页256B及4/32/64KiB
擦除；SR=00/02/20，保守保护检查未触发；仍不能由JEDEC/SFDP确定芯片完整后缀。
见[完整记录](bench-2026-10-04.md)。内置128KiB保护选项只读快照已取得，无选项修改。

`flash_transaction.py` 固定两区边界、文件/备份绑定、外部先校验再内部提交以及
恢复外部先于内部。越界、现场原内容不同、读回失败、超时和Ctrl+C均覆盖。
事务核心不打开设备；现已增加下述受限SWD后端，但尚无首次安装/失败启动恢复入口，不能用作刷机命令。
seal只绑定具体数据与范围，不替代用户许可；当前没有永久写入授权。

```powershell
python utils/build-tx15-boot-bench.py --flash-info
# 台架已实际就绪后才提示按键；仅状态/SFDP读取并恢复原系统
python utils/hardware/run_native_chain.py --arm --flash-info
# 仅生成清单；不连接调试器
python utils/hardware/flash_transaction.py --evidence local/hardware-session/native-chain-20261004-114414.json
```

`local/tx15-hardware/install/transaction-plan.json` 绑定现有RF关闭镜像、两份既有
内外备份和本次实机观察；候选外部擦除532480B，内部128KiB。
后续实际擦写必须重新核对设备/保护/原内容，补齐SWD后端及中断持久记录，
完成恢复执行验证后，再安排用户确认和首次写入。未进行任何Flash擦除或编程。

## 受限SWD后端与中断记录（2026-10-04）

`swd_flash.py` 实现外部4KiB擦除/256字节页编程、内部单个128KiB扇区擦除/
32字节Flash字编程；地址固定在外部首1MiB和内部`0x08000000..0x0801ffff`。
写入前重新检查CPU暂停、线程模式、SysTick/缓存/MPU关闭、PH12保持供电、
PLL128/HCLK64、LDO/VOS1、容量及当前保护状态。没有选项字节、状态寄存器
写入、整片NOR擦除或第二内部扇区操作。超时不复位/恢复CPU或强行改写忙中的控制器。

`flash_journal.py` 在每条破坏性命令前将操作范围/数据摘要与dirty标志写入独占
JSON记录，fsync后原子替换；记录保存失败则不发WREN/Flash解锁命令。
外部读回检查点是内部写入的前置；阶段验证后禁止再次改写该阶段。
成功安装仍禁止恢复旧PC；只有完整恢复双方原内容并验证后才解除。
进程/USB中断保留失败或未完成intent，既有记录不覆盖。Windows文件系统/存储
突然掉电的所有场景并无保证；安装前仍须另存已校验备份。

只读台架入口：

```powershell
python utils/hardware/run_native_chain.py --arm --flash-backend-check
```

它使用原3816字节RAM初始化镜像，停止SysTick并暂停CPU后，由SWD后端独立
读取JEDEC/SR/SFDP和内外Flash各64字节前缀，与RAM报告/原备份核对，再恢复原系统。
传输层另有允许列表，只准控制器设置与读取命令；不允许WREN、Flash KEY、DR数据
写入或目标Flash写入。Ctrl+C也先执行原上下文恢复。前缀检查不等同完整备份检查。

实机已通过，日志 `local/hardware-session/native-chain-20261004-122319.json`：
独立后端的JEDEC/SR/SFDP及内外各64B与既有报告/备份一致；原系统恢复检查
通过，用户确认原界面恢复。可选 `--press-window 300` 留5分钟按键窗口。
41项相关软件检查通过。未发送擦写命令，后续不重复此项基础核对。

仍需完成：失败安装后重新进入RAM恢复环境的入口、完整恢复读回与安装退出策略的
台架验证，最终具体刷入确认清单。实际擦除/编程尚未实机验证；当前未写Flash，
未获得永久刷入许可，未验证真实断电启动。

## 下一批

2026-10-04 完整 RAM 链台架已通过：

```powershell
python utils/build-tx15-boot.py --ram-chain
python utils/hardware/chain_ram_session.py
python utils/hardware/run_native_chain.py --arm
```

最后一条仅在 TX15/PWLINK2 接好、正常开机并能配合按键时执行。须看到
ARMED 提示后再按电源键；应用就绪后有75秒操作时间，测试期间不按电源键。
原 NOR 仍是原固件，台架实际读取 JEDEC/原前缀，但将应用读取来源替换为
`0xd0200000` 的电脑上传缓冲。`0xd0100000` 暂存、完整CRC/向量校验、
复制读回和应用交接均执行同一原生实现；电脑不直接装载应用目的地址。
因此通过只能证明这条装载/交接链，不能证明 NOR 安装或真实 POR 已通过。

正常退出恢复 ADC/LCD/QSPI/SDRAM/时钟/电压及原 CPU；只有活动 SysTick
允许正常返回。其它活动异常或恢复校验失败时保持 CPU 暂停和供电，禁止
恢复未核对 PC，此时需要人工断电再开机；Flash未改写。工具不含安装功能。

1. 已完成：不写Flash的完整原生启动程序→独立应用RAM链及正常退出恢复。
2. 核对实时保护/擦除编程几何，完成受限安装/恢复工具及故障退出读回。
3. 展示最终文件、地址、备份与恢复步骤，再安排首次持久写入。
4. 拔掉调试器，从断电状态验证原生开机、页面/输入和电源键关机。

恢复应先还原外部槽并读回，最后还原内部128KiB并读回，再断电验证原系统；
不能先恢复原内部启动程序，却让它继续读取尚未恢复的外部内容。

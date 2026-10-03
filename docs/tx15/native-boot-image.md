# TX15 原生启动镜像契约 v1

当前交付包含载荷封装、原生启动程序与独立应用候选，但还不是经过实机
独立启动验收的成品。具体布局、构建和恢复文件见[原生安装候选](native-installation.md)。
仍不包含Flash写入工具或USB更新器，没有执行持久擦写。

## 启动路线

内部 Flash 放置 New Deviation 原生启动程序；完成电源保持、冷启动
时钟、QSPI、SDRAM、显示初始化后，从核对过的外部存储位置读取载荷，
完整校验后装载应用及资源。沿用现有应用的 RAM 运行地址，不采用
其它遥控器系统的应用框架。候选布局为原生独占外部偏移0起1MiB启动槽，
将替换该范围内原内容；实际写入前仍须验证几何、保护和恢复工具。

台架应用要求版本6板级初始化报告，并保留RAM台架/射频超时策略。
新独立候选通过 `TX15_STANDALONE=1` 分开构建，要求原生V9交接，运行报告
为V10；首版射频关闭，不自动返回原固件。不能混用两个模式的 `.nd15`。

## 二进制格式

全部整数为小端32位；固定64字节头，随后为代码和资源两段。

| 偏移 | 字段 | 要求 |
| --- | --- | --- |
| 0 | magic，8字节 | `ND15APP1` |
| 8 | version | 1 |
| 12 | total bytes | 等于完整文件长度 |
| 16 | entry | Thumb入口，与向量表第2项相同 |
| 20 | board | `0x54583135`，TX15契约标识，不是芯片自动识别 |
| 24 | code descriptor，16字节 | 目的地址、文件偏移、有效长度、CRC32 |
| 40 | resource descriptor，16字节 | 同上 |
| 56 | flags/reserved | 0 |
| 60 | header CRC32 | 头的前60字节 |

代码目的地址固定 `0x24010000`，最大 `0x6c000` 字节；资源目的地址
固定 `0xd0080000`，最大 `0x80000` 字节。每段在文件内补零到8字节
边界，CRC只计算有效字节；填充必须全零。代码偏移固定64，资源紧随
代码及其填充；不允许重叠、额外尾部数据或其它目的地址。

CRC采用标准CRC32/ISO-HDLC（与 Python `zlib.crc32` 相同），用于检测
损坏，不构成签名认证。必须校验两个段和全部176项向量后才生成装载
计划：初始SP为 `0x24080000`，所有处理函数和入口位于已装载代码内。
应用自身初始化BSS和专属栈；文件不携带BSS或栈内容。

`hardware/tx15/boot/image.c` 是无硬件副作用的固件端校验器：失败时清空
输出计划，不复制、不执行，也不写Flash。未来装载器应保持来源不可变，
校验成功后才复制；不能边校验边启动或将不可信文件长度直接用作映射读取范围。

## 生成与检查

```powershell
python utils/hardware/boot_image.py pack local/tx15-hardware/app/tx15-app.elf --output local/tx15-hardware/app/tx15-app.nd15
python utils/hardware/boot_image.py inspect local/tx15-hardware/app/tx15-app.nd15
python -m unittest discover -s utils/hardware/tests -p test_boot_image.py
```

当前RC候选封装为689384字节，入口 `0x24032599`，代码225113字节、
资源464200字节。载荷SHA256：
`a6737e29299c05c59b9dc457953ce34ee3c71b57c2ffb4b732f96f46f263adf4`。
这些数据只是本轮构建记录，之后构建必须重新校验。

下一步：完成本机存储身份/备份与恢复核对，实现原生冷启动和只读QSPI
装载，形成具体安装/恢复方案，再进行首次持久写入与断电独立开机验收。

## 本机备份证据（2026-10-03）

外部映射 `0x90000000` 起前16MiB已在原系统持续运行时读取两遍，文件
SHA256均为 `968cab41ec1bd50f271b8c2ad7fff0fc981fefdca42aadc3ef672933ce2ad7a1`。
本地记录：`local/backups/tx15-external-20261003-155621/manifest.json`，清理无错误；
读取后再次只读连接，DHCSR无暂停位，原系统仍运行。内部Flash128KiB的
历史双份备份也重新校验一致。没有复位、暂停、QSPI配置更改或Flash擦写。

控制器DCR为 `0x00180000`，其FSIZE配置与当前24位地址模式不等于
物理Flash容量证明；寄存器解释依据[ST RM0433](https://www.st.com/resource/en/reference_manual/dm00314099-stm32h742-stm32h743-753-and-stm32h750-value-line-advanced-arm-based-32-bit-mcus-stmicroelectronics.pdf)。
当前尚无JEDEC身份、TF卡备份或实际恢复验证，不宣称全机备份完成。

## 冷启动初始化与只读存储驱动（2026-10-03）

已实现独立启动所需的首段初始化代码，但尚未验证断电冷启动：

- `early_supply.S` 在任何RAM写入、C函数栈之前，用无栈汇编保持PH12供电、
  确认已启用LDO、完成SCUEN配置并等待ACTVOSRDY。失败原地停止，不写邮箱。
  依据[ST PWREx的Run*限制](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/master/Src/stm32h7xx_hal_pwr_ex.c)，
  供电配置完成前不能写RAM，不能仅靠后续C函数做这一步。
- `cold_start.c` 随后建立VOS1、至少2个Flash读等待周期及HSE/PLL128时钟；
  保留更高等待周期和其它ACR位。修改Flash读控制寄存器不等于编程Flash内容。
- `qspi.c` 仅从复位空闲控制器进入，使用4MHz、单线`0x9F`读JEDEC和
  `0x03`读数据；仅覆盖前16MiB地址窗口，不发送写使能、擦写或芯片配置命令。
  GPIO复用已与本机寄存器核对。容量/布局须待实际身份确认后决定。

合并RAM镜像只运行上述初始化和64字节读取，不初始化显示、SDRAM或射频；
使用版本8邮箱验证两次ticks/loops前进，JEDEC及读取头单独保存。
主机将读取头与已有16MiB备份前64字节比较。异常退出也强制复位QSPI、
恢复PG6输出锁存，再恢复原GPIO/时钟和原固件复位入口；恢复失败禁止继续执行。
台架要求已就绪LDO/VOS1..3和足够读等待周期。初始化临时进入VOS1；退出先恢复
HSI64，再恢复原VOS并等待实际电压就绪，供电选择及Flash读等待周期保持不变。

```powershell
python utils/build-tx15-boot-bench.py
python -m unittest discover -s utils/hardware/tests
```

本批77项相关检查通过；合并镜像ARM编译/链接及RAM布局检查通过，
text3436字节、BSS4308字节，入口`0x240002c1`。本机构建ELF SHA256：
`ff22f7e5ba0272e8f6b6bf11735a5d93817351ecc81a875c599f81c2ad3389d7`。
这些构建数据不是断电独立启动证明；暖复位RAM测试不构成POR证明。

下一步依据下列实机结果确定存储布局、编写真正的内部Flash启动程序与
载荷装载路径，并区分应用的台架/持久运行模式。
当前仍无实机验收后的可刷入成品；候选已确定原生启动槽偏移0，安装清单
仍未授权，实际几何/保护/恢复和断电启动待验收，不执行持久写入。

### 合并台架实测

首轮在装载前发现本机复位后VOS3（CSR1/D3CR=`0x6000`，CR3=`0x05000042`，
ACR=`0x37`），被过严VOS1门槛拒绝；未装载镜像，原固件恢复且无清理错误。
补齐安全电压恢复并通过回归/集中审查后，第二轮成功：

- 日志 `local/hardware-session/reset-halt-power-20261003-165924.json`。
- 3440字节RAM装载读回一致，版本8状态3/error0；ticks278→730、
  loops149398→390352，Fault字段全零，PH12供电保持有效。
- JEDEC=`0xc84018`，64字节`0x03`读取与已有映射备份前64字节完全一致。
  该ID与[GigaDevice GD25Q128H官方ID表](https://download.gigadevice.com/Datasheet/DS-01121-GD25Q128H-Rev1.2.pdf)
  一致；GD25Q128类为128Mbit/16MiB，不能由相同ID确定具体后缀或保护状态。
- 先恢复HSI64，再恢复原VOS3；CSR1/CR3/D3CR/ACR精确读回初始值，
  QSPI复位、PG6锁存、GPIO/FMC、时钟、CPU上下文恢复全部成功，无清理错误。
  原固件再次运行，用户确认原界面恢复。

本轮只有RAM与外设寄存器操作，未写Flash内容、选项字节、射频参数。
仍未验证真实POR、SFDP/具体型号、Flash保护/恢复编程、TF卡备份或正式安装。

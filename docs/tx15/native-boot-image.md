# TX15 原生启动镜像契约 v1

当前交付是启动载荷封装及装载前校验，不是可直接刷写的固件。
不包含 Flash 地址、擦写操作、启动程序或 USB 更新器。

## 启动路线

内部 Flash 放置 New Deviation 原生启动程序；完成电源保持、冷启动
时钟、QSPI、SDRAM、显示初始化后，从核对过的外部存储位置读取载荷，
完整校验后装载应用及资源。沿用现有应用的 RAM 运行地址，不采用
其它遥控器系统的应用框架。外部 Flash 分区/型号确认前不指定安装偏移。

现有应用仍要求版本6的板级初始化报告，且包含 RAM 台架退出/射频超时
策略。冷启动程序必须建立独立的初始化契约，正式应用必须区分台架与
持久运行模式；不能把当前 `.elf` 或 `.nd15` 当成独立启动成品。

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

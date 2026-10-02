# TX15 MAX 内置 ELRS 设备发现

板级依据：本地固定 EdgeTX 提交 `19b50d967e6e579ac5a1b3bdb014b148a6b47491`
的 `radio/src/targets/tx15/hal.h`，仅参考硬件定义。寄存器依据 ST `stm32h750xx.h`。

| 功能 | 配置 |
|---|---|
| 内置串口 | USART6，PG14 TX / PG9 RX，AF7，全双工、不反相 |
| 内置电源 / boot | PB13 高电平开启；PH9 低电平正常启动 |
| 首轮时钟 | 既有PLL128/HCLK64，PCLK2=32MHz，USART16SEL=0，BRR=80 |
| 格式 | 400000 baud，8N1，FIFO关闭，IRQ71，无DMA |
| 缓冲 | RX256环形（可用255），TX64整帧复制，IRQ单次最多32次处理 |
| 外置参考 | USART2 PA2/PA3，PD4供电；尚未实现/实测，不照搬内置双工设置 |

固件中默认不启用。仅环境变量 `TX15_ELRS_DISCOVERY=1` 构建时启用设备发现。
USART6向量固定在外设IRQ71（向量索引87），保留176个向量/704字节检查。
查询仅发送0x28广播设备发现；不发送RC、模型ID、绑定或设置写入。
首个请求在启动1秒后发送；每秒重试，收到有效内部模块0x29或15秒超时后关电。
报告 `tx15_rf_report` 包括状态、计数、名字、原始版本字段和参数数量。

恢复：暂停CPU/停止SysTick → 禁用IRQ71并确认不在该异常中 → PB13关电 →
USART6复位 → 清pending、恢复priority与APB2 → 原有GPIO/显示/SDRAM/时钟恢复 →
原固件复位入口。GPIOB快照需临时开启时钟；清理失败必须阻止恢复运行。
`rf_session.py`不恢复GPIO配置本身，由既有display/SDRAM恢复器负责。
物理GPIO/IRQ活跃位与寄存器复位失败不能由软件单元测试代替。

本版本是设备发现诊断，不是实时通道驱动：持续高频收发、UART错误原因分类、
飞行调度、模块选择UI和ELRS解锁通道仍需后续开发。

## 参数读取扩展

`TX15_ELRS_PARAMETERS=1` 自动开启发现及只读参数抓取：发现后按1..N发0x2C，
按chunks-remaining顺序重组0x2B，每项最多512字节、最多64项。单chunk等500ms，
最多3次请求，整轮最多45秒；失败标明参数ID并关电。全部读取后关电。
禁止发送0x2D参数写入。`tx15_rf_parameters`保留原始字段，主机工具
`utils/hardware/crsf_parameters.py`仅用于验收解码，不替代未来官方Lua界面。
新增报告字段把设备识别后的UART错误/丢字节与启动阶段分开统计。

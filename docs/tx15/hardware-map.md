# TX15 MAX 硬件适配记录

2026-09-21：用户确认持有 TX15 MAX 和 ST-Link；EdgeTX 版本口述为最新版，精确版本和主板修订尚未读取。下表是固定源码定义，不等于本机测量结果。

参考版本：EdgeTX `f5c13ab13ecadf3689c5854cfba51c43646fceec`。文件链接均固定到该提交。

|部件|参考定义|New Deviation 处理方式|
|---|---|---|
|CPU|STM32H750xB；HSE 定义 48 MHz|新 H7 时钟/启动实现；以实际晶振和板卡核实结果为准|
|电源|按键 PA4，电源保持 PH12|先核实电平及开关时序，再实现 Deviation 电源接口|
|内置模块|USART6，TX PG14、RX PG9，AF7；电源 PB13；启动控制 PH9|新增 H7 全双工 UART/DMA，供原 Deviation CRSF 使用|
|模块 DMA|TX DMA1 stream1，RX DMA1 stream5，DMAMUX USART6|对照 ADC/显示资源表，明确缓冲区与 cache 责任|
|QSPI|CLK PF10；CS PG6；数据 PF9/PF8/PF7/PF6；容量宏 0x1000000|先读 JEDEC ID 和原分区，禁止以容量宏推断可覆盖范围|
|外部 SDRAM|8 MiB；TX15 构建覆盖起点为 0xD0000000|初始化和内存测试独立于主界面，先验证缓存关闭模式|
|显示|逻辑 480×320，物理 320×480，16 位；驱动使用 LTDC|画面旋转、帧缓冲和触摸坐标必须一起校验|
|触摸|GT911 参考实现；I2C4 PD13/PD12，INT PE2，RESET PJ13|实现 Deviation touch 接口，不引入 EdgeTX 触摸状态体系|
|IO 扩展|共享 I2C，总线地址定义 0x74、0x75|确认库采用 7 位还是移位地址后使用；校验按键/微调方向|
|存储接口|SDMMC1 与 SDMMC2 均有定义|进一步对照板卡和驱动确认内置存储及卡槽用途|
|摇杆/模拟输入|采用 ADC 驱动，板配置提供映射|解析 hw_defs 中全部 analog 定义并实机逐轴核对；不推测顺序|

证据入口：

- [hal.h：电源、QSPI、UART、I2C、触摸](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/targets/tx15/hal.h#L84)
- [构建：CPU/SDRAM/模块/驱动](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/targets/tx15/CMakeLists.txt)
- [硬件 JSON](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/boards/hw_defs/tx15.json)
- [IO 扩展定义](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/targets/tx15/bsp_io.h)
- [LCD](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/boards/rm-h750/lcd_driver_480.cpp)

## 实机前仍需获取

准确 EdgeTX 版本/构建号、主板修订、MCU 标记、存储芯片标记、可用 SWD 连接点、原固件及用户模型备份。ST-Link 的存在不代表已连接或已验证恢复。

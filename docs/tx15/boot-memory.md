# TX15 启动与内存审计（首轮）

> 历史审计留档，2026-09-23 起不再沿此处的外部固件兼容/版本核对路线开发。当前独立 RAM 诊断、复位和供电条件见 [实机联调说明](hardware-bringup.md)，后续由芯片官方资料和本机验证决定启动布局。下文旧模拟器排期及兼容装载要求不作为当前任务前提。

本文件仅陈述参考源码，尚未获得本机读回结果，不能作为直接刷写指南。

## 已确认的参考机制

EdgeTX 固定版本 `f5c13ab13ecadf3689c5854cfba51c43646fceec`：

- [主链接布局](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/boards/generic_stm32/linker/stm32h750_sdram/layout.ld)将 `REGION_TEXT_STORAGE` 指向 NORFLASH，将 `REGION_TEXT` 指向 SDRAM；这意味着不能把外部 Flash 的存储地址等同于代码运行地址。
- 布局的通用 EXTRAM 默认是 0xC0000000；[TX15 构建配置](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/targets/tx15/CMakeLists.txt)设置 `TARGET_EXTRAM_START=0xD0000000`。生成实际链接命令后仍需核对覆盖是否进入最终 ELF。
- 内部 Flash 区域定义为 0x08000000/128 KiB，启动程序大小常量为 0x10000。此常量不是授权覆盖整个内部 Flash 的依据。
- NORFLASH 固件链接区域为 0x90000000/8 MiB，而板卡 QSPI 总容量宏为 16 MiB。容量与固件分区不同，剩余空间用途必须另查。
- ISR 向量与 data 使用 DTCMRAM，bss 使用 RAM_D1。数据缓冲区不能仅凭 CPU 可访问就假定 DMA 可访问。
- [board.cpp](https://github.com/EdgeTX/edgetx/blob/f5c13ab13ecadf3689c5854cfba51c43646fceec/radio/src/boards/rm-h750/board.cpp#L112)中启动程序路径初始化外部 Flash 和 SDRAM；运行时另有 `ExtFLASH_InitRuntime()`。

## 对原生 Deviation 的决定

1. 独立实现 Deviation 的 H7 平台启动，保留应用、混控和页面结构。
2. 首次原型优先研究与现有启动程序兼容的装载契约，减少破坏恢复路径的可能；不预设兼容已经成立。
3. 必须追踪启动入口、数据拷贝表、向量表重定位、时钟/MPU/cache 状态和 UF2 地址编码后，才生成新固件链接布局。
4. DMA 缓冲区使用区域、对齐和 clean/invalidate 策略必须列入 P2 的明确设计；UI、ADC 与 CRSF 的责任分别定义。

## 尚未完成的证据

- 本机启动程序/分区读回和精确版本对应。
- UF2 封装与实际固件入口之间的完整调用链。
- QSPI 剩余分区用途、内置存储和卡槽映射。
- ST-Link 对该主板的连接、只读识别以及恢复操作验证。

这些缺口阻止首次固件写入，但不阻止主机侧测试和模拟器开发。当前未生成或执行任何擦写命令。

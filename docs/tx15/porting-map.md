# Deviation → TX15 接口差距（首轮）

## 已有核心及接入点

|模块|现有文件/接口|移植工作|
|---|---|---|
|混控|`src/mixer.c`，`MIXER_CalcChannels()`，`Channels[]`|优先保持算法原样，定义输入映射和调用时序|
|模型|`src/config/`，`src/tests/test_model.c`|保存格式与硬件映射分离，不把旧射频配置静默换成 ELRS|
|显示|`src/target.h` 的 `LCD_*`，`src/target/drivers/display/emu/emu_color.c`|新增 H7/LTDC 实现，处理物理旋转、帧缓冲和更新策略|
|页面|`src/pages/320x240x16/`、`src/pages/common/`|复用操作流程，先运行原页面，后扩展 480×320 布局|
|输入|`src/target.h`、各目标 `capabilities.h`|TX15 通道/按钮枚举；校准和缺失输入行为需样本验证|
|计时|`CLOCK_StartTimer(unsigned us, u16 (*cb)(void))`|保持微秒单位和回调返回间隔约定，审查中断优先级|
|串口|`UART_SetDataRate(u32 bps)`、`UART_SetDuplex(uart_duplex duplex)`|USART6+DMA 全双工，保持现有调用契约|
|CRSF|`src/protocol/crsf_uart.c`|复用帧/参数逻辑，测试部分帧、CRC、超时和模块重启|
|模拟器|`src/target/drivers/mcu/emu/`|建立主机编译基线后再添加 TX15 模拟目标|

`crsf_uart.c` 已有 `Full (Int)` 选项、ELRS 相关设置和 `CLOCK_StartTimer` 调度，但不由此推断当前 ELRS 版本全部功能已经兼容。

## 构建约束

`src/Makefile` 从 `target/tx/*/*` 发现目标。新家族建议 `radiomaster`；`tx15` 是未来硬件目标名。默认 TXS 列表不自动包含全部目录，新增目标的批量构建范围需要明确。

`SCREENSIZE` 同时影响页面、绘制和文件系统资源。不能只把屏幕宏改成 480×320 就期望原页面自然适配。P1 需拆清“物理画布”和“原页面布局”的关系。

对象列表使用 `notdir`，不同目录同名源文件可能映射为同一对象文件。H7 适配应防止重复收集旧 STM32 同名驱动，验证实际编译列表，而非只看文件存在。

## P1 最小边界

输入：通过的原版主机测试/模拟器基线、明确的 TX15 输入表。
输出：可运行的 480×320 主机模拟目标；原混控和配置语义保持一致。先复用原页面布局作为过渡，明确这不是最终彩屏 UI。

验收：显示范围/触摸边界/滚轮与按键焦点；直通、反向、限幅、条件、虚拟通道、时间相关混控；旧模型硬件源映射和不支持协议显式拒绝。

P1 具体新增文件与接口测试在原版构建成功、输入表完成后固定。P2 链接脚本需先满足 boot-memory.md 的证据要求；当前不创建不可运行的 tx15 空壳来冒充适配进展。

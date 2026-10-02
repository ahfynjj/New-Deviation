# TX15 内外置 ELRS 与 Lua 兼容设计

## 已确认目标

用户要求原生 Deviation 支持官方 ELRS Lua 设置脚本，同时兼容内置与外置高频头。
保留 Deviation 模型、混控、页面体系；新增 Lua 解释器和 EdgeTX API 兼容层。
首期内外置任选其一工作，两个槽位保留独立配置；双模块同时发射和其他外置协议后续处理。
继续实机优先、临时 RAM 装载、不写 Flash。用户在上述方案后要求继续开发。

## 分层与契约

- Deviation 通道输出 → CRSF 通道打包 → 模块路由 → 内置/外置硬件适配器。
- 原版 ELRS Lua → EdgeTX API 兼容接口 → 同一个模块路由；参数收发与通道发送共享链路。
- 模块编号 internal=0、external=1，与 `model.getModule()` 对齐；off=-1。
- 启动默认关闭。切换模块/模型必须停止旧硬件、清空 TX/RX/DMA，然后建立新会话。
- 软件会话使用递增 generation，丢弃旧会话异步回复；不能据此分辨模块物理线上迟到的数据，硬件层仍须停止/清空。
- 通道数据只保留最新一份并优先发送；脚本队列有界，忙时返回失败供上层重试，不能覆盖已排队参数。
- 路由层由一个任务串行调用；IRQ/DMA只提供字节缓冲，不能并发修改路由状态。
- CRC/帧长校验在数据进入 Lua 前完成；Lua得到type与payload，不含sync/length/CRC，保留扩展地址。
- 第一版以源码 `.lua` 为兼容目标，固定官方脚本版本和哈希；不承诺 `.luac` 或全部 EdgeTX API。
- Lua以受限执行预算运行；混控和通道发送必须独立于脚本绘图/GC获得服务。
- 初期可内嵌未经修改的官方脚本；TF加载、模型持久化、独立启动另有阶段。

## 验收与边界

每个槽位分别验证设备识别、参数列表、写入读回、接收机通道和断链行为。
脚本报错、超预算、队列满、模块断开/切换不得阻塞通道发送或串写另一模块。
本轮先完成可独立测试的帧/路由核心。驱动接入前不启用RF、不改变现有实机镜像行为。
当前混控验收模型的CH5用于旋钮测试，不能直接用于ELRS发射；接入前建立独立的未解锁测试模型。

## 参考与待核对事项

- [TBS CRSF规范](https://github.com/tbs-fpv/tbs-crsf-spec/blob/main/crsf.md)：64字节上限、length/type/payload/CRC布局。
- [EdgeTX Lua收发API](https://luadoc.edgetx.org/lua-api-reference/rf-module/crossfiretelemetrypush)：参数队列背压语义。
- [官方ELRS脚本](https://github.com/ExpressLRS/Lua/blob/master/elrs.lua)：init/run、model.getModule、绘图/事件/bit32及CRSF请求。
- 现有 `src/protocol/crsf_uart.c` 紧耦合旧UART与全局状态，暂不影响旧机型；新核心先供TX15使用。
- 延续Deviation通道比例：10000→+100%，CRSF中心992、每100%为800ticks；饱和到0..1984，禁止溢出回绕。
- 内外置接口引脚、反相/双工、电源顺序仍须依据固定板级资料核对。不能将两个接口仅当作换UART号。
- 用户确认目前只有内置高频头，尚无外置模块；先内置实机，外置硬件验收延期。接收机型号待补充。真实硬件和实时性验收不可由主机测试替代。

Ruling: 沿用用户已确认方案，单代理直接执行首批可逆代码；不为同一方向重复请求批准。

# TX15 STO2 / AUD2 时钟与 I2C 计时修正

2026-10-17。依据用户两张完整诊断照片修正软件缺陷。软件批次未访问设备；随后用户
更新确认“磁盘有了 声音也有了，但是声音非常的小”。识别/合成音基本通过，音量待改善，
不等于WAV文件播放或文件写入通过。[反馈证据](evidence/2026-10-17/media-basic-user-acceptance.json)。

## 实测证据

`IMG_4992.JPG`：AUD1 Error Reason6，Tests0/DMA3/Errors1/Underruns0，Step4、Reg10、
Value00、I2C00008001，DmaFlags/SPI均0，Init281ms、Gap16ms。
`IMG_4993.JPG`：STO1 Error2/HW0，CMD0/STA00002000/RESP0、Reads0，Time282ms、
Gap142ms，CLK000000A0/PWR3，PLL01090898/SEL0，CMDR00001000，0MiB/RCA0。
照片原文件SHA256见[证据](evidence/2026-10-17/media-clock-i2c-fix.json)，图片不纳入仓库。

存储PLLCFGR的DIVQ1EN(bit17)没有置位，尽管旧驱动进行了写入。核对
[ST LL RCC v1.11.2](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/v1.11.2/Inc/stm32h7xx_ll_rcc.h)
的LL_RCC_PLL1Q_Enable，明确要求PLL1关闭时操作。此前根据扩展HAL中单独调用启用宏，
错误地推断可运行时开启PLL1Q；主机假寄存器也错误允许该写入。照片证明输出未开启，
CMD0/CPSMACT无法完成。此时尚未发出介质读取，不能认定SD协议/介质类型错误或介质损坏。

音频I2C8001为BUSY/TXE，没有NACK/BERR/ARLO标志。旧1ms计时使用整数毫秒差，在
毫秒边界前开始的事务可能只剩极短时间。新增假硬件用例证明：实际远少于1ms但跨一次
毫秒跳变的正常事务会失败。它是已复现的软件缺陷，也是本次照片失败的候选解释，尚未
通过实机证明所有音频故障都由其造成；寄存器序列不因这个推断而重写。

## 修正

- `media_clock.c`统一拥有PLL2：HSE48/M12*(98+2490/8192)，P8保持49.15198MHz，
  R2给196.60791MHz。两个输出都在PLL2停机时配置，之后不再修改其因子/输出门控。
- 原生应用恢复NOR模型/校准及初始化画面后才启动媒体时钟，避免NOR保护检查碰到
  PLL正在锁定。它保持到掉电，Audio stop只停SPI/DMA/复位codec，Storage stop只
  释放SD控制器/引脚/内核选择器，互不关闭媒体时钟。CPU PLL1、LCD PLL3不动。
- SDMMC使用PLL2R，divider246得到约399.61kHz、1bit、3.3V。开始前验证媒体时钟已
  锁定及参数；不满足返回HW2，不发命令或擅自配置其他PLL/接口。只读命令白名单不变。
- 音频I2C改用128MHz下128000周期的真实1ms预算及原有有限循环上限。启用DWT
  TRCENA/CYCCNTENA，必要时依据LSR解锁LAR，不重置CYCCNT；无可用计数器则返回
  I2CFFFFFFFE。其他I2C输入的3ms保护不改，无自动重试/总线复位。
- 冷启动DWT解锁经审查发现并新增失败回归；依据
  [Zephyr v3.7 Cortex-M DWT实现](https://github.com/zephyrproject-rtos/zephyr/blob/v3.7.0/arch/arm/include/cortex_m/dwt.h#L40-L80)。

媒体时钟常开增加待机耗电，尚未测量。此策略服务未来SD读语音与音频并行；不引入
实时停启PLL的隐藏所有权切换。500ms音频初始化及2s存储总超时保持，错误快照仍保留。
现有NOR模型/校准、内部启动器、USB设置ABI与只读存储边界保持；没有文件写入/模型迁移。

## 验证与更新

49项相关检查通过（30.142秒），包括禁止运行时PLL门控写、冷启动DWT解锁、毫秒边界、
真实周期超时/回绕、Audio stop后时钟保留、存储未就绪拒绝及已有模型/Lua/输入/USB回归。
149对象ARM/加载范围通过，BSS到16KiB栈底余155048B。集中审查无剩余阻断项。

USB包 `local/tx15-usb-release/tx15-media-clock-i2c-fix-20261017.ndu`，708752B，
载荷708624B、CRC32 97153e90、API/设置ABI1，SHA256
`ec5a8ae642ad79cd7f0650c12c1c04d1fc47c018c2a353277207337b3c571923`。
旧AUD1/STO1诊断包保持原哈希，可用现有USB工具回退。没有访问或刷写设备。

下一步一次USB更新并重启（接收机断电）：Storage test STO2 → Scan一次，等3秒记录
容量/文件系统或完整错误页；再Audio test AUD2 → Play300ms一次，等2秒记录有无声音
及完整页。成功读取/发声必须由实机确认，不把49项软件检查视为硬件已通过。

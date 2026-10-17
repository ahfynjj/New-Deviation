# TX15 AUD1 / STO1 故障信息保留

2026-10-17。此版补齐诊断，未宣称修复音频或内置存储的实机故障。

用户先报告Audio test Error、Storage Error2，随后抄录：

```text
audio: test:0 dma:25 error:9 underruns:0
storage: error:0 hw:0 0mib sdsc rca:0000 unknown bas:0
         cms:0 sta:00002000 resp:00000000 reads:0
         no writes/no migration
```

保留原始拼写。storage状态名称及采集时机未知，Error0不能覆盖早先Error2的反馈。
Error2表示超时，STA2000表示CPSMACT活动；不能据此认定介质损坏或时钟故障。音频
DMA非零表明传输中断曾发生，Tests0不能证明发声成功；累计Errors并非独立尝试次数。

## 诊断字段

Audio test AUD1显示Reason、成功配置步数、最后寄存器/值、清标志前I2C状态、DMA错误
标志/SPI状态、初始化耗时/最大轮询间隔。Reason1内存约束，2传输资源占用/约束，3总超时，
4传输不可用，5页寄存器读取失败/非零，6配置写失败，7音量写失败，8DMA错误。
I2C FFFFFFFF表示未通过事务准入，不是硬件ISR；准入失败不新增ISR访问。

Storage test STO1显示状态、耗时/轮询间隔及SDMMC CLKCR/POWER/CMD、RCC PLLCFGR/
SDMMC时钟选择器。活动请求取消/超时前保存；命令完成后保留清标志前快照。审查发现
CMD17响应错误被清理再次覆盖STA，已新增失败回归并修正。Stop/退出保留故障字段，
状态可变Off；新尝试重置本次诊断。音频Tests/DMA/Errors/欠载仍为开机累计值。

没有更改初始化寄存器序列、PLL/引脚参数、协议、500ms音频/2s存储总超时。无新增
自动重试、其他接口探测、介质写入或模型迁移；启动器、NOR模型/校准格式、USB ABI不变。
快照为有限寄存器读取，没有设备端日志写入。

## 验证与一次实机采集

相关46项检查通过（29.992秒），148对象ARM构建及NDU加载范围/ABI/完整性检查通过。
故障原因、NACK保留、CMD17超时/CRC清理、页面显示均有回归。详见
[证据](evidence/2026-10-17/audio-storage-fault-capture.json)。未访问或更新设备，根因待定位。

通过现有USB工具更新 `local/tx15-usb-release/tx15-audio-storage-diag-20261017.ndu`，
重启后Storage test → Scan一次，等3秒拍完整页，再Audio test → Play300ms一次，等2秒
拍完整页。接收机保持断电，不反复点击。根据两张快照提出下一项单一修复假设。
原STO0包保留，可通过USB回退；回退不代表这两项功能曾经通过。

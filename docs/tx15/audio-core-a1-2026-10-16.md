# TX15 语音 A1 离线核心

2026-10-16。用户继续推进，并明确 AUD0“尚未更新或试听”。A0实际发声、D2 Lua、输入和RF联合验收仍未完成；本轮只实现独立于硬件的解析/转换/请求队列，不启用新的实机播放路径，不替换已有AUD0更新文件。

## 已实现

| 模块 | 行为和边界 |
|---|---|
| `src/audio/wav.{h,c}` | 增量RIFF/WAVE头解析，每次最多消费512字节；扫描未知chunk及WORD补齐，保留最多18字节头；接受mono PCM8/16、8/16/32kHz，核对byte rate/block align/实际文件与父chunk范围；拒绝浮点、压缩、立体声、不支持的采样率、截断、溢出及半个采样 |
| `src/audio/pcm.{h,c}` | unsigned8/signed16小端转signed16；8/16kHz线性插值到32kHz，32kHz直接输出；保留跨输入块的半个16位样本和插值状态；每调用最多512字节输入、256个输出样本；最后样本保持，输出长度准确；不消费声明数据后的padding或尾部 |
| `src/audio/queue.{h,c}` | 固定16请求，优先级为Lua/普通/计时器/告警，同优先级FIFO；非零事件ID合并为最新内容且不降低优先级；保留2个告警容量，必要时淘汰更低优先级；路径复制上限127字节；统计拒绝/淘汰/合并/峰值，无动态分配或文件读取 |

`nd_wav_feed`到达DATA只表示格式和声明范围已验证，停止在PCM数据起点，并不证明后续实际文件读取完整；未来文件后端仍须按data_bytes读取，PCM EOF检查会拒绝未读满的样本。解析按已取得的实际文件大小验证，RIFF之外的尾随字节不播放。

PCM输出背压时保留状态，输出容量0不吞输入；`nd_pcm_finish`在已读完样本但尚有插值输出时返回MORE，调用方继续以零输入排空。输入截断返回错误，不用补零掩盖坏文件。

队列接受仅表示复制请求，不代表文件存在、成功播放或Lua API兼容。路径规范化/目录授权属于A2文件层；队列本身只检查长度。当前没有连接正在播放的音频，清队列不停止DMA；高优先级打断播放、超时、实际欠载和1ms主循环预算由后续player实现和实测完成。数字短语不可被插入的组合机制也仍属后续阶段。

## 检查结果

6项新增主机测试包含多种分块大小/输出容量组合、metadata超过512字节、奇数chunk补齐、扩展fmt头、恶意长度、所有头截断位置、PCM极值/分裂样本/插值尾部、队列满/合并/淘汰/顺序与路径边界。每个模块均先观察新增测试失败，再实现至通过。

连同已有音频硬件、Lua、输入、模型/校准和USB包回归，共40项检查通过（27.122秒）。143对象ARM构建及原生装载验证通过；新增核心尚无产品调用，链接器移除未引用部分。构建后的ND15与既有AUD0镜像逐字节一致；现有 `tx15-audio-a0-20261016.ndu` SHA256仍为 `14cda0927eb8912cff206e06a0c0b4611ca97fb0f85afe1cc2a3a1fd015c0874`。

只读集中代码审查未发现阻断项。没有访问遥控器，没有更新其Flash，也没有读取/更改用户介质文件。软件验证和资源预算不等于真实语音文件播放及负载验收。

```powershell
$env:PYTHONPATH='utils;utils/hardware;utils/hardware/tests;.'
& 'D:\DEVI移植\tools\pyocd-venv\Scripts\python.exe' -m unittest test_audio_wav test_audio_pcm test_audio_queue
```

完整40项命令见[证据](evidence/2026-10-16/audio-core-a1.json)。ARM输出为 `local/tx15-hardware/audio-core-a1-20261016/app`；启用TX15_AUDIO=1只增加交叉编译检查，本轮没有生成新的USB包。

## 下一步

剩余A1工作：非阻塞player、内置短WAV片段、停止/抢占/超时、音频块提交接口，以及运行耗时统计。A0试听结果到位后再接实际后端；随后A2核对真实存储介质并加入异步文件读取。A1整阶段尚未完成，不把这次离线代码视为语音已可用。

RIFF布局/FOURCC/chunk长度与WORD补齐依据[Microsoft RIFF说明](https://learn.microsoft.com/en-us/windows/win32/xaudio2/resource-interchange-file-format--riff-)；采样率集合、插值方法、队列策略和每调用限额是本项目已确认计划的实施选择。

# UI04：Mixer 触摸优化

保留 Deviation 混控模型、回调和保存逻辑，将 Mixer 列表与 Simple、Complex
编辑页接入原生 480×320 卡片触摸。空通道也可以触摸选择模板。

- 列表每屏五行：点左侧通道名进入限位／虚拟通道名称，点右侧内容进入混控。
  可上下滑动翻页，也可使用 Previous／Next；顶部提供 Monitor 和 Order。
- 点参数进入编辑，出现左右 40 像素的减／加区域；每次抬手只调整一步。
  再点中间确认，短按 EXIT 也可结束编辑。滚轮操作继续保留。
- Simple 提供 Source、Curve、Scale、Offset；Complex 保留 Basic／More 两页。
  Source 的 S1/S2 捕获和 Switch 的拨动捕获继续使用原逻辑。
- Edit curve 可触摸进入曲线编辑。Expo、曲线内部、限位及排序子页仍用滚轮，
  本轮不支持曲线拖点。按页面 OK 保存，Cancel 保持原有取消语义。

触摸以抬手为触发点，拖动和长按不连发；页面、滚动位置或编辑页重建改变时，
丢弃旧手势。Map 0、进入页面后的释放门控、显示换帧及批量绘图保持不变。
不修改启动器、模型或校准格式，不修改射频、音频和存储驱动。

64 项 host 回归检查及 157 个 ARM 对象构建链接通过；独立静态审查没有重要
问题。USB 包封装、CRC、启动 API 1 和设置 ABI 1 已核对。
证据见 `evidence/2026-10-28/mixer-touch-ui04-candidate.json`。
本轮未访问或刷写遥控器，不能据此确认实机触摸手感或保存行为。

## USB 验收

固件：`local/tx15-usb-release/tx15-mixer-touch-ui04-20261028.ndu`。
使用现有专用工具，按 EXIT 开机进入 USB UPDATE 后更新，重启查看 UI04。
首次检查保持接收机断电：

1. Mixer 列表点选、滑动及翻页；物理滚轮仍能遍历各通道。
2. Simple／Complex 点参数、加减、点中间结束；短按 EXIT 结束编辑。
3. 空通道从 None 切换模板，往返切换 Simple／Complex，确认显示与触摸一致。
4. Source 捕获 S1/S2、Switch 捕获拨动；OK 保存后重启保留，Cancel 放弃修改。

原 UI03-R1 包可通过同一工具回退：
`local/tx15-usb-release/tx15-card-speed-ui03r1-20261028.ndu`。

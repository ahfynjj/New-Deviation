# UI02：480×320 原生菜单与触摸

用户在 Touch test 确认 Map 0，反馈点击基本正确；本轮固定菜单 Map 0。
仅适配 MAIN MENU、Model menu、Transmitter menu，保持 Deviation 菜单顺序、
混控、模型与保存语义。参数页和 ELRS Lua 内仍使用滚轮，后续逐页适配。

## 操作

- 主界面仍按滚轮进入 MAIN MENU。
- 菜单六行，每行 40 像素，使用已有 23bold 字体；标题区域 36 像素。
- 点菜单项，松手后进入；上下滑动翻页。底部 Back、Previous、Next。
- 滚轮、ENTER、EXIT 保留，进入未适配的参数页后继续使用它们。
- 进入菜单或从 Lua、关机倒计时返回后，需先释放屏幕才能接受新触摸。
  如果控制器没有初始零触点报告，第一次触摸/松手只解除保护，再点一次。
- Touch test 仍独立探测、使用 trial Map，诊断按钮仍通过滚轮操作。

## 实现边界

`TX15_MENU_TOUCH=1` 依赖 `TX15_TOUCH_DIAGNOSTIC=1`。保持 `HAS_TOUCH=0`，
仅经菜单自身的枚举及原有进入回调路由；避免旧参数区域接收误点。
GUI 主循环分发，硬件服务仅采样排队；切页、弹窗、Lua 与关机取消捕获。
多点、总线错误、队列溢出遵循 P1 CANCEL；滑动后回到起点也不触发点选。
500ms 以内短触才接受，跨菜单行/滚轮翻页后释放不进入原目标。
不修改 BL、模型/校准 ABI、ELRS 协议、音频驱动或显示时序。

## USB 验收

固件 `local/tx15-usb-release/tx15-menu-touch-ui02-20261027.ndu`。
保持接收机断电，按 EXIT 开机进入 USB UPDATE，以现有更新工具选择该文件。
更新完成重启，About 应为 UI02。

检查三类菜单点选、滑动、底部按钮、滚轮与 EXIT；进入 Touch test、ELRS Lua
后返回菜单，确认不会自动进入另一项；取消关机后菜单可继续操作。
再确认模型、校准、六路输入、开关与正常关机保存。连接接收机验收另行进行。
本轮未连接或刷写实机，软件检查与 ARM 构建不等于触摸精度/RF 实机验收。
显示闪烁和流畅度仍需要用户反馈，不因 UI02 构建通过而宣称解决。

回退应用包：`tx15-touch-p1-ui01-20261025.ndu`。两版均保持 boot API/settings ABI 1。

软件验证：49 项相关检查通过，156 个 ARM 对象构建和链接通过。
NDU 大小 715128 字节，SHA256：
`bd9c77b89dc18e30c90669be40979e8b6cdceb53724be7e17837518a44d8ea45`。
完整记录见 `evidence/2026-10-27/menu-touch-ui02-candidate.json`。

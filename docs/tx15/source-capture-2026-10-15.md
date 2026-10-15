# TX15 Mix 旋钮自动选源 SRC1

用户批准 S1/S2 作为连续输入源，在 Mix 的 Src 字段编辑时转动后自动选中。Switch 字段保持 SA–SF 档位捕获，旋钮不作为开关条件。本轮不启动语音实现；语音按[开发计划书](../superpowers/plans/2026-10-15-tx15-native-voice.md)后续推进。

## 使用与范围

Simple、Expo&DR、Complex 混控的 Src 均支持：短按滚轮进入橙框编辑 → 转动 S1 或 S2 → 字段选择对应旋钮 → 短按滚轮或 EXIT 锁定。进入编辑时已有旋钮位置不直接改值，未编辑时转动不抢选。保留滚轮手选所有来源、None、长按滚轮反向；自动选择保留当前反向标志，不依据旋钮正负值切换反向。EXIT 只结束字段编辑，保存整条混控仍需页面 OK。

捕获读取现有校准后的六路 ADC，只有 S1/S2 参与。相对进入编辑或上次接受的基线，累计移动达到 1000 范围单位（10 个百分点，即全行程的 5%）才触发，减轻静止抖动影响。两个旋钮同一采样同时达到门槛时只更新基线，不随意选中一个；ADC 无效期间不捕获，恢复后重新建立基线。屏蔽来源、失焦、离页、对象移除和确认退出沿用现有保护。

## 软件验证

先新增并运行失败测试，再实现：门槛/累计移动、静止位置、同时移动、ADC 失效恢复、重新编辑基线；实际 buttons.c 和 INPUT_SelectInput 链路检查确认锁定、EXIT、反向、手选、忽略来源、失焦和对象删除，以及 Src/Switch 捕获范围互不干扰。共 27 项相关检查通过，耗时 14.468 秒；136 个 ARM 对象链接和原生装载检查通过。CODE/BSS 到固定栈底尚余 2872 字节，未扩大装载范围或缩减栈。本轮没有访问设备或刷写，实机验收待反馈。

集中只读代码审查未发现阻断问题；核对了三类 Src 接入、生产回调、捕获范围和控件清理。

构建：`utils/build-tx15-app.py`，启用 TX15_STANDALONE、TX15_ELRS_PRODUCT/RC/LUA/WRITE、TX15_PERSISTENCE。输出 `local/tx15-hardware/s1-s2-source-capture-20261015/app`。

检查命令：

```powershell
$env:PYTHONPATH='utils;utils/hardware;utils/hardware/tests;.'
& 'D:\DEVI移植\tools\pyocd-venv\Scripts\python.exe' -m unittest test_source_capture test_switch_capture test_input_dashboard test_controls test_switch_upgrade test_calibration_snapshot test_rf_model test_usb_update_package
```

## USB 更新与验收

固件 `local/tx15-usb-release/tx15-s1-s2-source-capture-20261015.ndu`，About 为 `New Deviation TX15 SRC1`。使用已有专用更新工具，关机后按住 EXIT 开机进入 USB UPDATE，连接可靠数据线，连接 → 选择该文件 → 更新，等待完成；关闭工具、拔 USB，再正常关机开机。此次应用更新不改启动器、模型结构、校准布局或设置 ABI。

接收机断电即可验证：未进入编辑时转旋钮不改 Src；进入橙框后分别明显转动 S1/S2，字段应切换到对应来源；短按确认后转动不再抢选。Switch 字段拨开关仍能捕获，转旋钮不抢选。需要保留的混控按页面 OK 保存，再正常关机开机确认。软件检查不替代这些实机操作结果。

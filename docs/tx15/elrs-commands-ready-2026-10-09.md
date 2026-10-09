# TX15 ELRS 命令版更新准备 — 2026-10-09

官方ELRS Lua命令参数的软件候选已准备，当前尚未授权安装；遥控器仍运行上一校准保存版。功能和协议边界见[命令参数说明](elrs-commands-2026-10-08.md)。

## 具体更新清单

| 项目 | 冻结内容 |
| --- | --- |
| 设备 | TX15 MAX，MCU UID `1c0039000e51333234363236` |
| 调试器 | PWLINK2 CMSIS-DAP，UID `B8EFB57613B198CA10834F0545435DBB` |
| 原生应用 | ND15 694768B；编程694784B；外部擦除696320B |
| 内部启动器 | 不变，擦除/编程均0B |
| 设置区 | 外部`0xF0000`起64KiB，当前模型/校准保留 |
| 应用ELF SHA256 | `94ef4a79b00d57873bab624b167ceca25205194f9305a984fbb6b219edd551ea` |
| ND15 SHA256 | `dcfbf4aafc8dcdfcd50ed1824d3ce0f03afdfa8ce522e8801802b413367868c1` |
| 当前内部备份 SHA256 | `762b8483524abf815e1a008754055240a5eb0d9347044863492613a5f050529e` |
| 当前外部备份 SHA256 | `5dc05dc51206dd4ae4b769e285fedb1046944d7caf03869422ed62acc6ae3978` |

现场只读快照：`local/hardware-session/status-snapshot-20261009-212552.json`，状态`snapshot-verified`，Flash擦写命令0，退出CPU暂停已核对。用户断开调试器、电池后确认正常进入Deviation。该快照包含已保存的最新模型和校准，恢复不得改用早期原系统设置。

更新包：`local/tx15-hardware/install/elrs-commands-kit`。
恢复包：`local/tx15-hardware/install/elrs-commands-recovery-20261009.zip`，9610275B，SHA256 `577b035330e0f28aea0f841701902202bc155198bb3ed76c061db5ba365678dd`。
ZIP CRC检查、解包后实际`status_update.read`、事务清单/设备绑定令牌、原始备份/载荷/读取程序逐字节核对通过；运行工具源码也逐字节匹配。未物理执行此包回退，不将离线包校验等同实机恢复。

## 软件验证

`python -m unittest discover -s utils/hardware/tests`：202项通过，51.566秒，日志`local/tx15-hardware/elrs-commands/full-suite-20261009-final.log`。
随后131对象ARM产品构建通过；默认产品输出ELF、ND15、build.json与现场冻结包逐字节一致。默认离线清单入口通过，不打开调试器。

8项旧测试失败的处理：构建支持`TX15_BUILD_DIR`；RF关闭测试清除继承的TX15模式变量并使用独立临时输出，断言默认产物未变；更新测试从既有冻结真实镜像构造临时基线，继续运行生产校验；主机界面测试链接真实开关解码器，只替代主机不能访问的I2C硬件入口。旧RAM启动链应用哈希仅在测试上下文临时匹配真实RF关闭镜像，继续固定原装载器哈希，逐个破坏ELF/BIN/应用/载荷时均拒绝，并断言上下文退出恢复生产常量。生产硬件入口的候选批准常量及擦写允许列表未改。

独立上下文最终审查无Critical/Important。暂缓1项Minor：`build-tx15-app.py`外部生成C编译失败时，错误分支仍调用`relative_to(root)`，可能掩盖终端编译器错误及退出码；实际诊断保留在`compile.log`。当前构建成功，此限制不影响固件运行，未为修正它追加构建/测试循环。

## 下一次实机操作

需先取得本具体清单的人工批准。`utils/hardware/flash_install.py`明确要求：`Do not execute a write command until the human approves its concrete checklist.` 设备绑定令牌只是校验值，不等于授权。

批准后保持接收机断电，等待工具实际就绪再按住电源键，捕获供电保持后按提示松开。工具完整核对现场原内容后才擦写，更新完核对应用读回、未改动尾部和内部启动器，退出CPU暂停，再人工断电重启。

合并验收：现有模型/校准仍在；MAIN MENU进入官方ELRS Lua，确认命令项/确认或取消交互及返回；不主动触发绑定或WiFi。模块READY仅证明模块报告结束，绑定/WiFi真实结果、接收端通道和失联、外置硬件、RSSI数值解释分别待验收。

结构化证据：[validation.json](evidence/2026-10-09/elrs-commands-ready/validation.json)。

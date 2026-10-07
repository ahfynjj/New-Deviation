# TX15 校准持久化修复

实机只读诊断：校准全0，物理最低油门归一化约-9008，未过-9500门槛；模块开启但RC published/frames为0。重新校准后门槛通过，约250 RC帧/秒，短时监测LQ100且UART错误不增加，用户确认恢复连接。日志local/hardware-session/rf-live-20261007-210606.json和rf-live-after-calibration.json。该结果不是长时间可靠性或接收机通道控制验收。

修复将操纵模式和六路max/min/zero与模型1合为原双记录存储中的单次提交。52字节版本头含magic/version/model长度/mode及六路校准，拒绝非法mode和非零错误校准。可读取旧模型记录，正常保存时迁移；保存失败仍保留待保存状态。仅改变校准或模式也会触发正常关机保存。油门门槛不变。

131对象ARM构建通过；实质测试直接调用真实CONFIG_SaveModelIfNeeded、CONFIG_IsModelChanged和CONFIG_WriteModel，检查校准/模式单独变化与失败重试；双记录存储测试覆盖断写保护。集中只读审查无阻断项。旧模型读取迁移经代码审查，尚未进行真实NOR升级验收。

更新工具增加--baseline明确选择当前已安装status-kit，验证其事务和首0xf0000已安装镜像；完整保留模型区现场快照。旧更新包仍可校验，不能覆盖已有kit。下一步只读捕获当前状态，冻结calibration-kit和回退包，获得具体清单确认后刷入。首次新版启动后需校准一次，再正常关机/开机核对校准、模型和接收机连接；本轮未写Flash。

现场只读快照及冻结calibration-kit完成，应用694016字节、擦除696320字节，内部启动器和模型区不改；回退ZIP与解包校验通过。47项相关软件检查通过。新版尚未刷入，校准持久性和重启连接待验收。

## 2026-10-07 安装中止与恢复

用户已授权刷入校准保存版。安装在外部应用编程至0x50f00后，事务记录的临时文件替换触发Windows WinError 5。工具停止写入并确认CPU保持暂停；内部启动器未改，外部应用不完整，禁止正常启动。失败日志为`local/hardware-session/flash-entry-20261007-213220.json`，事务`transaction-3f9675b7cd2641c19a3557bf3925b7ab.json`为failed、sequence=1466、external_dirty=true、internal_dirty=false。

安装时曾由另一进程轮询事务文件，可能引发Windows共享冲突，具体占用进程未确认。停止读取运行中的事务文件，后续只监测工具标准输出。事务保存增加仅针对Windows错误5/32/33的有限重试（最多10次、间隔50ms），每次重试重新核对原记录，持续失败仍中止且不发送下一条硬件命令。12项事务记录测试通过，另41项Flash相关、12项安装入口及12项后端检查通过。

完整硬件工具测试201项中有8项未通过：`test_app_adapter.test_pixel_order_and_real_deviation_font_via_romfs`缺少controls链接依赖；两项boot_chain测试的固定候选哈希与当前构建不同；三项native_update测试要求旧RF-off构建；两项status_update测试在合并运行时构建元数据不匹配。不能声称完整测试套件通过；冻结calibration-kit独立校验已通过，恢复不依赖上述可变构建输出。

恢复已成功：日志`local/hardware-session/flash-entry-20261007-220446.json`为verified-halted；事务`transaction-7915105005c944b891d6ec089c797f42.json`为recovered、sequence=4229，外部1MiB和内部128KiB均与原备份完整一致，dirty标记已清除，退出CPU暂停确认通过。模型区SHA256为`7d66b222a25e93b96dbde8d9e319718387f9aade0884f15b2a512411ea4b5425`。已提示用户断电重启确认上一版正常开机，目视验收待回复。校准版本尚未成功安装，不能宣称校准已持久保存。

后续更新增加每64KiB擦除/编程标准输出进度，不再轮询正在替换的事务文件。重试须使用已冻结的calibration-kit（payload SHA256 `b3b34cd791e8ed9d7efe393653f007b0ce33c090d54c946ecf8c1c23a25ac0f5`），不能使用完整套件测试生成的RF-off工作构建；standalone构建测试会覆盖工作输出目录，是合并运行后status_update两项元数据错误的原因。

含修正工具和失败/恢复事务证据的新回退包为`local/tx15-hardware/install/calibration-recovery-20261007-v2.zip`；ZIP完整性、解包后的冻结kit及恢复令牌均校验通过。证据见[evidence/2026-10-07/calibration-recovery/validation.json](evidence/2026-10-07/calibration-recovery/validation.json)。

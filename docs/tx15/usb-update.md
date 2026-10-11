# TX15 USB 更新工具

当前阶段：Windows 工具和常驻 USB 启动器候选已构建，尚未安装到遥控器。**当前已安装固件还不能用这个工具更新。** USB 识别、完整更新包传输和 RAM 校验已通过只读实机测试；USB 擦写、常驻入口和断电重启验收仍待完成。

## 安装完成后的日常操作

1. 遥控器关机，按住 **EXIT** 再开机。看到 **USB UPDATE** 后松开按键，用可靠的数据线连接遥控器数据 USB 口和电脑。
2. 双击 `NewDeviationUpdater.exe`，选择 TX15 并点击“连接”，选择 `.ndu` 固件，再点击“更新固件”。看到“更新完成”后，正常关机并重新开机。

工具会先自动备份模型和校准。默认备份位置为 `%LOCALAPPDATA%\NewDeviation\backups\<遥控器身份>\`，也可在窗口更改位置。更新不需要填写 Flash 地址、波特率或令牌。请保留整个 `NewDeviationUpdater` 文件夹，不能只复制其中的 EXE。

传输完成和 READY 表示固件已在 RAM 中校验，只有 Flash 完整读回成功后的 DONE 才显示更新完成。若工具报告“状态未知”，保持遥控器供电，不能重复点击更新；先查看遥控器更新界面的结果。模型和校准区不在 USB 写入范围内。

## 首次安装安排

首次安装仍使用 PWLINK2。本次按用户要求跳过新增现场备份，复用已验证的既有快照，生成设备绑定清单和回退 ZIP。安装时仍完整只读比较内部 128 KiB 和外部首 1 MiB；任意字节（包括模型或校准）不同，均在擦除前停止。具体清单见 [USB 启动器首次安装](usb-boot-install-2026-10-11.md)，本次启动器写入需单独批准。安装事务会重写**相同的已安装应用前缀**，然后擦除内部 128 KiB 并安装新启动器；不会顺带安装开发中的 ELRS 命令版。正常启动、EXIT 入口、设置保留和一次真实 USB 更新均需随后验收。

USB 更新只写外部应用 `[0,0xF0000)`；`[0xF0000,0x100000)` 的模型与校准、应用以外的尾部逐字节核对。应用头最后写入。断电可能损坏单槽应用，此时应由常驻启动器进入恢复更新界面；首版没有自动回滚或断点续传。CRC 用于检测损坏，不是数字签名。

## 开发与复现

以下命令均在仓库根目录运行。构建不打开调试器、不刷写。

```powershell
D:\DEVI移植\tools\pyocd-venv\Scripts\python.exe utils/build-tx15-boot.py --usb-update --out local/tx15-hardware/boot-usb
utils/build-tx15-updater.ps1
D:\DEVI移植\tools\pyocd-venv\Scripts\python.exe -m unittest discover -s utils/hardware/tests
```

复用既有快照的离线入口是 `utils/hardware/usb_boot_update.py --reuse-snapshot --snapshot local/tx15-hardware/install/elrs-commands-kit`，不打开设备、不刷写；它读取并验证旧包中的原始快照，不使用其中尚未安装的 ELRS 命令版应用。需要新快照时，现场备份入口是 `utils/hardware/usb_boot_update.py --capture --arm`，必须在交互终端中等待真实按住电源键确认；只读 Flash，结束保持 CPU 暂停并由用户断电恢复。默认基线是已安装的 `calibration-kit`。`--install` / `--recover` 使用新的 `tx15-usb-boot-update-v1` 许可域，旧应用更新许可不能使用。未给硬件参数时，只输出离线清单。

设备枚举只匹配实验 VID/PID `CAFE/4015` 和 24 位十六进制序列号，再用 HELLO 核对 MCU UID。不自动连接 PWLINK2 或普通串口。实验 VID/PID 不代表正式分配。

固定来源：TinyUSB 0.18.0、STM32H7 CMSIS v1.10.3、CMSIS 5.9.0；快照及许可在 `third_party/usb/`。电脑端依赖固定为 pyserial 3.5 / PyInstaller 6.11.1，独立环境及交付产物在 `local/`，不提交用户备份。

当前软件和硬件证据见 [USB 实施记录](usb-progress-2026-10-11.md)。

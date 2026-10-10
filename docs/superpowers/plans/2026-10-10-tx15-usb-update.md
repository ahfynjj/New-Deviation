# TX15 USB Self-Service Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This project preserves inline execution unless the user chooses otherwise; do not dispatch task agents by default.

**Goal:** 用户脱离PWLINK2，用TX15数据USB和Windows专用工具更新原生应用，模型/校准保留，损坏应用能重新进入更新模式。

**Architecture:** 内部常驻启动器负责进入更新模式、USB CDC、完整接收和受限外部NOR事务；纯C镜像/协议/事务核心通过回调隔离硬件。Windows工具负责选设备/文件、备份、提交、真实完成反馈；首次安装启动器使用现有受限SWD路径及新设备绑定清单。

**Tech Stack:** ARM GCC8.2.1、原生C/汇编、TinyUSB0.18.0 CDC/DWC2、STM32H7/CMSIS头、Python3.11/Tkinter、pyserial3.5、PyInstaller6.11.1，既有unittest与主机GCC真实C测试。

**Spec:** `docs/superpowers/specs/2026-10-10-tx15-usb-update-design.md`，2026-10-10用户已批准；本计划待用户审阅。

## Global Constraints

- 操作：关机后EXIT+开机，接数据USB，选择`.ndu`并更新；完成后正常电源键关机/开机。首版不从应用菜单软复位进入。
- 内部Flash容量128KiB；USB模式无内部Flash/选项字节写接口。首次SWD安装的内部写入另行批准。
- 外部应用写入只在`[0,0xF0000)`；设置`[0xF0000,0x100000)`及其它NOR区域禁止写入，全片擦除禁止。
- JEDEC=`0xC84018`、容量16MiB、3字节地址、页256B、4KiB擦除`0x20`；保护/几何观察不符禁止提交。
- ND15最大`64+0x6C000+0x80000=0xEC040`字节；新镜像暂存`0xD0100000`，原首1MiB影子`0xD0200000..0xD02FFFFF`，两者互不重叠。
- 完整RAM接收/校验后才允许COMMIT；头最后编程，完整读回/再次ND15验证/设置和未改槽尾逐字节比较后才DONE。
- 两个射频模块在更新模式关闭：PB13、PD4置低；PH12供电保持不受模块操作影响。
- USB：PA11/PA12 AF10、PH5 VBUS、USB OTG_FS/rhport0、Full Speed；EXIT=PG3低有效；先板级参考，后实测。
- USB核时钟HSI48+CRS SOF同步，USBSEL=3；PLL1/PLL3配置保持原样，初始化/同步超时禁止提交。
- 用户不用安装Python、填地址/波特率/令牌。Windows10/11首版目标；CDC驱动识别必须实测。
- CRC检测损坏，不提供签名；单槽可能丢失旧应用，恢复靠内部常驻更新器，首版无自动回滚/断点续传。
- 不做触摸、TF、USB摇杆、日志平台、模型编辑器、遥控器模拟器或DFU兼容。
- 所有新构建输出独立目录；旧启动器/固件批准哈希和Flash门禁不为测试或新功能放宽。

## Review Focus

1. 接收分段/合并、重复帧或旧会话COMMIT不能造成错误偏移和二次擦写；任务2/4覆盖。
2. 电脑备份无法落盘、中文路径或用户取消时不能提交；任务5覆盖。
3. USB断开或主机超时不能把RAM接收当成完成，也不能自动重发COMMIT；任务4/5覆盖。
4. NOR操作耗时期间USB不能失去状态响应，接收缓冲不能改写已批准镜像；任务4覆盖。
5. 新启动器安装后，USB未插入的正常启动、EXIT选择和损坏镜像恢复均不能依赖已损坏应用；任务4/6覆盖。

## 文件职责与依赖固定

| 单元 | 文件 | 职责 |
| --- | --- | --- |
| 更新包 | `hardware/tx15/usb_update/package.[ch]`、`utils/usb_update/package.py`、`utils/pack-tx15-update.py` | 固定头/CRC/版本/ND15校验与产品包装 |
| 协议 | `hardware/tx15/usb_update/protocol.[ch]`、`receiver.[ch]`、`utils/usb_update/protocol.py` | 有界解析、会话、接收、不可变READY |
| USB板级 | `hardware/tx15/usb_update/usb_board.[ch]`、`usb_descriptors.c`、`tusb_config.h`、`probe_main.c` | USB时钟/供电/描述符/只读RAM诊断 |
| 更新执行 | `hardware/tx15/usb_update/transaction.[ch]`、`nor.[ch]`、`runtime.[ch]`、`screen.[ch]`、`hardware/tx15/boot/update_mode.[ch]` | 范围限定、Flash事务、屏幕、启动模式 |
| 电脑端 | `utils/usb_update/client.py`、`gui.py`、`gui_model.py`、`requirements.txt`、`utils/run-tx15-updater.py`、`utils/build-tx15-updater.ps1` | 可测试连接/备份/提交和可双击交付 |
| 构建/台架/安装 | `utils/build-tx15-usb.py`、`utils/hardware/usb_probe_session.py`、`usb_boot_update.py` | 隔离产物、只读RAM试验、一次性启动器清单 |
| 来源 | `third_party/usb/`、`docs/tx15/usb-update.md` | 最小固定依赖快照、完整许可、用户步骤/证据 |

依赖在任务3才下载/快照，不在计划阶段安装。远程标签已核对实际提交：TinyUSB0.18.0=`86ad6e56c1700e85f1c5678607a762cfe3aa2f47`，ST cmsis-device-h7 v1.10.3=`6dac8c24d7b38ab20806d27dd7d8285a6433b8f7`，CMSIS_5 5.9.0=`2b7495b8535bdcb306dac29b9ded4cfb679d7e5c`。快照保留LICENSE，仅引入CDC/device/DWC2和必须的CMSIS头，不引入HAL应用或RTOS。主机新依赖固定pyserial3.5/PyInstaller6.11.1；在独立`local/tx15-usb-venv`安装，不改现有pyocd环境。

## Task 1: `.ndu`包装及双方兼容检查

**Files:** Create `hardware/tx15/usb_update/package.[ch]`, `utils/usb_update/__init__.py`, `package.py`, `utils/pack-tx15-update.py`; Test `utils/hardware/tests/test_usb_update_package.py`, `usb_update_package_test.c`；沿用`boot/image.[ch]`、`utils/hardware/boot_image.py`。

**Interfaces:** Produces C `int tx15_update_package_validate(const uint8_t *package,size_t bytes,uint32_t boot_api,uint32_t settings_abi,struct tx15_update_package *out)`；out含`image`、`image_bytes`、`image_crc`及已验证`tx15_boot_image`。Python `pack(image:bytes,*,boot_api:int=1,settings_abi:int=1)->bytes`、`unpack(package:bytes,*,boot_api:int=1,settings_abi:int=1)->UpdatePackage`，失败ValueError/C返回0并清空out。

固定128B小端头：0..7=`ND15UPD1`；8版本1；12机型`0x54583135`；16 ND15字节数；20 ND15整体CRC32；24最低boot API；28设置ABI；32..123全0；124头前124B的CRC32；128起ND15。CRC为IEEE/zlib，不填充到Flash文件；4KiB擦除和256B页填充属于事务内部。设置ABI1绑定现有模型/校准存储布局，布局变化必须改版本，不能只凭相同ABI宣称兼容。

- [ ] 写`test_roundtrip_real_nd15_and_c_python_agree`：真实已有fixture的ND15双方通过，截断/追加/机型错/ABI2/最低API2/保留字段非0/CRC修补后语义错均拒绝；`assert len(pack(image))==128+len(image)`，C失败out无部分计划。
- [ ] 跑`python -m unittest discover -s utils/hardware/tests -p test_usb_update_package.py`，观察缺失API或接受错误包的RED。
- [ ] 实现上述API，调用已有完整ND15解析器；包装CLI要求真实产品构建`rf_enabled=true,persistent_settings=true`及ELF/ND15哈希匹配，不能把测试RF关闭产物当产品发布。
- [ ] 同一命令GREEN，另验证未改变默认app/boot冻结文件。
- [ ] 提交本任务和测试；记录格式、实际输出hash及测试结果，不访问设备。

## Task 2: 有界传输与纯RAM接收状态

**Files:** Create `protocol.[ch]`, `receiver.[ch]`, `utils/usb_update/protocol.py`; Test `test_usb_update_protocol.py`, `usb_update_receiver_test.c`。

**Interfaces:** Consumes任务1；Produces `int tx15_update_frame_feed(struct tx15_frame_parser*,const uint8_t*,size_t,tx15_frame_callback,void*)`、Python `FrameCodec.feed(bytes)->list[Frame]`；`void tx15_update_receiver_init(struct tx15_update_receiver*,uint8_t *staging,size_t capacity,uint64_t session,uint32_t boot_api,uint32_t settings_abi)`、`int tx15_update_receiver_request(struct tx15_update_receiver*,const struct tx15_frame*,struct tx15_update_reply*)`。reply含`state,error,received,total,image_crc`；正式枚举IDLE0/RECEIVING1/VALIDATING2/READY3/ERASING4/PROGRAMMING5/VERIFYING6/DONE7/ERROR8，错误0表示无错误。

帧固定32B小端头：magic=`NDU1`、version u8=1、type u8、flags u16=0、session u64、sequence/offset/payload_bytes各u32、CRC32 u32，payload最多1024B；CRC覆盖头前28B及payload。opcode HELLO1/BEGIN2/DATA3/FINALIZE4/STATUS5/READ_SETTINGS6/COMMIT7/ABORT8；响应同opcode|0x80，错误细节属于响应，未知opcode不改变状态。HELLO session0；BEGIN携带任务1的128B头；staging前128B存该头，DATA偏移为ND15内部偏移，写staging+128+offset，保证任务1完整包校验API可直接使用。capacity至少128+ND15长度。FINALIZE空payload。接收模式30秒无数据超时丢弃RAM会话，不擦写；整个接收上限5分钟。

HELLO响应48B：UID12B；API、设置ABI、最大ND15长度、能力flags、JEDEC、容量、页字节数、擦除字节数各u32；最后SR1/SR2/SR3和SFDP已验证标志各u8。能力bit0=read_only、bit1=写入观察通过。session来自响应帧头，不信任USB字符串独立授权。状态/控制响应24B：state,error,received,total,image_crc,verification_flags各u32，末字段bit0仅完整读回DONE时设置。READ_SETTINGS请求payload为u32长度1..1024，帧offset为设置区内偏移，响应原始数据并回显偏移；提交期间拒绝此新读取。COMMIT payload=UID12B+image_bytes u32+image_crc u32；其frame session和READY冻结信息都须一致。Python同任务定义`DeviceInfo`（上述HELLO字段及session）、`DeviceStatus`（上述状态字段）供任务5使用。

- [ ] 写`test_stream_split_merge_noise_and_length_overflow`和`test_receiver_replay_gap_timeout_and_ready_immutable`：所有拆分点和合并均解码一次；超长帧/旧session/错CRC拒绝；顺序数据完整才READY，重复同序号/偏移逐字节一致才ACK；数据空洞/重复内容不同/READY后改包均拒绝，硬件写调用计数始终0。
- [ ] 跑`python -m unittest discover -s utils/hardware/tests -p test_usb_update_protocol.py`观察RED。
- [ ] 实现解析和接收，固定缓冲/边界检查；COMMIT只交付已验证只读包描述，不在本任务实现写入。ABORT仅在提交前生效；重连清解析/会话，DATA等待超时后旧包不能提交。
- [ ] 同一命令GREEN，并用Python帧驱动真实C接收器，覆盖32位offset回绕及最大镜像边界。
- [ ] 提交并记录接口；不得连接探针或创建自动烧录动作。

## Task 3: USB CDC与只读RAM实机入口

**Files:** Create `usb_board.[ch]`, `usb_descriptors.c`, `tusb_config.h`, `probe_main.c`, `utils/build-tx15-usb.py`, `utils/hardware/usb_probe_session.py`, `third_party/usb/`; Test `test_usb_board.py`, `test_usb_probe_session.py`, `test_usb_probe_build.py`。USB专用startup可以从已审查boot reset代码派生到`hardware/tx15/usb_update/startup.S`，不覆盖legacy输出。

**Interfaces:** `int tx15_usb_init(void)`返回0仅在时钟/供电/外设初始化成功；`void tx15_usb_poll(void)`、`size_t tx15_usb_read(uint8_t*,size_t)`、`size_t tx15_usb_write(const uint8_t*,size_t)`、`void tx15_usb_stop(void)`、`uint32_t tx15_usb_ms(void)`、`int tx15_usb_new_session(uint64_t*)`。后者使用硬件RNG生成非0会话，失败禁止提交；USB reset/reconnect更新会话。探针只读模式HELLO返回12B UID、协议API1、ABI1、最大ND15长度、read_only=true；COMMIT/NOR写功能不链接。

- [ ] 写USB寄存器边界和超时测试：PLL1/PLL3/供电PH12不变；HSI48未ready或USB供电不ready失败，错误时不返回可写设备；指向HSI48选择3。测试`probe_session`在未arm/未知candidate/hash错/无held时不能上传，任何路径保持halt、不调用Flash backend。
- [ ] 跑`python -m unittest discover -s utils/hardware/tests -p 'test_usb_*'`观察本任务缺失接口RED；旧任务仍通过。
- [ ] 固定最小依赖并实现GPIO、HSI48/CRS/供电、rhport0 CDC、SysTick/OTG_FS IRQ；描述符产品`New Deviation TX15 Updater`，USB序列号取MCU UID；实验VID/PID可配置，不宣称正式分配。USB缓冲必须可访问且初始化符合ECC，cache/MPU保持关。
- [ ] 增加隔离模式`python utils/build-tx15-usb.py --probe --out local/tx15-hardware/usb-probe`，RAM链接和二进制hash/来源manifest通过；构建禁用/不链接NOR写代码。`usb_probe_session.py --candidate ...`默认只校验，不打开探针；`--arm`才在实际供电按键确认后复位捕获/UID核对/上传完整读回/启动，60秒后halt，所有错误出口不恢复旧PC。禁止改legacy批准常量；新允许写地址仅为审核后的RAM/控制寄存器。
- [ ] 同一软件命令GREEN、真实ARM链接和大小检查；提交。随后一次合并实机只读验收：Windows出现CDC设备、HELLO UID正确、连续分片信息传输、拔插重连、read_only拒绝COMMIT；记录USB识别和传输结果，不写Flash。结束人工恢复正常启动。不方便实测时继续任务4/5软件工作，明确硬件证据缺口。

## Task 4: 常驻入口及受限NOR事务

**Files:** Create `transaction.[ch]`, `nor.[ch]`, `runtime.[ch]`, `screen.[ch]`, `hardware/tx15/boot/update_mode.[ch]`; Modify `hardware/tx15/boot/main.c`, `startup.S`, `boot.ld`, `utils/build-tx15-boot.py`；Test `test_usb_update_transaction.py`, `usb_update_transaction_test.c`, `test_usb_boot_mode.py`, `test_usb_boot_build.py`。

**Interfaces:** 消费任务1/2/3。`struct tx15_update_io`包含ctx、`observe(ctx,struct tx15_update_flash_info*)`、`read(ctx,offset,dst,n)`、`erase4k(ctx,offset)`、`program(ctx,offset,src,n)`、`service(ctx)`；完整操作成功返回1，失败0。flash_info含JEDEC/容量/页/擦除/3个状态寄存器/SFDP已验证标志。`int tx15_update_tx_prepare(struct tx15_update_tx*,const struct tx15_update_io*,const struct tx15_update_package*,uint8_t *shadow,size_t capacity)`核对并备份首1MiB；`int tx15_update_tx_step(struct tx15_update_tx*)`每次推进一个受限动作，返回0进行中/1 DONE/-1 ERROR；`int tx15_boot_update_mode(unsigned exit_stable,enum tx15_boot_load_result result)`返回0 normal/1 updater。runtime对所有COMMIT字段核对后才调用prepare，进入事务后RAM镜像/版本/范围不可改。

- [ ] 写失败注入测试：每个擦除/编程阶段取消供电模型、保护/几何错、读回任一字节错、设置或尾部变化均不能DONE；所有写地址 `<0xF0000`，所有页不跨256B；实际头写晚于正文；原设置/尾部逐字节不变。提交前USB中断写计数0，提交后USB丢失仍可完成同一冻结事务，重复COMMIT写计数不增加。USB服务回调期间恶意DATA/BEGIN/ABORT不能改变镜像。
- [ ] 跑`python -m unittest discover -s utils/hardware/tests -p 'test_usb_*'`观察事务/模式RED。
- [ ] 实现严格NOR观察、状态允许掩码沿用`flash_geometry.assess`，SFDP边界逻辑与已有Python参考进行同fixture对照；读/擦/编程地址只经受限函数，明确无全擦/内部/选项字节接口。busy等待有上限并调用USB service，只响应状态；防止嵌套step。从shadow中比较设置及未触及尾部，重新验证Flash完整ND15。
- [ ] 实现BOOT模式选择和更新屏幕（等待/接收/校验/写入/完成/错误），EXIT上拉30ms稳定采样，不依赖应用或I2C；应用READ_ERROR/BAD_IMAGE进入更新器，其它初始化错误不授权写入。先释放电源键20ms，随后2秒长按在非写入阶段关机；写入阶段不软件关机。正常模式保持旧handoff/ECC初始化，USB IRQ仅更新模式启用。
- [ ] 独立构建`python utils/build-tx15-boot.py --usb-update --out local/tx15-hardware/boot-usb`，不改默认boot/boot-chain产物；128KiB/56KiB布局、704B向量、stackless供电、正常copy STRD和IRQ归属通过。同一软件命令GREEN，追加正常/强制USB/损坏应用模式真实C检查，提交。

## Task 5: Windows备份/更新工具及可双击交付

**Files:** Create `utils/usb_update/client.py`, `gui_model.py`, `gui.py`, `requirements.txt`, `utils/run-tx15-updater.py`, `utils/build-tx15-updater.ps1`; Test `test_usb_update_client.py`, `test_usb_updater_gui_model.py`；Modify打包CLI的产品输出接入（任务1文件）。

**Interfaces:** 消费Python包/FrameCodec及任务2的DeviceInfo/DeviceStatus。`UpdaterClient(transport,backup_dir:Path,progress:Callable)`，transport提供`read(n:int)->bytes`, `write(bytes)->int`, `close()`；`connect()->DeviceInfo`, `prepare(package:bytes)->PreparedUpdate`, `commit(prepared:PreparedUpdate)->UpdateResult`, `status()->DeviceStatus`。PreparedUpdate绑定UID/session/image_crc和已验证落盘备份路径；UpdateResult只有DONE且verification_flags bit0=1才success=true。`UpdaterModel`提供可测连接/文件/按钮使能和状态，不在Tk线程执行串口/备份/写入。

- [ ] 写`test_backup_failure_and_cancel_never_commit`、`test_wrong_device_and_reconnect_invalidate_prepared`、`test_commit_timeout_queries_without_resend`：中文/空格路径备份64KiB+UID+SHA正确；磁盘满/fsync或读回失败COMMIT帧数0；PWLINK2/普通COM描述符不自动连接，UID变或session变需重新准备；断连返回未知状态，不返回成功、不重复COMMIT。GUI模型READY/数据传完不能显示成功，实际DONE可显示完成。
- [ ] 跑`python -m unittest discover -s utils/hardware/tests -p 'test_usb_update_client.py'`及`-p 'test_usb_updater_gui_model.py'`观察RED。
- [ ] 实现读取受限设置备份，使用原子保存/fsync并重新读取SHA核对；默认`%LOCALAPPDATA%/NewDeviation/backups/<UID>/`，用户可选择可写目录。支持串口partial write/read，COMMIT仅一次，超时只查询，不静默跨设备/会话继续；窗体只有设备、连接、文件、更新、进度及明确结果。
- [ ] 隔离安装固定主机依赖，打包为onedir Windows程序`local/tx15-usb-release/NewDeviationUpdater/NewDeviationUpdater.exe`（用户双击）；新进程在未连接设备时启动可观察，记录窗口截图/启动证据，不自动点击更新。同一软件命令GREEN；在无开发venv的运行环境验证程序能打开，不能把打包成功当USB更新成功。
- [ ] 提交源码/锁定依赖/使用说明；大体积依赖产物、固件、用户备份留local，不提交个人数据。

## Task 6: 一次性USB启动器安装包、整体验收与交接

**Files:** Create `utils/hardware/usb_boot_update.py`, `test_usb_boot_update_kit.py`, `docs/tx15/usb-update.md`, `docs/tx15/evidence/2026-10-10/usb-update/validation.json`; Modify `TODO.md`。仅必要时扩展`flash_journal.py`/`install_entry.py`的不同kit读入口，旧批准常量保持原样。

**Interfaces:** `usb_boot_update.prepare(root,folder,baseline_folder,internal:bytes,external:bytes)->USBInstallKit`、`read(folder)->USBInstallKit`，严格当前已安装baseline及活跃installed记录；`USBInstallKit.approval(action:str)->str`域`tx15-usb-boot-update-v1`绑定实际UID/事务hash，新包不能借用旧许可。内部新boot ELF/BIN经`boot_elf.parse`及相互核对；应用使用已安装baseline的真实ELF/ND15，必须与现场应用一致，不顺带安装未批准ELRS命令版。

- [ ] 写`test_usb_boot_kit_preserves_live_app_models_and_requires_new_approval`：新boot被正确布局验证，旧应用及最新模型/校准原样；任意文件/hash/baseline/UID或旧令牌错在开探针前拒绝；新boot不能被legacy kit默认为已批准。离线恢复ZIP解包后实际read/逐字节校验通过。
- [ ] 跑新kit测试RED；实现独立kit读取/冻结。一次性SWD采用已有完整Transaction/Journal路径：它会先重写相同的已安装应用前缀，再安装新内部启动器；具体清单如实列外部擦除/编程及内部128KiB擦除，不假称只写boot。模型区和未触及尾部仍不变；恢复包绑定本次现场首1MiB/内部128KiB。默认CLI离线，不打开设备；capture只读，install/recover分别需明确具体包批准。
- [ ] 同一新kit测试GREEN；运行完整`python -m unittest discover -s utils/hardware/tests`、隔离USB boot/probe构建和当前产品包装/hash核对。一轮最终独立审查，仅修Critical/Important并按RED→GREEN验证；Minor记入交接，不重复多轮审查。
- [ ] 现场只读备份并正常恢复 → 展示真实冻结清单/回退包 → 得到具体刷入授权 → 用PWLINK2安装/读回/暂停退出 → 用户正常断电冷启动。设计/计划许可不等于这次写入许可。
- [ ] 合并USB实机验收：正常启动和原模型/校准、EXIT+开机、Windows连接/备份、一次实际USB应用更新及最终DONE、正常电源键关机开机、输入和ELRS基本保留。错误文件及提交前取消不得修改Flash；损坏镜像恢复入口先用只读RAM故障注入触发验证路径，真实应用损坏后的重启/恢复另列明确台架安排与授权，不提前声称通过。
- [ ] 更新源码/测试/构建/枚举/擦写/读回/用户验收各层证据与TODO，提交推送；交付EXE、`.ndu`、现场恢复ZIP和两步日常操作说明。缺物理证据时保留pending，不因已构建宣称交付完成。

## 自检与执行交接

规格覆盖：进入/退出/供电→任务3/4；包/兼容→1；协议/重连→2/3；事务/恢复→4/6；备份/GUI/交付→5；一次性授权安装→6。接口名称及包/帧字段在生产者和消费者一致；5项Review Focus均有所属测试。USB库和Python依赖已有确定版本/提交，实际安装安排在实施阶段。

规划修正：原设计的PLL2Q不是H750 USB可选时钟，修为HSI48+CRS；依据ST官方RCC定义，不改变操作流程或显示主频。成本：USB同步稳定性仍需任务3实测，失败时不得继续Flash写入。

首个用户可见结果是USB识别和只读HELLO，不先修改已安装应用；下一次用户配合只在实际RAM工具就绪后发出，避免空等待。后续日常升级由用户在专用工具操作，无聊天按键同步。完整新启动器永久安装仍单独审阅具体刷入清单。

待用户审阅本计划后，按已沿用的本会话直接实施方式逐任务推进；本计划阶段无依赖安装、产品代码修改、设备访问或Flash写入。

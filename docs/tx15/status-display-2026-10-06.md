# TX15 电压与信号显示

目的：显示真实电池电压和ELRS接收端RSSI/LQ，退出Lua后仍更新，遥测过期显示NO LINK。

ADC3轮询PH3/channel14，12bit，HCLK/4，长采样；独立于ADC1六路输入。原生换算使用3300mV参考及100k/32k分压，暂未进行万用表校准。初始化或转换失败显示未知电压。

CRSF 0x14数据每模块独立CRC解码，长度错误或LQ越界不采纳，LQ=0或超过3秒无数据不显示有效连接。当前同时开启两模块时主页面优先显示内置；Lua所选目标不影响双模块常驻接收。

固定硬件参考：EdgeTX f5c13ab13ecadf3689c5854cfba51c43646fceec，boards/hw_defs/tx15.json、boards/rm-h750/board.h、boards/generic_stm32/battery_voltage.cpp。参考仅用于引脚/分压，不采用其应用框架。

18项离线检查通过，131对象ARM候选构建通过；未刷入。下一步必须从已安装ELRS版本准备新的更新和恢复包，并读取/保留用户已经保存的0xf0000起64KiB设置区。旧controls→ELRS包不能用于本次更新。实机验收：电池电压对照万用表；已绑定接收机上电产生RSSI/LQ，退出Lua仍更新，接收机断电后变为NO LINK。

2026-10-06 更新准备完成：只读实机完整读取128KiB内部和外部首1MiB，已安装应用核对通过，现场模型区完整保存；日志status-snapshot-20261006-095157.json。冻结status-kit应用693504字节，擦除696320字节，内部启动器不改，模型区不擦写。ZIP回退包及解包后完整校验通过。41项更新/显示/事务相关检查通过；审查发现的active记录路径校验已补回并添加失败回归。与实机只读会话并行运行事务锁测试会触发锁保护，结束会话后顺序重跑全部通过。下一步经具体清单确认后刷入，接收端信号和电压精度仍未实测。

只读备份：`python utils/hardware/status_update.py --capture --arm --press-window 600 --swd-frequency 500000`（需要真实按键配合，已有kit不得覆盖）。离线检查：`python utils/hardware/status_update.py`。安装/恢复需要冻结kit对应的完整approval，不能复用其它版本token。恢复流程会还原捕获时的完整模型区；安装后新修改的模型须另行备份。

2026-10-06 用户明确同意刷入后，status-kit安装完成：应用读回及外部剩余区域、内部128KiB比较通过；事务installed，模型区保持原值，退出CPU暂停。日志flash-entry-20261006-101238.json。待用户断电重启后的电压/模型保留/信号验收。

用户重启后确认“电压显示8.18 ，模型设置有”：电压显示及模型保留验收通过；尚未对照万用表，不宣称电压精度通过。RSSI/LQ接收端验收仍待进行。

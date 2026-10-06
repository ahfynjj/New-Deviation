# TX15 电压与信号显示

目的：显示真实电池电压和ELRS接收端RSSI/LQ，退出Lua后仍更新，遥测过期显示NO LINK。

ADC3轮询PH3/channel14，12bit，HCLK/4，长采样；独立于ADC1六路输入。原生换算使用3300mV参考及100k/32k分压，暂未进行万用表校准。初始化或转换失败显示未知电压。

CRSF 0x14数据每模块独立CRC解码，长度错误或LQ越界不采纳，LQ=0或超过3秒无数据不显示有效连接。当前同时开启两模块时主页面优先显示内置；Lua所选目标不影响双模块常驻接收。

固定硬件参考：EdgeTX f5c13ab13ecadf3689c5854cfba51c43646fceec，boards/hw_defs/tx15.json、boards/rm-h750/board.h、boards/generic_stm32/battery_voltage.cpp。参考仅用于引脚/分压，不采用其应用框架。

18项离线检查通过，131对象ARM候选构建通过；未刷入。下一步必须从已安装ELRS版本准备新的更新和恢复包，并读取/保留用户已经保存的0xf0000起64KiB设置区。旧controls→ELRS包不能用于本次更新。实机验收：电池电压对照万用表；已绑定接收机上电产生RSSI/LQ，退出Lua仍更新，接收机断电后变为NO LINK。

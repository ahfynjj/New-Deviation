# 源码来源记录

## 应用主体

New Deviation 基于 DeviationTX/deviation，基线 `330193b9a4185f6a2cdc3af90d654169cd210094`。保留上游 Git 历史、版权和 LICENSE.TXT。示例显示驱动文件头写明 GPLv3 或更新版本。

libopencm3 固定 `d55bbafddb9768228748f48a82967f91a910806e`，通过原子模块配置取得；保持其自己的许可和版权。

## 硬件参考

EdgeTX `f5c13ab13ecadf3689c5854cfba51c43646fceec`：读取 TX15 目标、rm-h750 板驱动、hw_defs/tx15.json、stm32h750_sdram 链接布局和 elf2uf2.py。参考副本位于项目仓库外的 `D:\DEVI移植\tools\reference\edgetx`，不参与 New Deviation 编译。

EdgeTX 根 LICENSE 为 GPLv2，读取的部分驱动头同样写明 version 2。不能据“两者都是开源”就判定可直接混合发布。当前没有把这些驱动实现复制进本项目；进入 P2 时先逐文件核对许可、独立第三方来源和复用条件。对未明确可复用的实现，以硬件资料为依据独立实现平台接口。

## 工具链

工具只安装在 `D:\DEVI移植\tools`，不提交二进制依赖、不修改全局 PATH。

- MSYS2 基础归档：官方 release 2026-06-11，`msys2-base-x86_64-20260611.tar.xz`，SHA256 `a2d047e8ee213c3c6a49a8de427eb1069df12207c0422ff1b3cbb5c905c34221`，与 GitHub release asset digest 一致。
- ARM GCC：Deviation 官方构建说明提供的 Arm 下载地址，8-2018-q4-major Windows 包，SHA256 `be5e2f68549efaecb79bdc34ff03c06f27deb2fcec3badddb5729cfb5ce43d6b`；该值是本次下载的记录，不声称与独立官方签名比对。
- MSYS2 软件包通过 pacman 签名验证；实际安装版本在构建记录中列出。

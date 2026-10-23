# v0.1.3 · 首个公开预览版

HANDS OVER Demo × 郊狼 3.0 联动，支持 DG-LAB 4 与兼容扫码。手机设置 A/B 上限，电脑分别按“通道上限 × 真假结果比例”输出实际强度；默认假牙 20%、真牙 100%。连接设备就绪并读到所选通道上限后自动启用联动；手动测试可在游戏未运行时使用。

## 下载

- 普通使用：`HandsOverDGLab-0.1.3-windows-x64.zip`。解压后先读使用说明，退出游戏再运行“安装模组”。首次安装需联网从 BepInEx 官方取得固定 build 790，安装脚本自动校验 SHA-256。
- 对应完整应用源码：`*-application-source.zip`。运行包内部也包含同一份源码、构建脚本及许可证。
- 外部 LGPL 框架对应源码：`*-LGPL-framework-sources.zip`，含固定 BepInEx、Il2CppInterop 和 UnityDoorstop 的完整上游源码及构建文件。
- 校验：`*-SHA256SUMS.txt` 覆盖三个附件。

要求 Windows 10/11 x64。桌面程序已含 Python；如缺少 VC++ v14 x64，请从[微软官方页面](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)安装。本包不镜像 Windows CRT / API-set DLL，也不镜像整个加载器和 mini-CoreCLR。

## 本次分发整理

- 桌面默认 GPL-3.0-only；原创事件插件另为 MIT。补齐官方 SDK 原有 GPL LICENSE，保留第三方版权、复合许可、Roboto 字体与 CPython Windows 发行许可。
- 提供同一 Release 的应用和 LGPL 源码、固定来源与哈希、外部库替换/重新链接说明。
- 构建时隔离其他工具 PATH，原生依赖逐个核对来源和哈希，禁止未核对的系统兼容 DLL 混入公开包。
- 安装/卸载继续检查冲突并记录文件；不会覆盖其他来源的不同文件或删除用户修改的模组文件。

## 验证范围

本地单元与集成检查、独立桌面启动自检、二维码控件生命周期以及安装/卸载恢复均会在发布前执行。Windows CI 随仓库提供。

这是预览版。BepInEx 已在本机成功生成 v39 互操作程序集并加载插件进入菜单；完整多人对局中房主/加入者、普通/危险牙齿、保护/陷阱卡的实机验收仍待完成。旧波形比例模式曾由本人确认设备有输出；当前上限数值模式仍需本人核对设备实际数值及中断效果。不要把模拟 APP 或菜单加载成功当作全部设备、游戏验收完成。

详细来源与许可见 [THIRD-PARTY-NOTICES.md](https://github.com/Ghostknife11/HandsOverDGLab/blob/main/THIRD-PARTY-NOTICES.md)、[框架源码安排](https://github.com/Ghostknife11/HandsOverDGLab/blob/main/docs/FRAMEWORK-SOURCE.zh-CN.md)和 [Windows 运行库分发记录](https://github.com/Ghostknife11/HandsOverDGLab/blob/main/docs/WINDOWS-RUNTIME.zh-CN.md)。

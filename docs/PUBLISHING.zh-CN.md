# GitHub 公开发行与重建

当前公开版本：0.1.3 预览版。仓库为 [Ghostknife11/HandsOverDGLab](https://github.com/Ghostknife11/HandsOverDGLab)，每个 Release 将运行包和对应源码放在同一个下载页面。

## 发行附件

- `HandsOverDGLab-0.1.3-windows-x64.zip`：桌面 EXE、原创插件 DLL、安装/卸载/启动脚本、完整许可材料、原生依赖来源记录、内置的完整应用源码。
- `*-application-source.zip`：与该次运行包对应的完整应用源码、官方固定 SDK、构建脚本、依赖版本、测试和说明。它与运行包内 `source/HandsOverDGLab` 来自同一次导出。
- `*-LGPL-framework-sources.zip`：固定 BepInEx、Il2CppInterop、UnityDoorstop 的完整未修改源码归档、原有构建文件、许可证、来源和哈希。
- `*-SHA256SUMS.txt`：上述三个附件的 SHA-256。运行包另含逐文件 SHA256.json；应用源码另含 SOURCE-SHA256.json。

每次修改应用并重建，都重新生成全部对应材料。不能仅更新 EXE 后继续把不匹配的旧源码附件当作该版本源码。

## 许可证与实际边界

默认 **GPL-3.0-only**；桌面实际导入的官方 SDK 自带 GPL v3。原创 `plugin/` 另外按 MIT 提供；第三方保留原许可，范围见 [COPYRIGHT.md](../COPYRIGHT.md) 和 [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md)。不要在 GitHub 套用 MIT 模板覆盖根目录 LICENSE。

0.1.3 公开包不镜像整个加载器和 mini-CoreCLR。安装脚本直接从 BepInEx 官方取得固定 build 790 归档，验证 SHA-256 后执行冲突检查和安装。用户可自行提供 `-FrameworkPath` 离线安装或替换外部库。精确 LGPL 源码在同一 Release 实际提供，另见 [FRAMEWORK-SOURCE.zh-CN.md](FRAMEWORK-SOURCE.zh-CN.md)，包括修改、替换和重新链接说明。

桌面 EXE 自带 CPython 运行环境。保留完整 PSF Windows 安装许可、标准库第三方原文、Pillow 复合许可、Roboto 字体许可等。公开包排除 API-set、UCRT 和 VC++ runtime DLL；使用 Windows 系统组件与微软官方 x64 v14 安装器。每个实际保留原生文件的来源与哈希由构建记录，详见 [WINDOWS-RUNTIME.zh-CN.md](WINDOWS-RUNTIME.zh-CN.md)。

这是具体版本的来源、文件与许可证核对记录，不承诺未知未来依赖也自动满足同样条件。更换 Python、wheel、框架或打包工具时需更新记录并重新检查。

## 保留与排除

源码导出使用 `scripts/source_export.py` 的允许列表，包含本项目代码、固定 SDK、测试、构建/安装脚本、许可证、来源与文档。排除游戏 DLL、interop、素材、运行环境、build/dist/release、日志、安装清单、本机配置、手机配对标识、缓存和 .env。

`G:\dglab` 里仍保留旧个人运行包供本机回退；0.1.0～0.1.2 不上传 GitHub Release。那些旧包曾漏 SDK LICENSE、未包含对应应用源码，并从其他工具 PATH 收集了部分兼容 DLL；0.1.3 重新构建，不能通过给旧包补一份总许可证来代替核对。

## 重建

1. 准备 Python 3.13.9、.NET SDK 和本人已合法安装的游戏。
2. 创建虚拟环境并安装 `requirements-dev.txt`；运行依赖见 requirements.txt，构建依赖另有 requirements-build.txt。
3. 运行 `scripts/bootstrap.py` 获取固定加载器。也可直接从官方取得文档记录的固定归档并核对哈希。
4. 安装加载器，启动本人游戏一次生成 interop，随后退出游戏。interop 不进入 GitHub；必要时给 .NET 构建传入本人 `GamePath`。
5. `python -m unittest discover -s tests -v` 执行本地检查。
6. `python scripts/build_release.py` 构建并生成三个 ZIP 与 SHA256SUMS。此过程会限制打包 PATH、拒绝未审核来源的原生依赖、逐文件校验来源哈希，并在仅含 Windows 系统目录的 PATH 下执行独立 EXE 的 Tk/二维码/波形自检。
7. 对照生成包的 SHA256.json、应用源码清单、LICENSES/desktop-native-origin.json 和固定框架源码清单。执行安装冲突、升级和卸载恢复检查后再上传附件。

仓库附 Windows CI。完整多人游戏、实际设备强度与中断验收状态必须按 README 如实保留，不能把单元测试或菜单加载成功改写为全部实测通过。

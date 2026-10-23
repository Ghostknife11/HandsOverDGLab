# 第三方组件、来源与许可证

核对日期：2026-10-23。范围：本仓库源码、0.1.3 公开包及外部依赖，以及用于版本对照的旧 0.1.2 本地完整包。不同发行形式包含的文件不同；下列“随本地完整包”不代表源码仓库内含该二进制。

本项目原创代码的许可范围见 [COPYRIGHT.md](COPYRIGHT.md)。默认 GPL-3.0-only；`plugin/` 原创代码另按 MIT 提供。**第三方代码不因根目录 LICENSE 而被重新许可。**

## 直接引入的 DG-LAB 官方 SDK 与波形

| 项目 | 固定版本 / 来源 | 用途 | 许可证与保留内容 |
| --- | --- | --- | --- |
| [dglab-kit-python](https://github.com/dungeonlab-open/dglab-kit-python) | 提交 `4cce771c0fd93d043f3e83bbb0467e4197cde62e`，包版本 0.1.0，作者元数据 LF112 | V3/V4 WebSocket、事件、任务、设备状态；源码位于 `desktop/vendor/dglab_kit_python/` | [上游 GPL v3 原文](https://github.com/dungeonlab-open/dglab-kit-python/blob/4cce771c0fd93d043f3e83bbb0467e4197cde62e/LICENSE)；本地 [vendor/LICENSE](desktop/vendor/LICENSE) 与 [来源记录](desktop/vendor/ORIGIN.md) |
| SDK 官方郊狼波形 | 同一提交的 `waveform/coyote.py` | GUI 内置 24 种波形，包括“气泡” | 属于上述 GPL v3 SDK；保留作者来源，不宣称为本项目原创 |

2026-10-23 比较本地与固定提交归档，13 个 SDK 源文件/类型标记文件逐字节一致。所有项目适配在 `desktop/handsover/`，未改写 vendored SDK。

**更正：旧本地包 `THIRD-PARTY-NOTICES.txt` 中 “The pinned SDK archive has no standalone LICENSE file” 是错误陈述。原始 SDK 归档有 GPL v3 LICENSE，旧打包流程漏收集。不能据此把桌面程序仅按 MIT 或 BSD 发布。**

## Python 桌面程序

以下许可证原文已保留在 [LICENSES/python-packages/](LICENSES/python-packages/)。各许可证内原有版权、免责声明及 Pillow 的原生库条款均需保留。

| 组件 | 核对版本 | 作用 | 许可证 / 主要权利人 |
| --- | --- | --- | --- |
| [websockets](https://github.com/python-websockets/websockets) | 15.0.1 | WebSocket 传输 | BSD-3-Clause，Aymeric Augustin 及贡献者 |
| [python-qrcode](https://github.com/lincolnloop/python-qrcode) | 8.2 | 二维码生成 | BSD-3-Clause；原派生部分保留 MIT 声明，Lincoln Loop、Kazuhiko Arase 等 |
| [Pillow](https://github.com/python-pillow/Pillow) | 13.0.0 | 二维码图像、Tk 显示、构建图标 | MIT-CMU；另含原生依赖许可证，Secret Labs、Fredrik Lundh、Alex Clark 及贡献者 |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | 5.2.2 | GUI 控件、主题及资产 | **MIT**，Tom Schimansky；以实际 LICENSE 为准，其 METADATA 的 CC0 字段与 LICENSE 不一致 |
| [darkdetect](https://github.com/albertosottile/darkdetect) | 0.8.0 | CustomTkinter 依赖 | BSD-3-Clause，Alberto Sottile |
| [packaging](https://github.com/pypa/packaging) | 26.3 | CustomTkinter 版本处理 | Apache-2.0 **或** BSD-2-Clause；保留两份原文与选择声明 |
| [colorama](https://github.com/tartley/colorama) | 0.4.6 | qrcode 的 Windows 安装依赖，主要用于命令行 | BSD-3-Clause；本 GUI 未调用彩色终端功能，不以“已安装”推定一定嵌入 EXE |

## 随桌面运行环境出现的组件与字体

| 组件 | 核对版本 | 来源与许可证 |
| --- | --- | --- |
| [CPython](https://github.com/python/cpython/tree/v3.13.9) 与标准库 / Tkinter | 3.13.9 | PSF-2.0 及 LICENSE 中列出的历史许可；`LICENSES/Python-3.13.9.txt` |
| [Tcl](https://github.com/tcltk/tcl/tree/core-8-6-15) / Tk | 8.6.15 | Tcl/Tk BSD 风格许可；`LICENSES/tcltk-tcl.txt`、`LICENSES/Tk-8.6.15.txt` |
| [OpenSSL](https://github.com/openssl/openssl/tree/openssl-3.0.18) | 3.0.18 | Apache-2.0；`LICENSES/openssl-openssl.txt` |
| [libffi](https://github.com/libffi/libffi/tree/v3.4.4) | 3.4.4 | MIT；`LICENSES/libffi-libffi.txt` |
| [Roboto](https://github.com/googlefonts/roboto) | 字体自身元数据 `Version 2.137; 2017` | Apache-2.0，Copyright 2011 Google Inc.；通过 CustomTkinter 资产收集；`LICENSES/Roboto-Apache-2.0.txt` |
| CustomTkinter shapes font、默认图标与主题 | 随 CustomTkinter 5.2.2 | 归该项目许可范围，保留 MIT 原文；本项目 H 图标为自行绘制 |
| Pillow 原生库 | 由当前 wheel 内 LICENSE 列明 | 不能统称为 MIT：包括 Brotli、FreeType、HarfBuzz、LittleCMS、libavif、libjpeg-turbo、libpng、libwebp、OpenJPEG、libtiff、xz、zlib-ng 等；保留 Pillow **整份** LICENSE |
| CPython 其他原生依赖 | 固定 CPython 构建配置 | 包括 bzip2 1.0.8、mpdecimal 4.0.0、xz 5.2.5、zlib 1.3.1，详见 [CPython 获取依赖脚本](https://github.com/python/cpython/blob/v3.13.9/PCbuild/get_externals.bat)；已保留完整 Windows 发行许可、CPython 第三方条款和额外原生库原文；运行包原生文件另附来源哈希清单 |
| Windows CRT / API 运行库 | Windows 10/11 与官方 VC++ v14 x64 | 0.1.3 不镜像 `VCRUNTIME*`、`MSVCP*`、`CONCRT*`、`ucrtbase.dll`、`api-ms-win-*` 或 `ext-ms-win-*`。由 Windows / 微软官方安装程序提供；详见 [Windows 运行环境记录](docs/WINDOWS-RUNTIME.zh-CN.md) |

界面使用 Windows 自带 Microsoft YaHei UI 字体；未把该字体文件复制进源码包。0.1.3 的 H 图标改为几何图形绘制，不读取微软字体。旧本地版本曾读取 Segoe UI 字形生成 ICO，但未复制字体文件。

## 游戏侧与 BepInEx 发行包

插件通过独立 DLL 引用下列组件。`Private=false` 防止把游戏引用复制为本插件产物。源码仓库不包含这些二进制；0.1.2 本地完整包的 `framework/` 则包含官方加载器及其依赖。

| 组件 / 对应文件 | 本地核对版本 | 来源 / 许可证 |
| --- | --- | --- |
| BepInEx Core、Preloader、Unity Common、Unity IL2CPP | `6.0.0-be.790+4e98359b51c48f103f948c57faca3be20027407a` | [BepInEx](https://github.com/BepInEx/BepInEx/tree/4e98359b51c48f103f948c57faca3be20027407a)，LGPL-2.1-only，由固定提交 `Directory.Build.props` 明确声明 |
| UnityDoorstop，`winhttp.dll` | 4.6.0 | [NeighTools/UnityDoorstop](https://github.com/NeighTools/UnityDoorstop/tree/v4.6.0)，LGPL-2.1 |
| HarmonyX，`0Harmony.dll` | 2.10.2 | [BepInEx/HarmonyX](https://github.com/BepInEx/HarmonyX/tree/v2.10.2)，MIT；**该文件来自 HarmonyX，不应错写成另一个 Harmony 版本** |
| Il2CppInterop Common / Generator / Runtime / HarmonySupport | `1.5.3+dbda1cb353b0f4253345dc45136d170b9e50a5a0` | [BepInEx/Il2CppInterop](https://github.com/BepInEx/Il2CppInterop/tree/dbda1cb353b0f4253345dc45136d170b9e50a5a0)，LGPL-3.0；上游许可证文件已包含 GPL v3 正文 |
| AsmResolver 四个程序集 | `6.0.0-beta.5+124e161a9bc0ebb83b4d97276ae3da3c9cfe2fc5` | [Washi1337/AsmResolver](https://github.com/Washi1337/AsmResolver/tree/124e161a9bc0ebb83b4d97276ae3da3c9cfe2fc5)，MIT |
| AssetRipper.CIL | `1.2.2+06216e69825ccd6536dc17e9ca81c4d539ce9321` | [AssetRipper.CIL](https://github.com/AssetRipper/AssetRipper.CIL/tree/06216e69825ccd6536dc17e9ca81c4d539ce9321)，MIT |
| AssetRipper.Primitives | `3.2.0+d759b3db98bf2a1cb8c2181faf5d405610aac585` | [AssetRipper.Primitives](https://github.com/AssetRipper/AssetRipper.Primitives/tree/d759b3db98bf2a1cb8c2181faf5d405610aac585)，MIT，NuGet 3.2.0 元数据明确声明 |
| Cpp2IL.Core、LibCpp2IL、StableNameDotNet、WasmDisassembler | development.1452 / `558ddd98642010897d54316b51fbaa7889fda093` | [SamboyCoding/Cpp2IL](https://github.com/SamboyCoding/Cpp2IL/tree/558ddd98642010897d54316b51fbaa7889fda093)，MIT |
| Disarm | master.99 / `8574010015c8c56bb7faad7e407c50b0abe9cc72` | [SamboyCoding/Disarm](https://github.com/SamboyCoding/Disarm/tree/8574010015c8c56bb7faad7e407c50b0abe9cc72)，MIT |
| Dobby，`dobby.dll` | 1.0.5，由 BepInEx 固定构建脚本确认 | [BepInEx/Dobby](https://github.com/BepInEx/Dobby/tree/v1.0.5)，Apache-2.0 |
| Gee.External.Capstone | `2.3.2+b90e380c14e857865c94a355954236e678bd557c` | [9ee1/Capstone.NET](https://github.com/9ee1/Capstone.NET/tree/b90e380c14e857865c94a355954236e678bd557c)，MIT；不要混同 Capstone 引擎的许可证 |
| Iced | 1.21.0 | [icedland/iced](https://github.com/icedland/iced/tree/v1.21.0)，MIT |
| Mono.Cecil、Mdb / Pdb / Rocks | 0.11.4.0 | [jbevain/cecil](https://github.com/jbevain/cecil/tree/0.11.4)，MIT |
| MonoMod.RuntimeDetour、MonoMod.Utils、ILHelpers | 22.07.31.01，ILHelpers 文件未声明版本 | [MonoMod/MonoMod](https://github.com/MonoMod/MonoMod/tree/v22.07.31.01)，MIT；ILHelpers 不虚构版本号 |
| MonoMod.Backports | `1.1.2+a1b82852b2574742776af08818487b90b0bfab93` | [MonoMod/MonoMod](https://github.com/MonoMod/MonoMod/tree/a1b82852b2574742776af08818487b90b0bfab93)，MIT |
| SemanticVersioning | 2.0.2 | [adamreeve/semver.net](https://github.com/adamreeve/semver.net)，MIT；未从该 DLL 确定提交，不虚构固定提交 |
| 精简 .NET / CoreCLR 及 System.* / Microsoft.* 库 | 6.0.7 | [BepInEx/dotnet-runtime](https://github.com/BepInEx/dotnet-runtime/tree/6.0.7)，MIT 及其第三方声明，不等同于“所有 Microsoft 文件都属于同一许可证” |

**0.1.3 采用外部加载器边界：公开包不镜像 `framework/` 或 mini-CoreCLR；安装时由用户电脑直接从固定官方 URL 取得原始归档并强制校验 SHA-256。** 同一 Release 另实际提供 BepInEx、Il2CppInterop、UnityDoorstop 三个固定版本完整源码归档（包括构建脚本和许可），下载信息与哈希见 [framework-sources.json](LICENSES/framework-sources.json)，替换与重新链接见 [框架源码说明](docs/FRAMEWORK-SOURCE.zh-CN.md)。

HANDS OVER Demo 的 `GameAssembly.dll`、`global-metadata.dat`、`Jaws.*`、`UnityEngine.*`、`Unity.Netcode.*` 及生成的 `BepInEx/interop/` 仅作本地分析/编译/运行引用，不作为本项目开源内容上传。用户须自行合法安装游戏并生成 interop。

## 仅构建、测试或研究使用

| 项目 | 核对版本 | 用途 / 许可证 |
| --- | --- | --- |
| PyInstaller | 6.16.0 | 打包；GPL-2.0-or-later **带 Bootloader exception**，部分运行钩子 Apache-2.0；[官方说明](https://pyinstaller.org/en/v6.16.0/license.html)。此例外不会消除 DG-LAB SDK 的 GPL v3 义务 |
| pyinstaller-hooks-contrib | 2026.9 | 收集依赖的构建钩子；GPL-2.0-or-later / Apache-2.0，按文件原文与例外 |
| altgraph | 0.17.5 | PyInstaller 构建依赖，MIT |
| pefile | 2023.2.7 | PE 分析 / 打包，MIT |
| pywin32-ctypes | 0.2.3 | PyInstaller Windows 构建依赖，BSD-3-Clause |
| setuptools | 84.2.1 | 构建工具依赖，MIT，附带组件按其许可证 |
| zxing-cpp | 2.3.0 | 二维码回读测试，Apache-2.0；未被桌面入口引用，不作为 GUI 必需库 |
| .NET SDK | 本机 8.0.422 / 10.0.301、10.0.302 | 编译工具；不随插件源码/插件 DLL 分发；目标框架 net6.0，不等于要求最终用户安装这些 SDK |
| LLVM objdump | 本机研究工具 | 仅用于定位事件；Apache-2.0 WITH LLVM-exception；未复制工具到项目或发布包 |

第三方 Python 发行元数据与实际许可证文件索引见 [LICENSES/python-packages.json](LICENSES/python-packages.json)。有冲突时以所核对源码/发行包内实际许可证原文为准，不只依赖 pip 的单个 License 字段。

## 仅参考的协议与文档

- [DG-LAB 蓝牙与波形协议](https://github.com/dungeonlab-open/dglab-bluetooth-protocol/blob/main/coyote/README_CN.md)：核对郊狼 3.0 帧格式。
- [DG-LAB TypeScript SDK 文档](https://github.com/dungeonlab-open/dglab-kit/blob/main/README_CN.md)：核对 V4 二维码、任务和上限字段；本项目没有引入其 TypeScript SDK 包。
- [官方兼容中继源码](https://github.com/dungeonlab-open/dglab-websocket-simple/tree/main/socket/v2/backend/src)：核对真实中继消息含义；本项目没有内置或运行该服务器，也没有复制其服务器实现。
- 官方 `wss://trex.dungeon-lab.cn/v4` 与 `wss://ws.dungeon-lab.cn` 是外部服务地址，服务本身不属于本仓库，也不由本项目许可证授权。

源码上传与 EXE 发布是两个检查范围。0.1.3 的实际附件、源码对应关系及旧包不再公开镜像的范围，见 [发布核对说明](docs/PUBLISHING.zh-CN.md)。

## 0.1.3 原生依赖补充材料

`LICENSES/Python-3.13.9-Windows-distribution.txt` 保留 PSF Windows 安装原文及微软 Distributable Code 附加说明；`CPython-3.13.9-third-party.rst` 保留该提交标准库第三方许可。另有 Expat 2.7.3（MIT）、mpdecimal 4.0.0（BSD-2-Clause）、HACL*（MIT）、XZ 5.2.5 liblzma（public domain 声明）与 zlib 1.3.1 的适用原文。`Python-3.13.9-upstream.spdx.json` 是整个官方安装器的来源证据，不代表全部安装器内容进入本 GUI；实际原生文件以运行包 `LICENSES/desktop-native-origin.json` 为准。

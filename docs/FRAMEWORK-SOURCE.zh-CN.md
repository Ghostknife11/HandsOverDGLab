# LGPL 框架源码与替换说明

适用版本：HandsOverDGLab 0.1.3；对应外部加载器为 BepInEx Unity IL2CPP Windows x64 `6.0.0-be.790+4e98359`。

## 从同一个 Release 取得源码

本项目 [v0.1.3 Release](https://github.com/Ghostknife11/HandsOverDGLab/releases/tag/v0.1.3) 同时提供 `*-LGPL-framework-sources.zip`。内含下列三个**完整、未修改的上游源码归档**，各自原有的构建文件、版权和许可证均保留。归档没有 Git 子模块；不以几个选出的接口文件代替库源码。

| 组件 | 与本地官方二进制核对的版本 | 固定源码 |
| --- | --- | --- |
| BepInEx Core / Preloader / Unity Common / Unity IL2CPP | 6.0.0-be.790 | `BepInEx/BepInEx@4e98359b51c48f103f948c57faca3be20027407a` |
| Il2CppInterop Common / Generator / Runtime / HarmonySupport | 1.5.3 | `BepInEx/Il2CppInterop@dbda1cb353b0f4253345dc45136d170b9e50a5a0` |
| UnityDoorstop / winhttp.dll | 4.6.0 | `NeighTools/UnityDoorstop@v4.6.0` |

下载地址、源码归档 SHA-256 和许可见仓库 [LICENSES/framework-sources.json](../LICENSES/framework-sources.json)，官方二进制版本及逐文件哈希见 [LICENSES/framework-binaries.json](../LICENSES/framework-binaries.json)。源码归档是随本次 Release 实际提供的文件，不依赖未来上游网站一直可用，也不是仅提供一个没有版本的首页链接。Release 外层 SHA256SUMS 同时覆盖运行包、应用源码包和 LGPL 源码包。

`scripts/prepare_compliance.py` 会校验固定哈希后组装此源码包；若内容损坏或出现未经核对的子模块则停止。无需付费即可下载。源码仍按各库的 LGPL 原文许可，根目录 GPL 或原创插件的 MIT 不能覆盖第三方权利。

## 构建与安装修改版

三个归档都带原有构建入口。BepInEx 归档的 `.github/workflows/build.yml`、`build/Program.cs` 和 `build.sh` 记录其构建流程；Il2CppInterop 带 `build.cake` 和 .NET 项目文件；UnityDoorstop 带 `build.bat` / `build.sh`、`xmake.lua` 和平台 C 源码。

- BepInEx 使用 .NET SDK 8 和 Git；上游构建脚本会读取提交信息。可从记录的仓库克隆并检出上述提交，以保留 Git 上下文，再运行 `./build.sh --target Compile --build-type BleedingEdge --build-id 790`；只构建本地库不需要上游发布密钥。直接从 ZIP 构建时可使用相应项目文件与 `dotnet build -c Release`，版本属性应按上述提交设置。
- Il2CppInterop 可在源码根目录用 `dotnet build -c Release`，或按原有 Cake 脚本构建。保留项目文件中固定的 NuGet 依赖，编译输出的目标框架需与所选加载器兼容。
- UnityDoorstop 使用上游 xmake 流程与 Windows C 工具链，按归档内 Windows 构建入口选择 x64、Release。输出作为代理 DLL 使用，安装路径为游戏根目录 `winhttp.dll`。

以上提供源码和构建路径；本次没有宣称已将整个上游框架重建到与官方签名、时间戳和哈希逐字节一致。本项目自己的插件和桌面程序另由 `scripts/build_release.py` 构建；插件编译还需本人本地游戏生成的 interop，游戏文件不随源码发布。

退出游戏后，可以在游戏目录替换 `BepInEx/core/BepInEx.*.dll`、`BepInEx/core/Il2CppInterop.*.dll` 和根目录 `winhttp.dll` 为接口兼容的修改版。程序没有针对这些外部库设置签名白名单或运行时哈希锁定；安装脚本拒绝覆盖用户改过的文件，是为了保留修改，不限制运行修改版。需要升级时可先备份修改，再自行合并。

本项目允许为修改这些库和调试修改版而进行必要的逆向工程，不另设禁止条款；保留 LGPL 及 GPL 授予的修改、重新链接和分发权利。库通过外部独立 DLL 加载，不内嵌进本项目桌面 EXE 或插件 DLL；本项目插件完整源码和项目文件也随包提供。

## 二进制取得边界

0.1.3 的公开运行包**不镜像 `framework/` 或 mini-CoreCLR**。安装脚本直接从 BepInEx 官方服务器取得固定完整归档，先验证 SHA-256，再执行原有的冲突检查、复制和安装记录。支持用户显式提供本地 `-FrameworkPath`，用于离线安装或使用修改版。

官方归档：[build 790 Windows x64 IL2CPP](https://builds.bepinex.dev/projects/bepinex_be/790/BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.790%2B4e98359.zip)。SHA-256：`7e2c83e38db7744d6457839bc869b311aa29a47517938a3a7643be24d00c72ec`。

本项目提供上述 LGPL 源码包，方便使用者取得准确版本并维护修改。MIT / Apache 等其他外部框架库的来源和许可仍见第三方来源表；不把 LGPL 源码包描述为整个 .NET 或游戏运行环境的全部源码。

# Windows 运行环境来源与分发记录

核对日期：2026-10-23；适用于公开发行版 0.1.3，Windows 10/11 x64。

## 发行包的实际边界

| 文件 / 组件 | 0.1.3 的处理 | 依据与证据 |
| --- | --- | --- |
| `api-ms-win-*.dll`、`ext-ms-win-*.dll`、`ucrtbase.dll` | 不随公开包复制；由 Windows 提供 | [微软 UCRT 部署说明](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment)：UCRT 是 Windows 10 以后的系统组件 |
| `VCRUNTIME*.dll`、`MSVCP*.dll`、`CONCRT*.dll` | 不随包镜像或自动安装；需要时由用户从微软官方安装 x64 VC++ v14 运行库 | [微软官方下载与许可说明](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)，[官方 x64 安装程序](https://aka.ms/vc14/vc_redist.x64.exe)；这类文件不按本项目 GPL 重新许可 |
| `python313.dll`、标准库、Python `.pyd` | 来源为 PSF 官方 Python 3.13.9 Windows x64 安装程序；保留完整 Windows 发行许可及第三方声明 | [官方发行页](https://www.python.org/downloads/release/python-3139/)、`LICENSES/Python-3.13.9-Windows-distribution.txt` 和 `CPython-3.13.9-third-party.rst` |
| `libssl-3.dll`、`libcrypto-3.dll`、`libffi-8.dll`、`tcl86t.dll`、`tk86t.dll`、`zlib1.dll` 等被收集的原生依赖 | 仅接受来自上述 Python 安装或已记录 Python wheel 的文件；逐文件记录来源与 SHA-256 | 运行包 `LICENSES/desktop-native-origin.json`，适用许可证原文见 `LICENSES/` |
| Pillow 的原生扩展 / 内置图像库 | 来自固定 Pillow wheel；保留整份复合许可，不能笼统改写成 MIT | `LICENSES/python-packages/pillow/`；包括 FreeType 等原文 |
| PyInstaller 启动器与运行钩子 | 来自固定 6.16.0 wheel；保留其许可证、Bootloader exception 与 Apache 部分 | `LICENSES/python-packages/pyinstaller/`，固定构建依赖见 requirements-build.txt |
| BepInEx 的 `dotnet/`、mini-CoreCLR 与其中 Microsoft 文件 | 不镜像到公开运行包；安装时由用户的电脑直接获取固定官方加载器归档 | `scripts/Get-OfficialFramework.ps1` 的官方 URL 与强制 SHA-256；独立外部运行环境不能统称为本项目 GPL/MIT 资产 |

Python 官方安装程序 `python-3.13.9-amd64.exe` SHA-256：`200ddff856bbff949d2cc1be42e8807c07538abd6b6966d5113a094cf628c5c5`。本地完整安装的 `LICENSE.txt` 比源码根目录通用 LICENSE 更长，包含 Windows 发行的微软 Distributable Code 附加说明、bzip2、libffi、Tcl/Tk 等内容；本次保留整份，不能只拿 13 KB 的通用 PSF 文本替代它。附加条件只针对相应微软代码，不改变用户编写的 Python 程序的许可。

保留上游官方安装程序的 [SPDX 清单](https://www.python.org/ftp/python/3.13.9/python-3.13.9-amd64.exe.spdx.json) 到 `LICENSES/Python-3.13.9-upstream.spdx.json` 作为来源证据。该文件描述整个上游安装器，包含 pip 等**不一定被本 GUI 收集的内容**；实际随本 GUI 运行的原生文件以构建后 `desktop-native-origin.json` 为准。上游清单中的 `NOASSERTION` 不等于没有许可证。

原生库相关原文还包括：Expat 2.7.3（MIT）、mpdecimal 4.0.0（BSD-2-Clause）、HACL*（MIT）、XZ 5.2.5 的 liblzma（上游 public domain 声明）、zlib 1.3.1（zlib）、OpenSSL 3.0.18（Apache-2.0）、libffi 3.4.4（MIT），以及 CPython 归档内标准库第三方声明。

## 构建时如何阻止混入

1. 构建子进程的 PATH 只保留选定 Python 与 Windows 系统目录，排除其他桌面工具的库目录。
2. PyInstaller 收集完成后，在打包前去掉系统 CRT、API-set 和 VC++ DLL。保留下来的每个原生依赖必须位于固定 Python 或该虚拟环境的包目录，否则构建失败。
3. 每个实际复制的原生依赖再次对照来源哈希；整个最终包再扫描一次被排除的名称。不能只看源码没有引用某个 DLL，就断言包里没有它。
4. 独立 EXE 在仅含 Windows 系统目录的 PATH 下运行 `--self-check`，检查 Python、真实 Tk 图片控件和波形生成；不连接实际设备，不发送刺激。

`启动联动.cmd` 会检查系统中的 VC++ 关键文件并在缺失时给出微软官方下载地址。检查文件存在只是启动提示，不保证其版本足够；若仍出现运行库缺失或版本错误，请从上述官方地址修复安装最新适用 x64 v14 运行库。本程序无需系统 Python。

0.1.0～0.1.2 的旧本地完整包没有经过这套分发边界核对，不作为本次 GitHub Release 附件上传。0.1.3 的记录针对重新构建的实际产物，不给旧文件补贴一个许可标签。

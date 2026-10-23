# DG-LAB Python SDK 来源

- 上游：<https://github.com/dungeonlab-open/dglab-kit-python>
- 固定提交：`4cce771c0fd93d043f3e83bbb0467e4197cde62e`
- 来源目录：上游 `src/dglab_kit_python/`
- 本地目录：`desktop/vendor/dglab_kit_python/`
- 上游包版本：`0.1.0`，作者元数据：LF112。
- 许可证：GNU GPL version 3；完整原文见本目录 `LICENSE`。
- 本项目保守按 `GPL-3.0-only` 分发与之组合的桌面应用，不据此假定上游授予了未来版本许可。

2026-10-23 逐文件比较，13 个上游源码/类型标记文件均与固定提交归档完全相同。未对 vendored SDK 源码进行修改。本项目的设备状态处理、兼容协议适配、上限百分比计算位于 `desktop/handsover/`。

官方波形数据也来自该 SDK 的 `waveform/coyote.py`，不是本项目原创波形。OVC 波形随上游包保留，但当前程序不控制 OVC 设备。

此前本地调试包声称该 SDK 没有独立 LICENSE，此说法错误：原始归档包含 LICENSE，之前只是漏收集进发布包。本文件及根目录第三方说明予以更正。

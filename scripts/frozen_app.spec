# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import json
import sys
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(root / 'scripts'))
from release_policy import excluded_runtime, native_origin, digest

datas, binaries, hiddenimports = collect_all('customtkinter')
datas.append((str(root / 'desktop/assets'), 'assets'))
a = Analysis([str(root / 'desktop/main.py')],
    pathex=[str(root / 'desktop'), str(root / 'desktop/vendor')],
    binaries=binaries, datas=datas, hiddenimports=hiddenimports,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0)

# Windows 10/11 supply the API sets and UCRT. MSVC v14 is an external
# prerequisite. Never copy them from a developer's PATH or Python installation.
excluded = []
reviewed = []
kept = []
for destination, source, kind in a.binaries:
    if excluded_runtime(destination):
        excluded.append({'file': destination, 'sha256': digest(source),
            'disposition': 'excluded; use Windows or Microsoft official VC++ installer'})
        continue
    reviewed.append({'file': destination, 'sha256': digest(source),
        'origin': native_origin(source, sys.base_prefix, Path(sys.prefix) / 'Lib/site-packages')})
    kept.append((destination, source, kind))
a.binaries = kept
(root / 'build').mkdir(exist_ok=True)
(root / 'build/desktop-native-origin.json').write_text(json.dumps({
    'python': sys.version.split()[0], 'included': reviewed, 'excluded': excluded}, indent=2) + '\n', encoding='utf-8')
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='HandsOverDGLab',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, icon=str(root / 'desktop/assets/app.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='HandsOverDGLab')

# SPDX-License-Identifier: GPL-3.0-only
"""Build the public Windows package, source assets and redistribution inventory."""
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from source_export import export_source
from prepare_compliance import prepare
from release_policy import excluded_runtime, digest

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.3'


def run(args, env=None):
    subprocess.run([str(v) for v in args], cwd=ROOT, check=True, env=env)


def main():
    if sys.version_info[:3] != (3, 13, 9):
        raise RuntimeError('Use the audited CPython 3.13.9 Windows installation for this release')
    from importlib.metadata import version
    for name in ('requirements.txt', 'requirements-build.txt'):
        for line in (ROOT / name).read_text(encoding='utf-8').splitlines():
            if '==' not in line or line.startswith('#'): continue
            distribution, expected = line.split('==')
            distribution = distribution.split('[')[0]
            if version(distribution) != expected:
                raise RuntimeError('Build dependency differs from reviewed pin: ' + distribution)
    from PIL import Image, ImageDraw
    assets = ROOT / 'desktop/assets'
    assets.mkdir(parents=True, exist_ok=True)
    icon = Image.new('RGBA', (256, 256), (13, 17, 24, 255))
    canvas = ImageDraw.Draw(icon)
    canvas.rounded_rectangle((12, 12, 244, 244), radius=62, fill='#C6ED80')
    # Geometric H; no system font file or font glyph needed for this asset.
    for rectangle in ((70, 62, 96, 194), (160, 62, 186, 194), (96, 115, 160, 141)):
        canvas.rectangle(rectangle, fill='#0D1118')
    icon.save(assets / 'app.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    dotnet = shutil.which('dotnet') or 'C:/Program Files/dotnet/dotnet.exe'
    run([dotnet, 'build', 'plugin/HandsOverDGLab.csproj', '-c', 'Release', '--nologo'])
    for folder in ('build', 'dist', 'release'):
        (ROOT / folder).mkdir(exist_ok=True)
    env = os.environ.copy()
    # Do not let unrelated developer tools supply native DLLs to the bundle.
    env['PATH'] = os.pathsep.join([str(Path(sys.executable).parent), sys.base_prefix,
        str(Path(sys.base_prefix) / 'DLLs'), str(Path(env['WINDIR']) / 'System32'), env['WINDIR']])
    env['PYTHONUTF8'] = '1'
    run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--distpath', 'dist', '--workpath', 'build/frozen', 'scripts/frozen_app.spec'], env=env)
    package = ROOT / 'release' / f'HandsOverDGLab-{VERSION}-windows-x64'
    if package.exists(): package = package.with_name(package.name + '-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    package.mkdir()
    shutil.copytree(ROOT / 'dist/HandsOverDGLab', package / 'app')
    (package / 'plugin').mkdir()
    shutil.copy2(ROOT / 'plugin/bin/Release/net6.0/HandsOverDGLab.dll', package / 'plugin')
    (package / 'scripts').mkdir()
    for name in ('Install.ps1', 'Uninstall.ps1', 'Get-OfficialFramework.ps1', 'Start.ps1'):
        source = ROOT / 'scripts' / name
        # Windows PowerShell 5 needs a BOM for Chinese source text.
        (package / 'scripts' / name).write_text(source.read_text(encoding='utf-8-sig'), encoding='utf-8-sig')
    shutil.copy2(ROOT / 'README.md', package / '使用说明.md')
    commands = {
        '启动联动.cmd': '@echo off\r\nchcp 65001 >nul\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\\Start.ps1"\r\nif errorlevel 1 pause\r\n',
        '安装模组.cmd': '@echo off\r\nchcp 65001 >nul\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\\Install.ps1" %*\r\npause\r\n',
        '卸载模组.cmd': '@echo off\r\nchcp 65001 >nul\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\\Uninstall.ps1" %*\r\npause\r\n'}
    for name, content in commands.items(): (package / name).write_bytes(content.encode('utf-8'))
    shutil.copytree(ROOT / 'LICENSES', package / 'LICENSES',
        ignore=shutil.ignore_patterns('__pycache__', '*.py', '*.pyc', '*.pyo'))
    shutil.copytree(ROOT / 'docs', package / 'docs')
    for name in ('LICENSE', 'COPYRIGHT.md', 'THIRD-PARTY-NOTICES.md'):
        shutil.copy2(ROOT / name, package / name)
    shutil.copy2(ROOT / 'desktop/vendor/LICENSE', package / 'LICENSES/dglab-kit-python-GPL-3.0.txt')
    shutil.copy2(ROOT / 'plugin/LICENSE', package / 'plugin/LICENSE')
    source = export_source(package / 'source/HandsOverDGLab')
    (package / 'SOURCE-AND-LICENSE.txt').write_text(
        'Complete application source: source/HandsOverDGLab/ (GPL-3.0-only; see COPYRIGHT.md).\n'
        'The same GitHub Release also supplies the matching application-source ZIP and\n'
        'LGPL-framework-sources ZIP with the pinned BepInEx, UnityDoorstop and Il2CppInterop sources.\n'
        'Loader binaries / mini-CoreCLR are NOT mirrored in this public package.\n'
        'Install.ps1 obtains the original fixed official loader archive and verifies SHA-256.\n'
        'Required: Windows 10/11 x64 and official Microsoft Visual C++ v14 x64 runtime.\n'
        'Microsoft CRT and API-set DLLs are NOT distributed here.\n'
        'See docs/FRAMEWORK-SOURCE.zh-CN.md and docs/WINDOWS-RUNTIME.zh-CN.md.\n', encoding='utf-8')
    native = json.loads((ROOT / 'build/desktop-native-origin.json').read_text(encoding='utf-8'))
    # Provenance must match copied files, rather than just Analysis input.
    for entry in native['included']:
        binary = package / 'app/_internal' / entry['file']
        if digest(binary) != entry['sha256']: raise RuntimeError('Native output changed: ' + entry['file'])
    forbidden = [p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file() and excluded_runtime(p.name)]
    if forbidden: raise RuntimeError('Unexpected Windows runtime redistribution: ' + repr(forbidden))
    (package / 'LICENSES/desktop-native-origin.json').write_text(json.dumps(native, indent=2) + '\n', encoding='utf-8')
    report = ROOT / 'build/bundle-self-check-0.1.3.json'
    clean_env = env.copy()
    clean_env['PATH'] = str(Path(env['WINDIR']) / 'System32') + os.pathsep + env['WINDIR']
    run([package / 'app/HandsOverDGLab.exe', '--self-check', report], env=clean_env)
    check = json.loads(report.read_text(encoding='utf-8'))
    if not check.get('ok') or not check.get('frozen'): raise RuntimeError('Standalone self-check failed')
    native['validation'] = {'standalone_self_check': 'passed', 'python_on_path': False,
        'framework_binaries_mirrored': False, 'windows_runtime_dlls_in_package': forbidden}
    (package / 'LICENSES/desktop-native-origin.json').write_text(json.dumps(native, indent=2) + '\n', encoding='utf-8')
    manifest = {p.relative_to(package).as_posix(): digest(p) for p in sorted(package.rglob('*')) if p.is_file()}
    (package / 'SHA256.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    asset_base = ROOT / 'release' / f'HandsOverDGLab-{VERSION}-windows-x64'
    archive = Path(shutil.make_archive(str(asset_base), 'zip', root_dir=package.parent, base_dir=package.name))
    source_zip = Path(shutil.make_archive(str(asset_base) + '-application-source', 'zip', root_dir=source.parent, base_dir=source.name))
    framework_zip = prepare(Path(str(asset_base) + '-LGPL-framework-sources.zip'))
    files = (archive, source_zip, framework_zip)
    sums = Path(str(asset_base) + '-SHA256SUMS.txt')
    sums.write_text(''.join(digest(p) + '  ' + p.name + '\n' for p in files), encoding='utf-8')
    print(json.dumps({'version': VERSION, 'directory': str(package), 'assets': [str(p) for p in (*files, sums)],
        'self_check': check, 'native_files': len(native['included'])}, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__': main()

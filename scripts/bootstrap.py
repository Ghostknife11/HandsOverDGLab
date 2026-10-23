# SPDX-License-Identifier: GPL-3.0-only
"""Fetch pinned, official development dependencies; never modifies PATH."""
from pathlib import Path
import hashlib, json, shutil, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.tools'
DOWNLOADS = ROOT / '.downloads'
SDK_COMMIT = '4cce771c0fd93d043f3e83bbb0467e4197cde62e'

def download(url, name):
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOADS / name
    if not dest.exists():
        req = urllib.request.Request(url, headers={'User-Agent': 'HandsOverDGLab/0.1'})
        with urllib.request.urlopen(req, timeout=120) as src, dest.with_suffix('.partial').open('wb') as out:
            shutil.copyfileobj(src, out)
        dest.with_suffix('.partial').replace(dest)
    print(name, dest.stat().st_size, hashlib.sha256(dest.read_bytes()).hexdigest(), flush=True)
    return dest

def extract(archive, dest):
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if not (dest / item.filename).resolve().is_relative_to(dest.resolve()):
                raise ValueError('Archive path escaped destination')
        z.extractall(dest)

if __name__ == '__main__':
    TOOLS.mkdir(parents=True, exist_ok=True)
    bep = download('https://builds.bepinex.dev/projects/bepinex_be/790/BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.790%2B4e98359.zip', 'BepInEx-790.zip')
    extract(bep, TOOLS / 'bepinex')
    sdk = download(f'https://codeload.github.com/dungeonlab-open/dglab-kit-python/zip/{SDK_COMMIT}', 'dglab-kit-python-pinned.zip')
    extract(sdk, TOOLS / 'sdk-source')
    py = download('https://www.python.org/ftp/python/3.13.9/python-3.13.9-amd64.exe', 'python-3.13.9-amd64.exe')
    records = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [bep, sdk, py]}
    (DOWNLOADS / 'sha256.json').write_text(json.dumps(records, indent=2) + '\n')

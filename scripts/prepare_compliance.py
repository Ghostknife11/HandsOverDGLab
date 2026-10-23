# SPDX-License-Identifier: GPL-3.0-only
"""Fetch pinned LGPL source archives and assemble the same-release source asset."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def prepare(destination):
    cache = ROOT / '.audit-cache/framework-sources'
    cache.mkdir(parents=True, exist_ok=True)
    records = json.loads((ROOT / 'LICENSES/framework-sources.json').read_text(encoding='utf-8'))
    for record in records:
        path = cache / record['archive']
        if not path.exists():
            req = urllib.request.Request(record['url'], headers={'User-Agent': 'HandsOverDGLab-source/0.1.3'})
            with urllib.request.urlopen(req, timeout=60) as response:
                payload = response.read()
            if hashlib.sha256(payload).hexdigest() != record['sha256']:
                raise ValueError('Source archive hash mismatch: ' + record['component'])
            path.write_bytes(payload)
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Cached source archive hash mismatch: ' + record['component'])
        with zipfile.ZipFile(path) as source:
            if source.testzip() is not None: raise ValueError('Damaged source ZIP')
            if any(n.endswith('/.gitmodules') for n in source.namelist()):
                raise ValueError('Submodule sources require a fresh review')
    temporary = Path(str(destination) + '.partial')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as out:
        for record in records:
            out.write(cache / record['archive'], record['archive'])
        out.write(ROOT / 'LICENSES/framework-sources.json', 'framework-sources.json')
        out.write(ROOT / 'docs/FRAMEWORK-SOURCE.zh-CN.md', 'README.zh-CN.md')
        for name in ('BepInEx-LGPL-2.1.txt', 'NeighTools-UnityDoorstop.txt', 'BepInEx-Il2CppInterop.txt', 'GPL-3.0.txt'):
            out.write(ROOT / 'LICENSES' / name, 'LICENSES/' + name)
    temporary.replace(destination)
    return Path(destination)


if __name__ == '__main__':
    output = ROOT / 'release/LGPL-framework-sources.zip'
    output.parent.mkdir(exist_ok=True)
    print(prepare(output))

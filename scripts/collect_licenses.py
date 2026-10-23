# SPDX-License-Identifier: GPL-3.0-only
"""Retain installed license texts with original subpaths, avoiding collisions."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
REVIEWED={
    'websockets':'BSD-3-Clause', 'qrcode':'BSD-3-Clause AND MIT',
    'pillow':'MIT-CMU AND bundled component terms', 'customtkinter':'MIT',
    'darkdetect':'BSD-3-Clause', 'packaging':'Apache-2.0 OR BSD-2-Clause',
    'colorama':'BSD-3-Clause',
    'pyinstaller':'GPL-2.0-or-later WITH Bootloader-exception AND Apache-2.0 for runtime hooks',
    'pyinstaller-hooks-contrib':'GPL-2.0-or-later AND Apache-2.0 (file-specific)',
    'altgraph':'MIT', 'pefile':'MIT', 'pywin32-ctypes':'BSD-3-Clause',
    'setuptools':'MIT AND bundled component terms', 'zxing-cpp':'Apache-2.0',
}


def collect():
    licenses=ROOT/'LICENSES'
    records=[]
    for name,expression in REVIEWED.items():
        dist=importlib.metadata.distribution(name)
        entries=[]
        for item in dist.files or []:
            # A directory named packaging/licenses also contains Python modules
            # and caches. Retain notice files, not every file in that directory.
            if not Path(str(item)).name.lower().startswith(('license','copying','notice','authors','copyright')): continue
            source=Path(dist.locate_file(item))
            if not source.is_file(): continue
            target=licenses/'python-packages'/name/Path(str(item))
            if not target.resolve().is_relative_to(licenses.resolve()): raise ValueError('Invalid distribution path')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            entries.append({'path':target.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
        note=None
        if not entries and name=='zxing-cpp':
            source=licenses/'zxing-cpp-Apache-2.0.txt'
            if not source.is_file(): raise FileNotFoundError('Missing upstream ZXing license')
            entries.append({'path':source.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
            note='Installed test-only wheel has no license text; retained upstream v2.3.0 LICENSE separately.'
        if not entries: raise ValueError('No license collected for '+name)
        records.append({'name':name,'version':dist.version,'license_reviewed':expression,
            'license_metadata_original':dist.metadata.get('License-Expression') or dist.metadata.get('License'),
            'project_urls':dist.metadata.get_all('Project-URL',[]),'license_files':entries,'note':note})
    (licenses/'python-packages.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return records


if __name__=='__main__':
    result=collect()
    print('Distributions:',len(result),'retained license files:',sum(len(r['license_files']) for r in result))

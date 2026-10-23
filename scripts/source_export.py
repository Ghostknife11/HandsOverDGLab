# SPDX-License-Identifier: GPL-3.0-only
"""Export reviewed source without local runtimes, game files, logs or secrets."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ('desktop', 'plugin', 'scripts', 'tests', 'LICENSES', 'docs', '.github')
SOURCE_FILES = ('README.md', 'LICENSE', 'COPYRIGHT.md', 'THIRD-PARTY-NOTICES.md',
    '.gitignore', '.gitattributes', 'requirements.txt', 'requirements-build.txt', 'requirements-dev.txt', '启动联动.cmd')
EXCLUDED_PARTS = {'__pycache__', 'bin', 'obj', '.git', '.vs'}
EXCLUDED_SUFFIXES = {'.pyc', '.dll', '.exe', '.pyd', '.pdb', '.log', '.jsonl', '.dmp', '.nupkg', '.zip'}


def source_files():
    for name in SOURCE_FILES:
        path = ROOT / name
        if not path.is_file(): raise FileNotFoundError('Missing source distribution file: ' + name)
        yield path
    for directory in SOURCE_DIRS:
        for path in sorted((ROOT / directory).rglob('*')):
            relative = path.relative_to(ROOT)
            if not path.is_file() or any(p in EXCLUDED_PARTS for p in relative.parts): continue
            if path.suffix.lower() in EXCLUDED_SUFFIXES or path.name == '.DS_Store' or path.name.startswith('.env'): continue
            if directory == 'LICENSES' and path.suffix.lower() in {'.py', '.pyo'}: continue
            yield path


def export_source(destination):
    destination = Path(destination).resolve()
    if not destination.is_relative_to(ROOT): raise ValueError('Source export must remain in this workspace')
    files = list(source_files())
    if 'GNU GENERAL PUBLIC LICENSE' not in (ROOT/'desktop/vendor/LICENSE').read_text(encoding='utf-8'):
        raise ValueError('SDK license is missing or invalid')
    for record in json.loads((ROOT/'LICENSES/python-packages.json').read_text(encoding='utf-8')):
        for entry in record['license_files']:
            original=ROOT/entry['path']
            if original.suffix.lower() in EXCLUDED_SUFFIXES or '__pycache__' in original.parts:
                raise ValueError('License index contains a non-notice artifact')
            if not original.resolve().is_relative_to(ROOT/'LICENSES'): raise ValueError('Invalid license index path')
            if hashlib.sha256(original.read_bytes()).hexdigest()!=entry['sha256']:
                raise ValueError('License text changed since inventory: '+entry['path'])
    destination.mkdir(parents=True, exist_ok=False)
    for source in files:
        target = destination / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    manifest = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    (destination/'SOURCE-SHA256.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    return destination


if __name__ == '__main__':
    parent = ROOT/'github-ready'
    parent.mkdir(exist_ok=True)
    destination = parent/'HandsOverDGLab'
    if destination.exists(): destination=parent/('HandsOverDGLab-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    export_source(destination)
    archive=shutil.make_archive(str(destination)+'-source','zip',root_dir=destination.parent,base_dir=destination.name)
    print('SOURCE_DIRECTORY',destination)
    print('SOURCE_ARCHIVE',archive)

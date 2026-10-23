# SPDX-License-Identifier: GPL-3.0-only
"""The public Windows build boundary and native-file provenance rules."""
import hashlib
from pathlib import Path
import re

SYSTEM_RUNTIME = re.compile(r'(?i)^(?:api-ms-win-.*|ext-ms-win-.*|ucrtbase|vcruntime\d.*|msvcp\d.*|concrt\d.*)\.dll$')


def excluded_runtime(name):
    return bool(SYSTEM_RUNTIME.fullmatch(Path(name).name))


def native_origin(source, python_root, site_root):
    source = Path(source).resolve()
    for root, label in ((Path(site_root).resolve(), 'python-site-packages'),
                        (Path(python_root).resolve(), 'CPython-3.13.9-Windows')):
        if source.is_relative_to(root):
            return label + '/' + source.relative_to(root).as_posix()
    raise ValueError('Native dependency outside reviewed Python installations: ' + str(source))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

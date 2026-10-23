# SPDX-License-Identifier: GPL-3.0-only
"""Public package must never silently acquire native files from a developer PATH."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from release_policy import excluded_runtime, native_origin


class PublicReleaseTests(unittest.TestCase):
    def test_native_boundary_and_system_runtime_filter(self):
        for name in ('api-ms-win-crt-runtime-l1-1-0.dll', 'ucrtbase.dll', 'VCRUNTIME140.dll', 'MSVCP140_1.dll'):
            self.assertTrue(excluded_runtime(name))
        self.assertFalse(excluded_runtime('libcrypto-3.dll'))
        self.assertFalse(excluded_runtime('python313.dll'))
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with self.assertRaises(ValueError):
                native_origin(base / 'unrelated-tool/unknown.dll', base / 'python', base / 'site')
            self.assertEqual(native_origin(base / 'site/PIL/native.dll', base / 'python', base / 'site'),
                'python-site-packages/PIL/native.dll')

    def test_untrusted_framework_archive_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            bad = base / 'fake.zip'
            bad.write_bytes(b'not the official loader')
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                '-File', str(ROOT / 'scripts/Get-OfficialFramework.ps1'), '-CacheRoot', str(base / 'cache'),
                '-ArchivePath', str(bad)], capture_output=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'SHA-256 mismatch', result.stderr)
            self.assertEqual(list((base / 'cache').iterdir()), [])

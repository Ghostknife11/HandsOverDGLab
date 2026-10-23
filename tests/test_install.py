# SPDX-License-Identifier: GPL-3.0-only
"""Exercise installer ownership and uninstall recovery in isolated fake games."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='handsover-install-')
        self.base = Path(self.temp.name)
        self.game = self.base / 'game'
        self.game.mkdir()
        (self.game / 'Hands Over.exe').write_bytes(b'original game')
        self.framework = self.base / 'framework'
        self.framework.mkdir()
        (self.framework / 'winhttp.dll').write_bytes(b'test loader')
        (self.framework / 'BepInEx/core').mkdir(parents=True)
        (self.framework / 'BepInEx/core/test.dll').write_bytes(b'test core')
        self.plugin = self.base / 'HandsOverDGLab.dll'
        self.plugin.write_bytes(b'test plugin')

    def tearDown(self): self.temp.cleanup()

    def run_script(self, script, *args):
        return subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',
            '-File',str(ROOT/'scripts'/script),'-GamePath',str(self.game),*map(str,args)],
            capture_output=True,timeout=30)

    def install(self):
        result=self.run_script('Install.ps1','-FrameworkPath',self.framework,'-PluginPath',self.plugin)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))

    def test_install_upgrade_uninstall_preserves_preexisting_and_generated_files(self):
        (self.game/'winhttp.dll').write_bytes(b'test loader')  # preexisting identical: never owned
        self.install()
        generated=self.game/'BepInEx/cache/user-data.txt'
        generated.parent.mkdir(parents=True)
        generated.write_text('generated')
        self.plugin.write_bytes(b'plugin upgrade')
        self.install()
        manifest=json.loads((self.game/'HandsOverDGLab.install.json').read_text(encoding='utf-8-sig'))
        self.assertNotIn('winhttp.dll',[e['path'] for e in manifest['files']])
        result=self.run_script('Uninstall.ps1')
        self.assertEqual(result.returncode,0)
        self.assertEqual((self.game/'Hands Over.exe').read_bytes(),b'original game')
        self.assertEqual((self.game/'winhttp.dll').read_bytes(),b'test loader')
        self.assertEqual(generated.read_text(),'generated')
        self.assertFalse((self.game/'HandsOverDGLab.install.json').exists())
        self.assertFalse((self.game/'BepInEx/plugins/HandsOverDGLab/HandsOverDGLab.dll').exists())

    def test_conflict_is_detected_before_any_install_write(self):
        (self.game/'winhttp.dll').write_bytes(b'other mod')
        result=self.run_script('Install.ps1','-FrameworkPath',self.framework,'-PluginPath',self.plugin)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.game/'winhttp.dll').read_bytes(),b'other mod')
        self.assertFalse((self.game/'BepInEx').exists())

    def test_modified_owned_file_is_preserved_with_recovery_manifest(self):
        self.install()
        (self.game/'winhttp.dll').write_bytes(b'user changed it')
        result=self.run_script('Uninstall.ps1')
        self.assertEqual(result.returncode,0)
        self.assertEqual((self.game/'winhttp.dll').read_bytes(),b'user changed it')
        manifest=json.loads((self.game/'HandsOverDGLab.install.json').read_text(encoding='utf-8-sig'))
        self.assertEqual([e['path'] for e in manifest['files']],['winhttp.dll'])

    def test_manifest_cannot_delete_outside_selected_game(self):
        protected=self.base/'outside.txt'
        protected.write_bytes(b'keep me')
        manifest={'owner':'HandsOverDGLab/v1','version':'0.1.0','files':[
            {'path':'..\\outside.txt','sha256':hashlib.sha256(protected.read_bytes()).hexdigest()}]}
        (self.game/'HandsOverDGLab.install.json').write_text(json.dumps(manifest),encoding='utf-8-sig')
        result=self.run_script('Uninstall.ps1')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(protected.read_bytes(),b'keep me')

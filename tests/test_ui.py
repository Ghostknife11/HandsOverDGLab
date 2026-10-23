# SPDX-License-Identifier: GPL-3.0-only
"""Regression for the real Tk image lifecycle, including disconnect/switching."""
import gc
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'desktop'), str(ROOT / 'desktop/vendor')]
import customtkinter as ctk
from handsover.ui_layout import draw_qr
from handsover.waveform import pairing_url


class QRWidgetTests(unittest.TestCase):
    def test_repeated_protocol_switch_disconnect_and_regenerate(self):
        root = ctk.CTk()
        root.withdraw()
        try:
            view = ctk.CTkLabel(root, text='准备扫码')
            view.pack()
            app = SimpleNamespace(qr_label=view, photo=None, pair_url=None)
            v4 = pairing_url('wss://trex.dungeon-lab.cn/v4', 'qr-session', 'v4')
            v3 = pairing_url('wss://ws.dungeon-lab.cn', 'qr-session', 'v3')
            for url in [None, v4, None, v3, None, v4, v3, None, v3] * 3:
                draw_qr(app, url)
                gc.collect()
                root.update_idletasks()
                image_name = view._label.cget('image')
                self.assertTrue(image_name)
                self.assertIn(str(image_name), root.tk.call('image', 'names'))
                self.assertEqual(app.pair_url, url)
                self.assertEqual(view.cget('text'), '' if url else '准备好手机\n点击下方生成二维码')
        finally:
            root.destroy()


if __name__ == '__main__': unittest.main()

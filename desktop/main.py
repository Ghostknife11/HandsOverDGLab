# SPDX-License-Identifier: GPL-3.0-only
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor'))

if __name__ == '__main__':
    try:
        if len(sys.argv) == 3 and sys.argv[1] == '--self-check':
            import json
            import customtkinter as ctk
            from types import SimpleNamespace
            from handsover.ui_layout import draw_qr
            from handsover.waveform import pairing_url, frames_for
            from handsover.config import Profile
            root = ctk.CTk()
            root.withdraw()
            view = ctk.CTkLabel(root, text='')
            app = SimpleNamespace(qr_label=view, photo=None, pair_url=None)
            for protocol, server in [('v4','wss://trex.dungeon-lab.cn/v4'),('v3','wss://ws.dungeon-lab.cn')]:
                for url in [pairing_url(server,'bundle-self-check',protocol),None]:
                    draw_qr(app,url)
                    root.update_idletasks()
            root.destroy()
            Path(sys.argv[2]).write_text(json.dumps({'ok':True,'frozen':bool(getattr(sys,'frozen',False)),
                'python':sys.version,'frames':frames_for(Profile())},ensure_ascii=False,indent=2),encoding='utf-8')
        else:
            from handsover.gui import Application
            Application().run()
    except Exception:
        import os
        import traceback
        log_dir = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'HandsOverDGLab'
        log_dir.mkdir(parents=True, exist_ok=True)
        report = traceback.format_exc()
        (log_dir / 'startup-error.log').write_text(report, encoding='utf-8')
        import tkinter.messagebox
        tkinter.messagebox.showerror('联动控制台无法启动', '启动失败，诊断信息已保存至：\n' + str(log_dir / 'startup-error.log'))
        raise

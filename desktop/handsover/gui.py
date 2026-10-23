# SPDX-License-Identifier: GPL-3.0-only
import asyncio
import ctypes
import logging
from logging.handlers import RotatingFileHandler
import os
import queue
import threading
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from .ui_layout import build_ui, draw_qr
from tkinter import messagebox
from .config import DATA_DIR, Settings, Profile
from .engine import Engine, GameServer
from .waveform import channel_limits, target_intensities

class Application:
    def __init__(self):
        try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception: pass
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(DATA_DIR / 'desktop.log', maxBytes=2_000_000, backupCount=3, encoding='utf-8')
        logging.basicConfig(level=logging.INFO, handlers=[handler], format='%(asctime)s %(levelname)s %(name)s %(message)s')
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk(fg_color="#0D1118")
        self.root.title('HANDS OVER · 郊狼联动 0.1.3')
        icon = Path(__file__).resolve().parents[1] / 'assets' / 'app.ico'
        if icon.exists(): self.root.after(250, lambda: self.root.iconbitmap(str(icon)))
        self.root.geometry('1160x900+100+30')
        self.root.minsize(1080, 850)
        try: self.settings = Settings.load()
        except Exception as e:
            logging.exception('Invalid settings')
            self.settings = Settings()
            messagebox.showwarning('配置已重置', '原配置无法读取，已使用默认参数。\n' + str(e), parent=self.root)
        self.queue = queue.Queue()
        self.loop = asyncio.new_event_loop()
        self.engine = None
        self.server = None
        self.devices = []
        self.photo = None
        self.pair_url = None
        self.phone_state = 'disconnected'
        self.closing = False
        self.make_ui()
        self.thread = threading.Thread(target=self.run_loop, name='device-network', daemon=True)
        self.thread.start()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(60, self.pump)

    def make_ui(self):
        build_ui(self)

    def run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.engine = Engine(self.settings, lambda k, v: self.queue.put((k, v)))
        self.server = GameServer(self.engine, self.settings.port)
        try: self.loop.run_until_complete(self.server.start())
        except Exception as e: self.queue.put(('error', f'无法监听本机端口 {self.settings.port}：{e}'))
        self.loop.run_forever()
        pending = asyncio.all_tasks(self.loop)
        for task in pending: task.cancel()
        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        self.loop.close()

    def submit(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        def done(f):
            try: f.result()
            except Exception as e:
                logging.exception('Command failed')
                self.queue.put(('error', str(e)))
                if self.engine: self.queue.put(('enabled', self.engine.enabled))
        future.add_done_callback(done)
        return future

    def read_settings(self):
        from decimal import Decimal
        profiles = {}
        for key, (percent, seconds, wave) in self.profile_vars.items():
            ticks = Decimal(seconds.get()) * 10
            if not ticks.is_finite() or ticks != ticks.to_integral_value(): raise ValueError('时间应以 0.1 秒为步长。')
            profiles[key] = Profile(int(round(percent.get())), int(ticks) * 100, self.waveforms[wave.get()])
        return Settings(server=self.server_var.get().strip(), port=self.settings.port,
            protocol="v4" if self.protocol_var.get() == "DG-LAB 4" else "v3",
            channels=[c for c, var in [(0, self.a_var), (1, self.b_var)] if var.get()], **profiles).validate()

    def apply(self):
        try:
            cfg = self.read_settings()
            if self.engine:
                async def run():
                    await self.engine.apply(cfg)
                    self.settings = cfg
                self.submit(run())
        except Exception as e: messagebox.showerror('设置无效', str(e), parent=self.root)

    def test(self, kind):
        try:
            cfg = self.read_settings()
            async def run():
                if cfg != self.engine.settings: await self.engine.apply(cfg)
                self.settings = cfg
                await self.engine.play(kind, manual=True)
            if self.engine: self.submit(run())
        except Exception as e: messagebox.showerror('设置无效', str(e), parent=self.root)

    def connect(self):
        if not self.engine: return
        self.connect_button.configure(state='disabled')
        async def run():
            try:
                if self.phone_state not in ('disconnected', 'idle'):
                    await self.engine.disconnect()
                else:
                    cfg = self.read_settings_snapshot
                    await self.engine.apply(cfg)
                    self.settings = cfg
                    await self.engine.connect()
            finally: self.queue.put(('connect_done', None))
        try: self.read_settings_snapshot = self.read_settings()
        except Exception as e:
            self.connect_button.configure(state='normal')
            messagebox.showerror('设置无效', str(e), parent=self.root)
            return
        self.submit(run())

    def select_device(self, _event):
        index = self.device_combo.current()
        if self.engine and 0 <= index < len(self.devices):
            client, dev = self.devices[index]
            self.submit(self.engine.select((client, dev['slotId'])))

    def copy_pairing(self):
        if not self.pair_url: return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.pair_url)
        self.add_log('配对链接已复制。')

    def stop(self):
        self.enabled_var.set(False)
        if self.engine: self.submit(self.engine.stop('已停止输出', disable=True))

    def refresh_targets(self):
        index=self.device_combo.current()
        device=self.devices[index][1] if 0 <= index < len(self.devices) else None
        protocol='v4' if self.protocol_var.get()=='DG-LAB 4' else 'v3'
        limits=channel_limits(device,protocol)
        self.limit_label.configure(text=f'手机上限：A {limits[0] if limits[0] is not None else "—"}    B {limits[1] if limits[1] is not None else "—"}')
        for key,(percent,_,_) in self.profile_vars.items():
            try:
                values=target_intensities(device,protocol,int(round(percent.get())))
                text=f'实际强度：A {values[0]}    B {values[1]}'
            except ValueError: text='手机上限比例 · 等待上限'
            self.target_labels[key].configure(text=text)

    def add_log(self, text):
        self.log_widget.configure(state='normal')
        self.log_widget.insert('end', text + '\n')
        if int(self.log_widget.index('end-1c').split('.')[0]) > 120: self.log_widget.delete('1.0', '30.0')
        self.log_widget.see('end')
        self.log_widget.configure(state='disabled')

    def pump(self):
        try:
            for _ in range(100):
                key, value = self.queue.get_nowait()
                if key == 'log': self.add_log(value)
                elif key == 'error':
                    self.add_log('错误：' + value)
                    self.output_var.set(value)
                elif key == 'output': self.output_var.set(value)
                elif key == 'enabled': self.enabled_var.set(bool(value))
                elif key == 'phone':
                    self.phone_state = value
                    labels = {'idle': '未连接', 'disconnected': '未连接', 'connecting': '正在连接中继…', 'waiting_for_peer': '等待手机扫码', 'paired': '手机已配对'}
                    self.phone_label.configure(text=labels.get(value, value))
                    self.connect_button.configure(text='生成连接二维码' if value in ('idle', 'disconnected') else '断开手机连接')
                elif key == 'connect_done': self.connect_button.configure(state='normal')
                elif key == 'game':
                    text = '对局中 · 正在监听本人按压' if value.get('active') else ('游戏已暂停' if value.get('paused') and value.get('gameplay', True) else '游戏已连接 · 等待进入对局')
                    if not value.get('connected'): text = '等待游戏插件连接'
                    elif not value.get('hooks'): text = '插件挂钩未就绪，请查看游戏日志'
                    if self.game_label.cget("text") != text: self.game_label.configure(text=text)
                elif key == 'qr':
                    draw_qr(self, value)
                elif key == 'devices':
                    self.devices = value.get('items', []) if isinstance(value, dict) else []
                    labels = [f"{d.get('name', '郊狼 3.0')} · {d['slotId'][-5:]}" for c, d in self.devices]
                    self.device_combo.configure(values=labels)
                    selected = value.get('selection') if isinstance(value, dict) else None
                    self.intensity_label.configure(text='当前强度：A —    B —')
                    for i, (c, d) in enumerate(self.devices):
                        if selected == (c, d['slotId']):
                            self.device_combo.current(i)
                            p = d.get('props', {})
                            self.intensity_label.configure(text=f"当前强度：A {p.get('intensityA', '—')}    B {p.get('intensityB', '—')}")
                            break
                    else: self.device_combo.set('请选择设备' if labels else '未发现已连接的郊狼 3.0')
                    self.refresh_targets()
        except queue.Empty: pass
        except Exception:
            logging.exception('UI update')
        if not self.closing: self.root.after(60, self.pump)

    def close(self):
        if self.closing: return
        self.closing = True
        self.enabled_var.set(False)
        async def shutdown():
            if self.engine:
                self.engine.closing = True
                await self.engine.disconnect()
            if self.server: await self.server.close()
        future = asyncio.run_coroutine_threadsafe(shutdown(), self.loop)
        deadline = __import__('time').monotonic() + 3
        def finish():
            if not future.done() and __import__('time').monotonic() < deadline:
                self.root.after(80, finish)
                return
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.root.destroy()
        finish()

    def run(self): self.root.mainloop()

# SPDX-License-Identifier: GPL-3.0-only
"""Rounded Tk interface with stable status labels and integer-module QR images."""
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from dglab_kit_python import COYOTE_WAVEFORMS
from .waveform import qr_bitmap
from .config import DATA_DIR
import os

BG, CARD, FIELD = '#0D1118', '#171E29', '#222C3B'
TEXT, MUTED, ACCENT = '#F1F5FA', '#91A0B6', '#C6ED80'
BLUE, ROSE = '#88C7FA', '#F28D9C'
SERVERS = {'v4':'wss://trex.dungeon-lab.cn/v4', 'v3':'wss://ws.dungeon-lab.cn'}

def label(parent, text='', size=13, color=TEXT, bold=False, **kwargs):
    return ctk.CTkLabel(parent, text=text, text_color=color,
        font=ctk.CTkFont('Microsoft YaHei UI', size, 'bold' if bold else 'normal'), **kwargs)

def button(parent, text, command, primary=False, **kwargs):
    return ctk.CTkButton(parent, text=text, command=command, height=38, corner_radius=9,
        fg_color=ACCENT if primary else FIELD, hover_color='#D7F6A4' if primary else '#303E52',
        text_color=BG if primary else TEXT, font=ctk.CTkFont('Microsoft YaHei UI',12,'bold'), **kwargs)

class IndexedMenu(ctk.CTkOptionMenu):
    def current(self, index=None):
        values = self.cget('values')
        if index is None: return values.index(self.get()) if self.get() in values else -1
        self.set(values[index])

def draw_qr(app, url):
    bitmap = qr_bitmap(url, 220) if url else Image.new('RGB', (220, 220), 'white')
    photo = ctk.CTkImage(light_image=bitmap, dark_image=bitmap, size=bitmap.size)
    # CTkLabel leaves the underlying Tk image in place for image=None. Releasing
    # that image then makes even a text change fail with a dangling pyimage name.
    # Always replace it with a live image before changing text; retain the old
    # reference until replacement has completed.
    app.qr_label.configure(image=photo)
    app.qr_label.configure(text='' if url else '准备好手机\n点击下方生成二维码')
    app.photo = photo
    app.pair_url = url

def enlarge(app):
    if not app.pair_url: return
    win=ctk.CTkToplevel(app.root); win.title('手机扫码连接'); win.geometry('520x590'); win.transient(app.root)
    label(win,'使用手机 APP 扫码',20,bold=True).pack(pady=(22,12))
    bitmap=qr_bitmap(app.pair_url,420)
    image=ctk.CTkImage(light_image=bitmap,dark_image=bitmap,size=bitmap.size)
    view=ctk.CTkLabel(win,text='',image=image,fg_color='white',corner_radius=8)
    view.pack(padx=20,pady=10); view._qr_image=image
    label(win,'若提示链接不正确，请切换「兼容扫码」重新生成。',12,MUTED).pack(pady=10)

def server_settings(app):
    win=ctk.CTkToplevel(app.root); win.title('服务器设置'); win.geometry('540x230'); win.transient(app.root)
    label(win,'WebSocket 中继地址',16,bold=True).pack(anchor='w',padx=24,pady=(22,10))
    ctk.CTkEntry(win,textvariable=app.server_var,height=38).pack(fill='x',padx=24)
    label(win,'wss 为加密连接，ws 为未加密连接；请与服务器保持一致。',12,MUTED).pack(padx=24,pady=12)
    button(win,'保存设置',lambda:(app.apply(),win.destroy()),True).pack(padx=24)

def protocol_changed(app, value):
    protocol='v4' if value=='DG-LAB 4' else 'v3'
    if app.server_var.get() in SERVERS.values(): app.server_var.set(SERVERS[protocol])
    app.apply()

def build_ui(app):
    shell=ctk.CTkFrame(app.root,fg_color='transparent'); shell.pack(fill='both',expand=True,padx=24,pady=20)
    head=ctk.CTkFrame(shell,fg_color='transparent'); head.pack(fill='x',pady=(0,20))
    icon=ctk.CTkFrame(head,width=46,height=46,fg_color=ACCENT,corner_radius=13)
    icon.pack(side='left',padx=(0,13)); icon.pack_propagate(False)
    label(icon,'H',28,BG,True).pack(expand=True)
    brand=ctk.CTkFrame(head,fg_color='transparent'); brand.pack(side='left')
    label(brand,'HANDS OVER',25,bold=True,height=30).pack(anchor='w')
    label(brand,'郊狼联动控制台 · v0.1.3',12,MUTED,height=22).pack(anchor='w')
    label(head,'手机设上限，游戏按比例输出。',13,MUTED).pack(side='right')
    body=ctk.CTkFrame(shell,fg_color='transparent'); body.pack(fill='both',expand=True)
    body.columnconfigure(0,weight=0,minsize=296); body.columnconfigure(1,weight=1); body.rowconfigure(0,weight=1)
    rail=ctk.CTkFrame(body,fg_color='transparent',width=296); rail.grid(row=0,column=0,sticky='nsew',padx=(0,18))
    main=ctk.CTkFrame(body,fg_color='transparent'); main.grid(row=0,column=1,sticky='nsew')
    connect=ctk.CTkFrame(rail,fg_color=CARD,corner_radius=16); connect.pack(fill='x')
    label(connect,'连接手机',17,bold=True).pack(anchor='w',padx=18,pady=(16,2))
    app.phone_label=label(connect,'● 尚未连接',12,MUTED); app.phone_label.pack(anchor='w',padx=18,pady=(0,10))
    app.protocol_var=tk.StringVar(value='DG-LAB 4' if app.settings.protocol=='v4' else '兼容扫码')
    app.server_var=tk.StringVar(value=app.settings.server)
    ctk.CTkSegmentedButton(connect,values=['DG-LAB 4','兼容扫码'],variable=app.protocol_var,
        command=lambda v:protocol_changed(app,v),height=32,selected_color='#405B3B',selected_hover_color='#4A6942',
        unselected_color=FIELD,unselected_hover_color='#303E52',fg_color=FIELD,corner_radius=8).pack(fill='x',padx=18,pady=(0,12))
    white=ctk.CTkFrame(connect,fg_color='#FFFFFF',corner_radius=12,width=258,height=238)
    white.pack(padx=18); white.pack_propagate(False)
    app.qr_label=ctk.CTkLabel(white,text='准备好手机\n点击下方生成二维码',text_color='#647082',
        font=ctk.CTkFont('Microsoft YaHei UI',13),width=230,height=220); app.qr_label.pack(expand=True)
    links=ctk.CTkFrame(connect,fg_color='transparent'); links.pack(fill='x',padx=18,pady=(7,10))
    for text,command in [('放大二维码',lambda:enlarge(app)),('复制链接',app.copy_pairing)]:
        ctk.CTkButton(links,text=text,command=command,fg_color='transparent',hover_color=FIELD,text_color=MUTED,
            width=120,height=25,font=ctk.CTkFont('Microsoft YaHei UI',11)).pack(side='left',expand=True)
    app.connect_button=button(connect,'生成连接二维码',app.connect,True); app.connect_button.pack(fill='x',padx=18,pady=(0,6))
    ctk.CTkButton(connect,text='服务器设置  ›',command=lambda:server_settings(app),fg_color='transparent',
        hover_color=FIELD,text_color=MUTED,height=27,font=ctk.CTkFont('Microsoft YaHei UI',11)).pack(fill='x',padx=18,pady=(0,10))
    device=ctk.CTkFrame(rail,fg_color=CARD,corner_radius=16); device.pack(fill='both',expand=True,pady=(14,0))
    label(device,'我的设备',15,bold=True).pack(anchor='w',padx=18,pady=(14,8))
    app.device_combo=IndexedMenu(device,values=['等待手机连接'],command=app.select_device,fg_color=FIELD,button_color=FIELD,
        button_hover_color='#303E52',dropdown_fg_color=FIELD,height=32,font=ctk.CTkFont('Microsoft YaHei UI',11),dynamic_resizing=False)
    app.device_combo.pack(fill='x',padx=18)
    app.intensity_label=label(device,'当前强度：A —    B —',16,bold=True)
    app.intensity_label.pack(padx=18,pady=(16,4))
    app.limit_label=label(device,'手机上限：A —    B —',14,ACCENT)
    app.limit_label.pack(pady=(0,6))
    label(device,'上限在手机设置，输出结束后归零',11,MUTED).pack(pady=(0,12))
    status=ctk.CTkFrame(main,fg_color=CARD,corner_radius=16); status.pack(fill='x')
    state_row=ctk.CTkFrame(status,fg_color='transparent'); state_row.pack(fill='x',padx=20,pady=(16,0))
    label(state_row,'游戏联动',17,bold=True).pack(side='left')
    app.enabled_var=tk.BooleanVar(value=False)
    ctk.CTkSwitch(state_row,text='启用联动',variable=app.enabled_var,
        command=lambda:app.submit(app.engine.set_enabled(app.enabled_var.get())) if app.engine else None,
        progress_color=ACCENT,button_color='#F1F5FA',button_hover_color='white',font=ctk.CTkFont('Microsoft YaHei UI',12),
        switch_width=40,switch_height=22).pack(side='right')
    app.game_label=label(status,'● 等待游戏插件连接',12,MUTED); app.game_label.pack(anchor='w',padx=20,pady=(4,10))
    label(status,'设备连接就绪后自动联动；手动测试无需进入对局。',11,MUTED).pack(anchor='w',padx=20,pady=(0,8))
    route=ctk.CTkFrame(status,fg_color='transparent'); route.pack(fill='x',padx=20,pady=(0,16))
    label(route,'输出通道',12,MUTED).pack(side='left',padx=(0,18))
    app.a_var=tk.BooleanVar(value=0 in app.settings.channels); app.b_var=tk.BooleanVar(value=1 in app.settings.channels)
    for text,var in [('A 通道',app.a_var),('B 通道',app.b_var)]:
        ctk.CTkCheckBox(route,text=text,variable=var,width=85,checkbox_width=18,checkbox_height=18,corner_radius=5,
            fg_color=ACCENT,checkmark_color=BG,hover_color='#6D8255',font=ctk.CTkFont('Microsoft YaHei UI',12)).pack(side='left',padx=(0,16))
    profiles=ctk.CTkFrame(main,fg_color='transparent'); profiles.pack(fill='x',pady=(14,0))
    profiles.columnconfigure((0,1),weight=1,uniform='profiles')
    app.waveforms={v['label']['cn']:k.value for k,v in COYOTE_WAVEFORMS.items()}; app.profile_vars={}; app.target_labels={}
    for i,(key,title,hint,color) in enumerate([('fake','假牙 · 轻反馈','普通按压 / 保护卡生效',BLUE),('real','真牙 · 强反馈','踩中机关 / 陷阱卡生效',ROSE)]):
        p=getattr(app.settings,key)
        card=ctk.CTkFrame(profiles,fg_color=CARD,corner_radius=16); card.grid(row=0,column=i,sticky='nsew',padx=(0,7) if i==0 else (7,0))
        label(card,title,16,color,True).pack(anchor='w',padx=18,pady=(17,1))
        label(card,hint,11,MUTED).pack(anchor='w',padx=18,pady=(0,12))
        percent=tk.DoubleVar(value=p.percent); seconds=tk.StringVar(value=f'{p.duration_ms/1000:g}')
        wave=tk.StringVar(value=next(n for n,c in app.waveforms.items() if c==p.waveform)); app.profile_vars[key]=(percent,seconds,wave)
        value=label(card,f'{p.percent}%',36,bold=True,anchor='w'); value.pack(anchor='w',padx=18)
        app.target_labels[key]=label(card,'手机上限比例 · 等待上限',11,MUTED)
        app.target_labels[key].pack(anchor='w',padx=18,pady=(0,7))
        def changed(v,l=value):
            l.configure(text=f'{int(round(v))}%')
            app.refresh_targets()
        ctk.CTkSlider(card,from_=0,to=100,number_of_steps=100,variable=percent,
            command=changed,progress_color=color,button_color=color,
            button_hover_color=color,fg_color=FIELD,height=18).pack(fill='x',padx=18,pady=(0,16))
        duration=ctk.CTkFrame(card,fg_color='transparent'); duration.pack(fill='x',padx=18,pady=(0,10))
        label(duration,'持续时长',12,MUTED).pack(side='left'); label(duration,'秒',12,MUTED).pack(side='right')
        ctk.CTkEntry(duration,textvariable=seconds,width=66,height=30,fg_color=FIELD,border_width=0,justify='center',
            font=ctk.CTkFont('Microsoft YaHei UI',13)).pack(side='right',padx=8)
        ctk.CTkOptionMenu(card,values=list(app.waveforms),variable=wave,fg_color=FIELD,button_color=FIELD,
            button_hover_color='#303E52',dropdown_fg_color=FIELD,font=ctk.CTkFont('Microsoft YaHei UI',12),height=32).pack(fill='x',padx=18,pady=(0,12))
        button(card,'测试假牙' if key=='fake' else '测试真牙',lambda k=key:app.test(k)).pack(fill='x',padx=18,pady=(0,18))
    actions=ctk.CTkFrame(main,fg_color='transparent'); actions.pack(fill='x',pady=14)
    button(actions,'保存并应用设置',app.apply,True).pack(side='left',fill='x',expand=True,padx=(0,10))
    ctk.CTkButton(actions,text='■  停止输出',command=app.stop,height=38,corner_radius=9,fg_color='#3B202A',
        hover_color='#572B39',text_color=ROSE,font=ctk.CTkFont('Microsoft YaHei UI',12,'bold')).pack(side='left',fill='x',expand=True)
    log=ctk.CTkFrame(main,fg_color=CARD,corner_radius=16); log.pack(fill='both',expand=True)
    log_head=ctk.CTkFrame(log,fg_color='transparent'); log_head.pack(fill='x',padx=18,pady=(10,2))
    label(log_head,'运行记录',12,MUTED).pack(side='left')
    ctk.CTkButton(log_head,text='打开日志目录 ›',command=lambda:os.startfile(str(DATA_DIR)),fg_color='transparent',hover_color=FIELD,
        text_color=MUTED,height=24,width=100,font=ctk.CTkFont('Microsoft YaHei UI',11)).pack(side='right')
    app.output_var=tk.StringVar(value='等待游戏事件或手动测试')
    label(log,'',12,anchor='w',textvariable=app.output_var).pack(fill='x',padx=18)
    app.log_widget=ctk.CTkTextbox(log,height=58,fg_color='transparent',text_color=MUTED,font=ctk.CTkFont('Microsoft YaHei UI',11),wrap='word')
    app.log_widget.pack(fill='both',expand=True,padx=12,pady=(0,8)); app.log_widget.configure(state='disabled')
    label(shell,'实际强度 = 手机通道上限 × 结果比例（向下取整）；波形采样保持原样。',11,MUTED).pack(anchor='w',pady=(12,0))

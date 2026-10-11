"""Small Windows updater. All serial and Flash work runs outside the Tk thread."""
import json
import os
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog,messagebox,ttk
from .client import UpdaterClient,UpdateCancelled,select_devices
from .gui_model import UpdaterModel

def default_backups():
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')))/'NewDeviation/backups'

class UpdaterWindow:
    def __init__(self,root):
        self.root=root;self.model=UpdaterModel();self.client=None
        self.events=queue.Queue();self.cancel=threading.Event();self.worker=None;self.closing=False
        self.devices=[];self.backup_dir=default_backups();self.last_progress=0
        root.title('New Deviation · TX15 USB 更新');root.geometry('680x380');root.minsize(640,360)
        frame=ttk.Frame(root,padding=20);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='New Deviation 固件更新',font=('Microsoft YaHei UI',16)).pack(anchor='w')
        ttk.Label(frame,text='关机后按住 EXIT 开机，进入 USB 更新界面，再连接数据 USB。').pack(anchor='w',pady=(8,16))
        line=ttk.Frame(frame);line.pack(fill='x')
        self.combo=ttk.Combobox(line,state='readonly',width=39);self.combo.pack(side='left',fill='x',expand=True)
        self.refresh_button=ttk.Button(line,text='刷新',command=self.refresh);self.refresh_button.pack(side='left',padx=8)
        self.connect_button=ttk.Button(line,text='连接',command=self.connect);self.connect_button.pack(side='left')
        line=ttk.Frame(frame);line.pack(fill='x',pady=12)
        self.file_var=tk.StringVar(value='请选择 .ndu 固件文件')
        ttk.Label(line,textvariable=self.file_var,width=50).pack(side='left',fill='x',expand=True)
        self.file_button=ttk.Button(line,text='选择固件',command=self.choose_file);self.file_button.pack(side='left')
        self.backup_var=tk.StringVar(value='备份位置：'+str(self.backup_dir))
        ttk.Label(frame,textvariable=self.backup_var,wraplength=620).pack(anchor='w')
        self.backup_button=ttk.Button(frame,text='更改备份位置',command=self.choose_backups)
        self.backup_button.pack(anchor='w',pady=5)
        self.progress=ttk.Progressbar(frame,maximum=100);self.progress.pack(fill='x',pady=(10,8))
        self.status_var=tk.StringVar(value='等待连接。当前固件需先安装 USB 更新启动器。')
        ttk.Label(frame,textvariable=self.status_var,wraplength=620).pack(anchor='w')
        self.update_button=ttk.Button(frame,text='更新固件',command=self.update);self.update_button.pack(anchor='e',pady=10)
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(80,self.poll)
        self.refresh();self.buttons()

    def buttons(self):
        active=self.worker is not None or self.model.busy
        for button in (self.refresh_button,self.connect_button,self.file_button,self.backup_button):
            button.configure(state='disabled' if active else 'normal')
        self.update_button.configure(state='normal' if self.model.can_update and not active else 'disabled')
        self.combo.configure(state='disabled' if active else 'readonly')

    def refresh(self):
        from serial.tools.list_ports import comports
        self.devices=select_devices(comports())
        self.combo['values']=[f'TX15 · {p.device} · {p.serial_number}' for p in self.devices]
        if self.devices:self.combo.current(0)
        else:self.combo.set('未检测到 TX15 USB 更新设备')

    def work(self,operation,kind):
        self.cancel.clear()
        def run():
            try:self.events.put((kind,operation()))
            except Exception as exc:self.events.put(('error',str(exc)))
        self.worker=threading.Thread(target=run,daemon=False);self.worker.start();self.buttons()

    def connect(self):
        if not self.devices or self.combo.current()<0:return
        device=self.devices[self.combo.current()]
        def operation():
            import serial
            if self.client:self.client.close();self.client=None
            deadline=time.monotonic()+3
            while True:
                try:port=serial.Serial(device.device,115200,timeout=.02,write_timeout=3);break
                except serial.SerialException:
                    if time.monotonic()>=deadline:raise
                    time.sleep(.1)
            client=UpdaterClient(port,self.backup_dir,self.report_progress)
            try:info=client.connect(expected_uid=bytes.fromhex(device.serial_number))
            except Exception:client.close();raise
            self.client=client;return info
        self.model.disconnected();self.status_var.set('正在连接和核对设备…');self.work(operation,'connected')

    def choose_file(self):
        path=filedialog.askopenfilename(title='选择 TX15 更新包',filetypes=[('New Deviation 固件','*.ndu')])
        if not path:return
        try:
            file=Path(path)
            self.model.select_file(file);self.file_var.set(file.name)
            self.status_var.set(f'固件校验通过：{len(self.model.package.image):,} 字节')
        except Exception as exc:self.status_var.set(str(exc));self.file_var.set('文件无效，请重新选择')
        self.buttons()

    def choose_backups(self):
        folder=filedialog.askdirectory(title='选择模型和校准备份位置')
        if folder:self.backup_dir=Path(folder);self.backup_var.set('备份位置：'+str(self.backup_dir))

    def report_progress(self,stage,current,total):
        now=time.monotonic()
        if current==total or now-self.last_progress>=.1:
            self.last_progress=now;self.events.put(('progress',(stage,current,total)))

    def update(self):
        if not self.model.can_update or not self.client:return
        self.model.begin();self.progress['value']=0;raw=self.model.raw
        def operation():
            self.client.backup_dir=self.backup_dir
            prepared=self.client.prepare(raw,cancel=self.cancel.is_set)
            if self.cancel.is_set():raise UpdateCancelled('已取消，未提交写入')
            self.events.put(('writing',None))
            return self.client.commit(prepared)
        self.status_var.set('正在备份模型和校准…');self.work(operation,'result')

    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait()
                if kind=='progress':
                    stage,current,total=value
                    self.progress['value']=current*100/total if total else 0
                    label={'backup':'备份模型与校准','receive':'传输并校验固件','write':'写入与读回校验'}[stage]
                    self.status_var.set(f'{label}：{current:,} / {total:,}')
                elif kind=='writing':self.status_var.set('正在写入。请保持电池和 USB 连接。')
                elif kind=='connected':
                    self.worker=None;self.model.connected(value)
                    self.status_var.set('已连接 TX15，可以选择固件并更新。' if UpdaterClient._writable(value)
                                        else '设备处于只读状态，当前不能更新。')
                elif kind=='result':
                    self.worker=None;self.model.complete(value);self.status_var.set(value.message)
                    if self.model.success:self.progress['value']=100
                elif kind=='error':
                    self.worker=None;self.model.busy=False;self.model.disconnected()
                    self.status_var.set(value+'；如已传输，请关机重开更新模式后再连接。')
                self.buttons()
        except queue.Empty:pass
        if self.closing and self.worker is None:
            if self.client:self.client.close()
            self.root.destroy();return
        self.root.after(80,self.poll)

    def close(self):
        if self.worker is not None:
            self.closing=True;self.cancel.set()
            self.status_var.set('等待当前操作结束；写入期间请保持供电和 USB 连接。')
        else:
            if self.client:self.client.close()
            self.root.destroy()

def main(smoke_report=None):
    root=tk.Tk();window=UpdaterWindow(root)
    if smoke_report:
        def record():
            root.update_idletasks()
            report=dict(schema=1,title=root.title(),visible=bool(root.winfo_ismapped()),
                update_button_enabled=window.update_button.instate(['!disabled']),
                automatic_device_open=False,automatic_flash_write=False,
                packaged_runtime=bool(getattr(__import__('sys'),'frozen',False)))
            Path(smoke_report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            root.after(500,window.close)
        root.after(500,record)
    root.mainloop()

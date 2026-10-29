#!/usr/bin/env python3
"""Small Tk UI for the native Honda NDS downloader."""
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, filedialog, messagebox

class App:
    def __init__(self, root):
        self.root=root;self.process=None;self.messages=queue.Queue();self.running=False
        root.title('Honda Map Downloader — Linux (unofficial)');root.geometry('820x650')
        frame=ttk.Frame(root,padding=16);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Honda Civic / bonneville EU',font=('',16,'bold')).pack(anchor='w')
        ttk.Label(frame,text='Independent Linux client • No formatting • Signed HERE license preserved').pack(anchor='w',pady=(0,14))
        self.mode=tk.StringVar(value='link' if len(sys.argv)>1 else 'vin')
        mode_line=ttk.Frame(frame);mode_line.pack(fill='x',pady=(0,8))
        ttk.Radiobutton(mode_line,text='VIN — Czech/European portal',variable=self.mode,value='vin').pack(side='left')
        ttk.Radiobutton(mode_line,text='Portal launch link',variable=self.mode,value='link').pack(side='left',padx=12)
        ttk.Label(frame,text='VIN (17 characters) or portal launch link, according to the selected mode').pack(anchor='w')
        self.url=tk.StringVar(value=sys.argv[1] if len(sys.argv)>1 else '')
        ttk.Entry(frame,textvariable=self.url,show='•').pack(fill='x',pady=(4,10))
        self.accepted=tk.BooleanVar()
        ttk.Checkbutton(frame,text='For VIN lookup: I have read and agree to HERE Terms of Use',variable=self.accepted).pack(anchor='w')
        ttk.Button(frame,text='Read HERE Terms of Use',command=lambda:webbrowser.open('https://legal.here.com/en-gb/terms')).pack(anchor='w',pady=(2,10))
        ttk.Label(frame,text='Destination: mounted FAT32 USB root (HereMapsV1 is created automatically)').pack(anchor='w')
        line=ttk.Frame(frame);line.pack(fill='x',pady=(4,8))
        self.destination=tk.StringVar();ttk.Entry(line,textvariable=self.destination).pack(side='left',fill='x',expand=True)
        ttk.Button(line,text='Choose folder…',command=self.choose).pack(side='right',padx=(8,0))
        self.overwrite=tk.BooleanVar()
        ttk.Checkbutton(frame,text='Allow replacing files with the same catalog paths',variable=self.overwrite).pack(anchor='w')
        ttk.Label(frame,text='Full USB and in-car validation is still required. This is an experimental compatibility client.').pack(anchor='w',pady=8)
        controls=ttk.Frame(frame);controls.pack(fill='x',pady=(0,10))
        self.preview=ttk.Button(controls,text='Check catalog',command=lambda:self.start(False));self.preview.pack(side='left')
        self.download=ttk.Button(controls,text='Download to USB',command=lambda:self.start(True));self.download.pack(side='left',padx=8)
        self.cancel=ttk.Button(controls,text='Stop',command=self.stop,state='disabled');self.cancel.pack(side='left')
        self.log=tk.Text(frame,height=14,wrap='word',state='disabled');self.log.pack(fill='both',expand=True)
        root.protocol('WM_DELETE_WINDOW',self.close);root.after(150,self.poll)
    def choose(self):
        folder=filedialog.askdirectory(title='Select the root of the mounted USB')
        if folder:self.destination.set(folder)
    def start(self,download):
        if self.running:return
        url=self.url.get().strip()
        if not url:
            messagebox.showerror('Missing input','Enter your VIN or paste the launch link from your Honda map portal.');return
        if self.mode.get()=='vin' and not self.accepted.get():
            messagebox.showerror('Terms of Use','Read the linked HERE terms and confirm your agreement before VIN lookup.');return
        if download and not self.destination.get():
            messagebox.showerror('Missing destination','Choose the mounted USB directory.');return
        if download and not messagebox.askyesno('Start download?',f"Download approximately 26.5 GB for the current catalog to:\n{self.destination.get()}\n\nCheck that this is your prepared USB. No drive will be formatted."):
            return
        self.running=True;self.preview.config(state='disabled');self.download.config(state='disabled');self.cancel.config(state='normal')
        self.stop_requested=threading.Event()
        command=[sys.executable,'-u',str(Path(__file__).with_name('honda_maps.py'))]
        if download:command+=['--download','--dest',self.destination.get()]
        if self.overwrite.get():command+=['--overwrite']
        source_flag='--vin-file' if self.mode.get()=='vin' else '--link-file'
        if self.mode.get()=='vin':command+=['--accept-here-terms']
        threading.Thread(target=self.worker,args=(url,command,source_flag),daemon=True).start()
    def worker(self,url,command,source_flag):
        name=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',prefix='honda-link-',delete=False) as f:
                name=f.name;f.write(url)
            self.process=subprocess.Popen(command+[source_flag,name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            if self.stop_requested.is_set():self.process.send_signal(signal.SIGINT)
            for line in self.process.stdout:self.messages.put(line)
            code=self.process.wait();self.messages.put(f'Process finished with exit code {code}.\n')
        except Exception:
            self.messages.put('Unable to start downloader. Check the Python installation and destination.\n')
        finally:
            if name:
                try:os.unlink(name)
                except OSError:pass
            self.process=None;self.messages.put(None)
    def stop(self):
        self.stop_requested.set()
        p=self.process
        if p and p.poll() is None:
            try:p.send_signal(signal.SIGINT)
            except ProcessLookupError:pass
    def poll(self):
        try:
            while True:
                line=self.messages.get_nowait()
                if line is None:
                    self.running=False;self.preview.config(state='normal');self.download.config(state='normal');self.cancel.config(state='disabled')
                else:
                    self.log.config(state='normal');self.log.insert('end',line);self.log.see('end');self.log.config(state='disabled')
        except queue.Empty:pass
        self.root.after(150,self.poll)
    def close(self):
        if self.running:
            if messagebox.askyesno('Stop download?','Stop the current download? Partial map files can be resumed.'):
                self.stop();self.root.after(200,self.finish_close)
        else:self.root.destroy()
    def finish_close(self):
        if self.running:self.root.after(200,self.finish_close)
        else:self.root.destroy()

if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()

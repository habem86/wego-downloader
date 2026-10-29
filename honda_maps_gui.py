#!/usr/bin/env python3
"""Minimal native Tk interface for the Honda NDS downloader."""
import os
from pathlib import Path
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk
import webbrowser

PAPER = '#F1F0EA'
CARD = '#FAF9F5'
INK = '#20251F'
MUTED = '#73796F'
LINE = '#D9DCD2'
ACCENT = '#BD482F'
PANEL = '#20251F'
PANEL_TEXT = '#F1F0E7'
PANEL_MUTED = '#A2AC9B'
SIGNAL = '#D6E8AC'


class App:
    def __init__(self, root, launch_url=None):
        self.root = root
        self.process = None
        self.messages = queue.Queue()
        self.running = False
        self.active_download = False
        self.stop_requested = threading.Event()
        self.total_files = self.completed_files = self.current_index = 0
        self.catalog_gb = None
        self.catalog_source = None
        self.current_file = ''
        self.last_error = ''
        self.log_open = False
        self.busy_widgets = []
        self._closing = False
        families = set(font.families(root))
        self.sans = next((x for x in ('Inter', 'Noto Sans', 'DejaVu Sans') if x in families), 'Helvetica')
        self.mono = next((x for x in ('JetBrains Mono', 'DejaVu Sans Mono', 'Liberation Mono') if x in families), 'Courier')
        self.mode = tk.StringVar(value='link' if launch_url else 'vin')
        self.url = tk.StringVar(value=launch_url or '')
        self.source_values = {'vin': '', 'link': launch_url or ''}
        self._last_mode = self.mode.get()
        self.destination = tk.StringVar()
        self.accepted = tk.BooleanVar()
        self.overwrite = tk.BooleanVar()
        self.revealed = False
        root.title('Honda Map Downloader')
        root.geometry('1040x870')
        root.minsize(940, 820)
        root.configure(bg=PAPER)
        root.option_add('*Font', (self.sans, 10))
        style = ttk.Style(root)
        style.theme_use('clam')
        self._track_image = tk.PhotoImage(master=root, width=1, height=4)
        self._track_image.put('#3D4438', to=(0, 0, 1, 4))
        self._fill_image = tk.PhotoImage(master=root, width=48, height=4)
        self._fill_image.put(SIGNAL, to=(0, 0, 48, 4))
        style.element_create('Utility.Progressbar.trough', 'image', self._track_image, border=0, sticky='nswe')
        style.element_create('Utility.Progressbar.pbar', 'image', self._fill_image, border=0, sticky='nswe')
        style.layout('Utility.Horizontal.TProgressbar', [('Utility.Progressbar.trough', {
            'sticky': 'nswe', 'children': [('Utility.Progressbar.pbar', {'side': 'left', 'sticky': 'ns'})]})])
        style.layout('Utility.Vertical.TScrollbar', [('Vertical.Scrollbar.trough', {
            'sticky': 'ns', 'children': [('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})]})])
        style.configure('Utility.Vertical.TScrollbar', background='#4B5444', troughcolor=PANEL,
                        bordercolor=PANEL, lightcolor='#4B5444', darkcolor='#4B5444',
                        borderwidth=0, arrowsize=8)
        self._build()
        self.mode.trace_add('write', self._mode_changed)
        self.url.trace_add('write', self._input_changed)
        self.accepted.trace_add('write', self._input_changed)
        self.destination.trace_add('write', self._destination_changed)
        self._mode_changed()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self._poll_id = root.after(100, self.poll)

    def label(self, parent, text, size=10, color=INK, bg=None, mono=False, bold=False, **kw):
        return tk.Label(parent, text=text, bg=bg or parent.cget('bg'), fg=color,
                        font=(self.mono if mono else self.sans, size, 'bold' if bold else 'normal'), **kw)

    def button(self, parent, text, command, kind='secondary', **kw):
        primary = kind == 'primary'
        dark = kind == 'dark'
        bg = INK if primary else PANEL if dark else CARD
        fg = CARD if primary else PANEL_TEXT if dark else INK
        button = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                           activebackground=ACCENT if primary else '#343C2E' if dark else '#E9EBE2',
                           activeforeground=CARD if primary or dark else INK,
                           disabledforeground='#6F7867' if dark else '#A8ADA1',
                           font=(self.mono, 10, 'bold'), relief='flat', borderwidth=0,
                           highlightthickness=1, highlightbackground=bg if primary or dark else LINE,
                           highlightcolor=ACCENT, padx=16, pady=11, cursor='hand2', **kw)
        return button

    def entry(self, parent, variable, size=11):
        widget = tk.Entry(parent, textvariable=variable, bg=CARD, fg=INK, insertbackground=INK,
                          disabledbackground=CARD, disabledforeground=MUTED,
                          selectbackground=INK, selectforeground=CARD,
                          font=(self.mono, size), relief='flat', borderwidth=0,
                          highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT)
        self.busy_widgets.append(widget)
        return widget

    def check(self, parent, text, variable):
        widget = tk.Checkbutton(parent, text=text, variable=variable, bg=CARD, fg=INK,
                                selectcolor=CARD, activebackground=CARD, activeforeground=INK,
                                disabledforeground=MUTED, font=(self.sans, 10),
                                highlightthickness=0, borderwidth=0, padx=0, anchor='w', cursor='hand2')
        self.busy_widgets.append(widget)
        return widget

    def _build(self):
        shell = tk.Frame(self.root, bg=PAPER, padx=32, pady=24)
        shell.pack(fill='both', expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(4, weight=1)
        header = tk.Frame(shell, bg=PAPER)
        header.grid(row=0, column=0, sticky='ew')
        self.label(header, 'H/M', size=15, mono=True, bold=True).pack(side='left')
        self.label(header, 'HONDA  /  MAP UTILITY', size=9, mono=True, color=MUTED).pack(side='left', padx=18)
        self.header_state = self.label(header, '●  READY', size=9, mono=True, color=ACCENT)
        self.header_state.pack(side='right')
        hero = tk.Frame(shell, bg=PAPER)
        hero.grid(row=1, column=0, sticky='ew', pady=(24, 22))
        self.label(hero, 'Map transfer', size=30, bold=True).pack(anchor='w')
        self.label(hero, 'Honda Civic  /  Europe', color=MUTED, size=11).pack(anchor='w', pady=(3, 0))
        cards = tk.Frame(shell, bg=PAPER)
        cards.grid(row=2, column=0, sticky='ew')
        cards.columnconfigure((0, 1), weight=1, uniform='cards')
        source = self._card(cards, 0, '01', 'SOURCE', right=False)
        destination = self._card(cards, 1, '02', 'DESTINATION', right=True)
        modes = tk.Frame(source, bg=CARD)
        modes.pack(fill='x', pady=(14, 16))
        modes.columnconfigure((0, 1), weight=1, uniform='source_modes')
        self.mode_buttons = {}
        for column, (value, text) in enumerate([('vin', 'VIN'), ('link', 'LAUNCH LINK')]):
            b = self.button(modes, text, lambda v=value: self.mode.set(v))
            b.grid(row=0, column=column, sticky='ew')
            self.mode_buttons[value] = b
            self.busy_widgets.append(b)
        self.source_title = self.label(source, 'Vehicle identification number', size=10)
        self.source_title.pack(anchor='w', pady=(0, 7))
        input_row = tk.Frame(source, bg=CARD)
        input_row.pack(fill='x')
        self.source_entry = self.entry(input_row, self.url, size=12)
        self.source_entry.pack(side='left', fill='both', expand=True, ipady=11)
        self.reveal_button = self.button(input_row, 'SHOW', self.toggle_reveal)
        self.reveal_button.pack(side='right', padx=(6, 0))
        self.busy_widgets.append(self.reveal_button)
        self.terms = tk.Frame(source, bg=CARD)
        self.check(self.terms, 'I have read and agree to HERE Terms of Use', self.accepted).pack(anchor='w')
        self.terms_link = tk.Label(self.terms, text='Read terms', fg=ACCENT, bg=CARD,
                                  font=(self.sans, 10, 'underline'), cursor='hand2', takefocus=1)
        self.terms_link.pack(anchor='w', padx=22, pady=(2, 0))
        self.terms_link.bind('<Button-1>', self.open_terms)
        self.terms_link.bind('<Return>', self.open_terms)
        self.terms_link.bind('<space>', self.open_terms)
        self.link_hint = self.label(source, 'Signed launch links stay private.', color=MUTED, size=10)
        self.source_note = self.label(source, 'CZECH REPUBLIC  /  ENGLISH PORTAL', size=8, mono=True, color=MUTED)
        self.source_note.pack(side='bottom', anchor='w', pady=(8, 0))
        self.label(destination, 'Mounted USB drive', size=10).pack(anchor='w', pady=(22, 7))
        dest_row = tk.Frame(destination, bg=CARD)
        dest_row.pack(fill='x')
        self.destination_entry = self.entry(dest_row, self.destination, size=10)
        self.destination_entry.pack(side='left', fill='both', expand=True, ipady=11)
        self.browse_button = self.button(dest_row, 'BROWSE', self.choose)
        self.browse_button.pack(side='right', padx=(6, 0))
        self.busy_widgets.append(self.browse_button)
        self.drive_space = self.label(destination, 'No drive selected', color=MUTED, size=10)
        self.drive_space.pack(anchor='w', pady=(10, 18))
        tk.Frame(destination, height=1, bg=LINE).pack(fill='x')
        output = tk.Frame(destination, bg=CARD)
        output.pack(fill='x', pady=(12, 10))
        self.label(output, 'OUTPUT', size=8, color=MUTED, mono=True).pack(side='left')
        self.output_label = self.label(output, 'HereMapsV1 /', size=10, mono=True)
        self.output_label.pack(side='right')
        self.check(destination, 'Allow replacing existing catalog files', self.overwrite).pack(anchor='w')
        self.label(destination, 'Select the USB root. Use a prepared FAT32 drive.', size=9, color=MUTED).pack(side='bottom', anchor='w', pady=(8, 0))
        actions = tk.Frame(shell, bg=PAPER)
        actions.grid(row=3, column=0, sticky='ew', pady=(16, 20))
        self.preview = self.button(actions, 'Check catalog', lambda: self.start(False))
        self.preview.pack(side='left')
        self.action_hint = self.label(actions, 'Enter a VIN to begin.', color=MUTED, size=9)
        self.action_hint.pack(side='left', padx=15)
        self.download = self.button(actions, 'Download to USB', lambda: self.start(True), kind='primary')
        self.download.pack(side='right')
        self._build_transfer(shell)
        footer = tk.Frame(shell, bg=PAPER)
        footer.grid(row=5, column=0, sticky='ew', pady=(14, 0))
        self.label(footer, 'INDEPENDENT LINUX CLIENT', size=8, color=MUTED, mono=True).pack(side='left')
        self.label(footer, 'Experimental · vehicle validation pending', size=9, color=MUTED).pack(side='right')

    def _card(self, parent, column, number, title, right=False):
        card = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1, height=306)
        card.grid(row=0, column=column, sticky='ew', padx=(8, 0) if right else (0, 8))
        card.pack_propagate(False)
        body = tk.Frame(card, bg=CARD, padx=22, pady=20)
        body.pack(fill='both', expand=True)
        heading = tk.Frame(body, bg=CARD)
        heading.pack(fill='x')
        self.label(heading, number, size=9, mono=True, color=ACCENT).pack(side='left')
        self.label(heading, title, size=9, mono=True, bold=True).pack(side='left', padx=12)
        return body

    def _build_transfer(self, parent):
        panel = tk.Frame(parent, bg=PANEL, padx=24, pady=18)
        self.transfer_panel = panel
        panel.grid(row=4, column=0, sticky='nsew')
        panel.columnconfigure(0, weight=1)
        heading = tk.Frame(panel, bg=PANEL)
        heading.grid(row=0, column=0, sticky='ew')
        self.label(heading, '03  /  TRANSFER', size=9, mono=True, color=PANEL_MUTED).pack(side='left')
        self.cancel = self.button(heading, 'Stop', self.stop, kind='dark')
        self.cancel.configure(pady=2, state='disabled')
        self.cancel.pack(side='right')
        self.transfer_title = self.label(panel, 'Waiting for source', size=19, bold=True, color=PANEL_TEXT)
        self.transfer_title.grid(row=1, column=0, sticky='w', pady=(10, 1))
        self.transfer_detail = self.label(panel, 'Check a catalog to see the available update.', size=10,
                                          color=PANEL_MUTED, anchor='w', justify='left', wraplength=850)
        self.transfer_detail.grid(row=2, column=0, sticky='ew')
        track = tk.Frame(panel, height=4, bg='#3D4438')
        track.grid(row=3, column=0, sticky='ew', pady=(16, 12))
        self.progress = ttk.Progressbar(track, style='Utility.Horizontal.TProgressbar', mode='determinate', maximum=100)
        self.progress.place(x=0, y=0, relwidth=1, height=4)
        stats = tk.Frame(panel, bg=PANEL)
        stats.grid(row=4, column=0, sticky='ew')
        self.files_stat = self.label(stats, 'FILES  --', size=9, mono=True, color=SIGNAL)
        self.files_stat.pack(side='left')
        self.size_stat = self.label(stats, 'MAP DATA  --', size=9, mono=True, color=PANEL_MUTED)
        self.size_stat.pack(side='left', padx=28)
        self.log_toggle = self.button(stats, 'Activity +', self.toggle_log, kind='dark')
        self.log_toggle.configure(padx=0, pady=0)
        self.log_toggle.pack(side='right')
        self.log_frame = tk.Frame(panel, bg=PANEL)
        self.log = tk.Text(self.log_frame, height=7, wrap='word', state='disabled', bg=PANEL,
                           fg=PANEL_MUTED, selectbackground='#4B5444', selectforeground=PANEL_TEXT,
                           font=(self.mono, 9), relief='flat', borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.log_frame, orient='vertical', style='Utility.Vertical.TScrollbar', command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        panel.rowconfigure(5, weight=1)

    def _mode_changed(self, *_):
        mode = self.mode.get()
        if self._last_mode != mode:
            self.source_values[self._last_mode] = self.url.get()
            self.url.set(self.source_values[mode])
            self._last_mode = mode
        vin = mode == 'vin'
        for value, button in self.mode_buttons.items():
            selected = value == self.mode.get()
            button.configure(bg=INK if selected else CARD, fg=CARD if selected else MUTED,
                             highlightbackground=INK if selected else LINE)
        self.source_title.configure(text='Vehicle identification number' if vin else 'Portal launch link')
        self.terms.pack_forget()
        self.link_hint.pack_forget()
        if vin:
            self.terms.pack(fill='x', pady=(12, 0), before=self.source_note)
        else:
            self.link_hint.pack(anchor='w', pady=(14, 0), before=self.source_note)
        self.source_note.configure(text='CZECH REPUBLIC  /  ENGLISH PORTAL' if vin else 'OFFICIAL PORTAL  /  SIGNED LINK')
        self.revealed = vin
        self._set_reveal()
        self._input_changed()

    def toggle_reveal(self):
        self.revealed = not self.revealed
        self._set_reveal()

    def _set_reveal(self):
        self.source_entry.configure(show='' if self.revealed else '•')
        self.reveal_button.configure(text='HIDE' if self.revealed else 'SHOW')

    def _input_changed(self, *_):
        if not self.running:
            if self.catalog_source and self.catalog_source != (self.mode.get(), self.url.get().strip()):
                self.catalog_source = None
                self.catalog_gb = None
                self.total_files = self.completed_files = 0
                self.progress.configure(mode='determinate', maximum=100, value=0)
                self.files_stat.configure(text='FILES  --')
                self.size_stat.configure(text='MAP DATA  --')
                self.transfer_title.configure(text='Source changed', fg=PANEL_TEXT)
                self.transfer_detail.configure(text='Check the catalog for this source before transferring.')
                self.header_state.configure(text='●  READY', fg=ACCENT)
            self._update_actions()

    def _update_actions(self):
        has_source = bool(self.url.get().strip())
        consent = self.mode.get() != 'vin' or self.accepted.get()
        ready = has_source and consent and not self.running
        self.preview.configure(state='normal' if ready else 'disabled')
        self.download.configure(state='normal' if ready and self.destination.get().strip() else 'disabled')
        if self.running:
            hint = 'You can stop and resume this transfer.'
        elif not has_source:
            hint = 'Enter a VIN to begin.' if self.mode.get() == 'vin' else 'Paste your launch link.'
        elif not consent:
            hint = 'Read and accept the HERE terms.'
        elif not self.destination.get().strip():
            hint = 'Check the catalog, then choose a USB.'
        else:
            hint = 'Ready to check or download.'
        self.action_hint.configure(text=hint)

    def _destination_changed(self, *_):
        value = self.destination.get().strip()
        try:
            path = Path(value).expanduser()
            if not value or not path.is_dir():
                raise OSError()
            free = shutil.disk_usage(path).free / 1e9
            text = f'{free:.1f} GB available · check the drive is FAT32'
        except (OSError, RuntimeError):
            text = 'No drive selected' if not value else 'Select an accessible, mounted USB directory'
        self.drive_space.configure(text=text)
        self._input_changed()

    def choose(self):
        folder = filedialog.askdirectory(parent=self.root, title='Select the mounted USB root, not HereMapsV1')
        if folder:
            self.destination.set(folder)

    def open_terms(self, _event=None):
        if not self.running:
            webbrowser.open('https://legal.here.com/en-gb/terms')

    def start(self, download):
        if self.running:
            return
        value = self.url.get().strip()
        if not value:
            messagebox.showerror('Missing input', 'Enter your VIN or paste a portal launch link.', parent=self.root)
            return
        if self.mode.get() == 'vin' and not self.accepted.get():
            messagebox.showerror('Terms of Use', 'Read the HERE terms and confirm your agreement before VIN lookup.', parent=self.root)
            return
        destination = self.destination.get().strip()
        if download and not destination:
            messagebox.showerror('Missing destination', 'Choose the mounted USB root.', parent=self.root)
            return
        if download:
            known_catalog = self.catalog_source == (self.mode.get(), value)
            size = f'{self.catalog_gb:.2f} GB' if known_catalog and self.catalog_gb is not None else 'the map files listed by the portal'
            if not messagebox.askyesno('Download to USB?', f'Download {size} to:\n{destination}\n\nThe release folder (usually HereMapsV1) is created inside this directory. The drive will not be formatted.', parent=self.root):
                return
        self.running = True
        self.active_download = download
        self.stop_requested.clear()
        self.completed_files = self.current_index = self.total_files = 0
        self.current_file = self.last_error = ''
        self.files_stat.configure(text='FILES  --')
        self.progress.configure(mode='indeterminate', maximum=100, value=0)
        self.progress.start(16)
        self.header_state.configure(text='●  WORKING', fg=ACCENT)
        self.transfer_title.configure(text='Loading catalog', fg=PANEL_TEXT)
        self.transfer_detail.configure(text='Connecting to the European update portal…')
        for widget in self.busy_widgets:
            widget.configure(state='disabled')
        self.cancel.configure(state='normal')
        self._update_actions()
        command = [sys.executable, '-u', str(Path(__file__).with_name('honda_maps.py'))]
        if download:
            command += ['--download', '--dest', destination]
        if self.overwrite.get():
            command += ['--overwrite']
        source_flag = '--vin-file' if self.mode.get() == 'vin' else '--link-file'
        if self.mode.get() == 'vin':
            command += ['--accept-here-terms']
        threading.Thread(target=self.worker, args=(value, command, source_flag), daemon=True).start()

    def worker(self, value, command, source_flag):
        name = None
        code = 1
        try:
            with tempfile.NamedTemporaryFile(mode='w', prefix='honda-source-', delete=False) as handle:
                name = handle.name
                handle.write(value)
            self.process = subprocess.Popen(command + [source_flag, name], stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True)
            if self.stop_requested.is_set():
                self.process.send_signal(signal.SIGINT)
            for line in self.process.stdout:
                self.messages.put(('line', line))
            code = self.process.wait()
        except Exception:
            self.messages.put(('line', 'Error: Unable to start downloader. Check Python and file permissions.\n'))
        finally:
            if name:
                try:
                    os.unlink(name)
                except OSError:
                    pass
            self.process = None
            self.messages.put(('finished', code))

    def _handle_line(self, line):
        text = line.strip()
        summary = re.search(r'\| (\d+) files \| ([\d.]+) GB \+ license', text)
        if summary:
            self.total_files = int(summary[1])
            self.catalog_gb = float(summary[2])
            self.catalog_source = (self.mode.get(), self.url.get().strip())
            self.size_stat.configure(text=f'MAP DATA  {self.catalog_gb:.2f} GB')
            if self.active_download:
                self.progress.stop()
                self.progress.configure(mode='determinate', maximum=self.total_files, value=0)
                self.transfer_title.configure(text='Downloading files')
            self._update_file_count()
        if text.startswith('Map folders: '):
            folders = text.partition(': ')[2].split(', ')
            output = folders[0] + ' /' if len(folders) == 1 else f'{len(folders)} release folders'
            self.output_label.configure(text=output)
        current = re.match(r'^\[(\d+)/(\d+)\] (.+)$', text)
        if current:
            self.current_index, self.total_files = int(current[1]), int(current[2])
            self.current_file = current[3]
            self.transfer_detail.configure(text=self.current_file)
        if text.startswith(('verified', 'license saved unchanged')) and self.current_index:
            self.completed_files = self.current_index
            self.progress.configure(value=self.completed_files)
            self._update_file_count()
        if text.startswith('Error:'):
            self.last_error = text[6:].strip()
        self.log.configure(state='normal')
        self.log.insert('end', line)
        if int(self.log.index('end-1c').split('.')[0]) > 600:
            self.log.delete('1.0', '100.0')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _update_file_count(self):
        total = f'{self.total_files:,}'
        label = f'FILES  {self.completed_files:,} / {total} complete' if self.active_download else f'FILES  {total} in catalog'
        self.files_stat.configure(text=label)

    def _finish(self, code):
        self.running = False
        self.progress.stop()
        for widget in self.busy_widgets:
            widget.configure(state='normal')
        self.cancel.configure(state='disabled')
        if code == 0:
            title = 'Download complete' if self.active_download else 'Catalog ready'
            detail = 'Safely eject the USB, then follow Honda’s in-car instructions.' if self.active_download else 'Choose the mounted USB root and start the transfer.'
            self.header_state.configure(text='●  COMPLETE' if self.active_download else '●  READY', fg=MUTED)
            self.transfer_title.configure(text=title, fg=SIGNAL)
        elif self.stop_requested.is_set():
            detail = 'Partial map files are kept. Start again with the same destination to resume.'
            self.transfer_title.configure(text='Stopped', fg=PANEL_TEXT)
            self.header_state.configure(text='●  STOPPED', fg=MUTED)
        else:
            detail = self.last_error or 'Open Activity for details and check the source or destination.'
            self.transfer_title.configure(text='Needs attention', fg='#F0A38A')
            self.header_state.configure(text='●  ATTENTION', fg=ACCENT)
        self.transfer_detail.configure(text=detail)
        self.progress.configure(mode='determinate', maximum=max(self.total_files, 1), value=self.completed_files)
        self._update_actions()

    def toggle_log(self):
        self.log_open = not self.log_open
        if self.log_open:
            self.transfer_title.grid_remove()
            self.transfer_detail.grid_remove()
            self.transfer_panel.rowconfigure(1, weight=1)
            self.transfer_panel.rowconfigure(5, weight=0)
            self.log_frame.grid(row=1, column=0, rowspan=2, sticky='nsew', pady=(10, 0))
        else:
            self.log_frame.grid_remove()
            self.transfer_panel.rowconfigure(1, weight=0)
            self.transfer_panel.rowconfigure(5, weight=1)
            self.transfer_title.grid()
            self.transfer_detail.grid()
        self.log_toggle.configure(text='Activity -' if self.log_open else 'Activity +')

    def stop(self):
        self.stop_requested.set()
        self.cancel.configure(state='disabled')
        self.transfer_title.configure(text='Stopping…', fg=PANEL_TEXT)
        process = self.process
        if process and process.poll() is None:
            try:
                process.send_signal(signal.SIGINT)
            except ProcessLookupError:
                pass

    def poll(self):
        try:
            for _ in range(250):
                kind, payload = self.messages.get_nowait()
                if kind == 'line':
                    self._handle_line(payload)
                elif kind == 'finished':
                    self._finish(payload)
        except queue.Empty:
            pass
        if not self._closing:
            self._poll_id = self.root.after(100, self.poll)

    def close(self):
        if self.running:
            if messagebox.askyesno('Stop download?', 'Stop this transfer? Partial map files can be resumed.', parent=self.root):
                self.stop()
                self.root.after(200, self.finish_close)
        else:
            self._closing = True
            self.root.after_cancel(self._poll_id)
            self.root.destroy()

    def finish_close(self):
        if self.running:
            self.root.after(200, self.finish_close)
        else:
            self.close()


if __name__ == '__main__':
    root = tk.Tk()
    App(root, sys.argv[1] if len(sys.argv) > 1 else None)
    root.mainloop()

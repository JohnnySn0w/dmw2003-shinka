"""Windows first-run wizard and stable launcher (bundled by PyInstaller)."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from setup_core import (TOOLCHAIN, Cancelled, SetupLock, activate,
                        data_root, default_duckstation_roots, describe_card,
                        discover_cards, emulator_running, launch_command,
                        read_settings, remembered_disc_ok, validate_disc)
from setup_prepare import prepare


class Launcher:
    def __init__(self, window, root, sdk):
        self.window, self.root, self.sdk = window, root, sdk
        self.settings = read_settings(root)
        self.events, self.cancel = queue.Queue(), threading.Event()
        self.busy, self.cards = False, []
        window.title('Shinka')
        window.geometry('820x780')
        window.minsize(740, 760)
        window.configure(bg='#101c32')
        icon = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))/'assets/shinka.ico'
        if icon.is_file():
            window.iconbitmap(str(icon))
        style = ttk.Style(window)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 10))
        style.configure('TFrame', background='#101c32')
        style.configure('TLabel', background='#101c32', foreground='#e6f2ff')
        style.configure('TCheckbutton', background='#101c32', foreground='#e6f2ff')
        style.map('TCheckbutton', background=[('active', '#1c3150')])
        style.configure('Title.TLabel', font=('Segoe UI', 26, 'bold'), foreground='#49bdff')
        style.configure('Accent.TButton', font=('Segoe UI', 11, 'bold'), padding=(16, 8))
        body = ttk.Frame(window, padding=24)
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        ttk.Label(body, text='SHINKA', style='Title.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Label(body, text='Set up your disc and memory card.', font=('Segoe UI', 12)).grid(row=1, column=0, sticky='w', pady=(2, 18))
        ttk.Label(body, text='1  Choose your Digimon World 2003 (Europe) disc').grid(row=2, column=0, sticky='w')
        self.disc = tk.StringVar(value=self.settings.get('disc', {}).get('cue', ''))
        row = ttk.Frame(body)
        row.grid(row=3, column=0, sticky='ew', pady=(8, 5))
        row.columnconfigure(0, weight=1)
        ttk.Entry(row, textvariable=self.disc, state='readonly').grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.browse = ttk.Button(row, text='Choose CUE…', command=self.choose_disc)
        self.browse.grid(row=0, column=1)
        ttk.Label(body, text='Leave the CUE and BIN where they are. Shinka remembers their location.').grid(row=4, column=0, sticky='w')
        ttk.Label(body, text='2  Start fresh or copy a memory card', font=('Segoe UI', 11, 'bold')).grid(row=5, column=0, sticky='w', pady=(20, 8))
        self.search = tk.BooleanVar(value=False)
        self.check = ttk.Checkbutton(body, text='Search for existing emulator data (DuckStation)', variable=self.search, command=self.toggle_search)
        self.check.grid(row=6, column=0, sticky='w')
        self.import_frame = ttk.Frame(body)
        self.import_frame.grid(row=7, column=0, sticky='nsew', pady=8)
        self.import_frame.columnconfigure(0, weight=1)
        self.card_list = ttk.Combobox(self.import_frame, state='readonly', values=['Start fresh — do not import'])
        self.card_list.grid(row=0, column=0, columnspan=3, sticky='ew')
        self.card_list.current(0)
        ttk.Button(self.import_frame, text='Choose folder…', command=self.choose_folder).grid(row=1, column=0, sticky='w', pady=8)
        ttk.Button(self.import_frame, text='Choose card file…', command=self.choose_card).grid(row=1, column=1, sticky='w')
        self.slot = tk.StringVar(value='1')
        ttk.Combobox(self.import_frame, textvariable=self.slot, values=['1', '2'], state='readonly', width=3).grid(row=1, column=2, sticky='e')
        ttk.Label(self.import_frame, text='Copy into Shinka slot 1 or 2. Original cards are never changed.').grid(row=2, column=0, columnspan=3, sticky='w')
        self.closed = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.import_frame, text='I have closed DuckStation before importing', variable=self.closed).grid(row=3, column=0, columnspan=3, sticky='w', pady=4)
        ttk.Label(self.import_frame, text='Emulator savestates (.sav) cannot be imported. Load the copied card with Continue.').grid(row=4, column=0, columnspan=3, sticky='w')
        self.import_frame.grid_remove()
        self.note = ttk.Label(body, wraplength=730)
        self.note.grid(row=8, column=0, sticky='ew', pady=(12, 8))
        self.status = tk.StringVar(value='Choose your CUE to begin.' if not self.settings.get('runtime') else 'Your existing installation and save profile are ready.')
        ttk.Label(body, textvariable=self.status, wraplength=730).grid(row=9, column=0, sticky='ew', pady=6)
        self.progress = ttk.Progressbar(body, mode='determinate')
        self.progress.grid(row=10, column=0, sticky='ew', pady=(2, 12))
        actions = ttk.Frame(body)
        actions.grid(row=11, column=0, sticky='ew')
        self.prepare_button = ttk.Button(actions, text='Prepare Shinka', style='Accent.TButton', command=self.start_prepare)
        self.prepare_button.pack(side='left')
        self.play_button = ttk.Button(actions, text='Play', style='Accent.TButton', command=self.play)
        self.play_button.pack(side='left', padx=8)
        self.cancel_button = ttk.Button(actions, text='Cancel', command=self.cancel.set, state='disabled')
        self.cancel_button.pack(side='right')
        footer = ttk.Frame(body)
        footer.grid(row=12, column=0, sticky='ew', pady=(16, 0))
        ttk.Button(footer, text='Open saves', command=self.open_saves).pack(side='left')
        ttk.Button(footer, text='Open preparation logs', command=self.open_logs).pack(side='left', padx=8)
        ttk.Label(body, text='Choose language with Start / Enter. In-game: A / X confirms; Y / A goes back.').grid(row=13, column=0, sticky='w', pady=(10, 0))
        window.protocol('WM_DELETE_WINDOW', self.close)
        self.refresh()
        window.after(80, self.poll)

    def refresh(self):
        ready = self.settings.get('runtime') and (Path(self.settings['runtime'])/'dmw2003-shinka.exe').is_file()
        self.play_button.configure(state='normal' if ready and not self.busy and remembered_disc_ok(self.settings.get('disc', {})) else 'disabled')
        self.prepare_button.configure(text=('Save setup' if self.current_version() else 'Update Shinka') if ready else 'Prepare Shinka', state='disabled' if self.busy else 'normal')
        for control in (self.browse, self.check):
            control.configure(state='disabled' if self.busy else 'normal')
        self.cancel_button.configure(state='normal' if self.busy else 'disabled')
        self.note.configure(text=(f"Save profile: {self.settings.get('profile', '')}" if ready else
            f"First setup downloads {TOOLCHAIN['bytes'] / 1024**2:.0f} MB of preparation tools and needs 6 GB free. "
            'It may take several minutes. No developer tools need to be installed. Original music is included; alternate soundtracks can be prepared separately.'))

    def current_version(self):
        try:
            expected = json.loads(self.sdk.with_suffix('.json').read_text(encoding='utf-8'))
            return self.settings.get('sdk', {}).get('sdk_sha256') == expected['sdk_sha256']
        except (OSError, ValueError, KeyError):
            return False

    def choose_disc(self):
        path = filedialog.askopenfilename(title='Choose your disc CUE', filetypes=[('PlayStation cue sheet', '*.cue')])
        if path:
            self.disc.set(path)
            self.status.set('Choose Prepare Shinka / Save setup to check this disc.')

    def toggle_search(self):
        if self.search.get():
            self.import_frame.grid()
            self.scan(default_duckstation_roots())
        else:
            self.import_frame.grid_remove()
            self.cards.clear()
            self.card_list.configure(values=['Start fresh — do not import'])
            self.card_list.current(0)

    def scan(self, roots):
        try:
            cards, errors = discover_cards(roots)
            merged = {card['path']: card for card in self.cards + cards}
            self.cards = sorted(merged.values(), key=lambda c: c['path'].casefold())
            self.render_cards()
            self.status.set(f'Found {len(self.cards)} usable card(s). Choose one to copy, or start fresh.')
            if errors:
                messagebox.showwarning('Some locations could not be read', '\n'.join(errors[:8]))
        except (OSError, ValueError) as exc:
            messagebox.showerror('Could not search for cards', str(exc))

    def render_cards(self):
        self.card_list.configure(values=['Keep current saves / start fresh — do not import'] +
            [f"{c['path']} · 128 KiB · {datetime.fromtimestamp(c['modified']).strftime('%Y-%m-%d %H:%M')}" for c in self.cards])
        self.card_list.current(0)

    def choose_folder(self):
        path = filedialog.askdirectory(title='Choose DuckStation data, portable-install, or memcards folder')
        if path:
            self.scan([Path(path)])

    def choose_card(self):
        path = filedialog.askopenfilename(title='Choose a memory card', filetypes=[('Raw PlayStation memory cards', '*.mcd *.mcr')])
        if path:
            try:
                self.cards.append(dict(**describe_card(path), modified=Path(path).stat().st_mtime))
                self.render_cards()
                self.card_list.current(len(self.cards))
            except (OSError, ValueError) as exc:
                messagebox.showerror('Unsupported card', str(exc))

    def background(self, work):
        self.busy = True
        self.cancel.clear()
        self.refresh()
        def worker():
            try:
                self.events.put(('done', work()))
            except Exception as exc:
                self.events.put(('error', exc))
        threading.Thread(target=worker, daemon=True).start()

    def notify(self, stage, done, total):
        self.events.put(('progress', (stage, done, total)))

    def start_prepare(self):
        if self.busy:
            return
        cue = self.disc.get()
        if not cue:
            self.choose_disc()
            return
        selected = self.card_list.current() if self.search.get() else 0
        card = self.cards[selected-1]['path'] if selected > 0 else None
        if card and not self.closed.get():
            messagebox.showinfo('Close DuckStation first', 'Close DuckStation and check the confirmation before importing. Your source card will be copied, never moved.')
            return
        slot = int(self.slot.get())
        def work():
            if card and emulator_running():
                raise ValueError('DuckStation is still running. Close it before importing a card.')
            if self.current_version() and self.settings.get('runtime') and (Path(self.settings['runtime'])/'dmw2003-shinka.exe').is_file():
                prepared = dict(runtime=self.settings['runtime'], revision=self.settings['revision'],
                    sdk=self.settings.get('sdk', {}),
                    disc=validate_disc(cue, self.cancel, lambda done, total: self.notify('Checking your disc', done, total)))
            else:
                prepared = prepare(cue, self.sdk, self.root, self.cancel, self.notify)
            if self.cancel.is_set():
                raise Cancelled('Setup cancelled. Your previous setup is unchanged.')
            if card and emulator_running():
                raise ValueError('DuckStation opened during preparation. Close it and retry the import.')
            return activate(self.root, prepared, card, slot)
        self.background(work)

    def play(self):
        if self.busy:
            return
        try:
            command = launch_command(self.settings)
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror('Locate your disc or repair setup', str(exc))
            self.window.deiconify()
            return
        self.window.withdraw()
        def work():
            logs = self.root/'logs'
            logs.mkdir(parents=True, exist_ok=True)
            started = time.monotonic()
            with (logs/'game.log').open('w', encoding='utf-8') as log:
                proc = subprocess.Popen(command, cwd=self.settings['runtime'], stdout=log, stderr=log,
                                        creationflags=subprocess.CREATE_NO_WINDOW)
                result = proc.wait()
            if result != 0 or time.monotonic()-started < 2:
                raise RuntimeError('The game could not start. Your saves are unchanged. Open the logs folder for details, or locate your disc again.')
            return 'played'
        self.background(work)

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'progress':
                    stage, done, total = value
                    self.status.set(stage)
                    if total:
                        self.progress.stop()
                        self.progress.configure(mode='determinate', maximum=total, value=done)
                    elif self.progress['mode'] != 'indeterminate':
                        self.progress.configure(mode='indeterminate')
                        self.progress.start(20)
                else:
                    self.busy = False
                    self.progress.stop()
                    self.progress.configure(mode='determinate', value=0)
                    self.window.deiconify()
                    if kind == 'error':
                        self.status.set(str(value))
                        if not isinstance(value, Cancelled):
                            messagebox.showerror('Shinka setup', str(value))
                    elif value == 'played':
                        self.window.destroy()
                        return
                    else:
                        self.settings = value
                        self.status.set('Ready to play. Load an imported card with Continue in the game.')
                    self.refresh()
        except queue.Empty:
            pass
        self.window.after(80, self.poll)

    def open_saves(self):
        path = Path(self.settings.get('profile', self.root/'saves'))
        if self.settings.get('profile') and not path.is_dir():
            messagebox.showerror('Save folder missing', 'Restore your save folder before playing. Shinka will not create a blank replacement.')
            return
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    def open_logs(self):
        self.root.mkdir(parents=True, exist_ok=True)
        os.startfile(self.root)

    def close(self):
        if self.busy:
            self.cancel.set()
            self.status.set('Stopping preparation safely…')
        else:
            self.window.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings', action='store_true')
    parser.add_argument('--data', type=Path)
    parser.add_argument('--sdk', type=Path)
    args = parser.parse_args()
    root = args.data.resolve() if args.data else data_root()
    app = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
    sdk = args.sdk or app/'sdk.zip'
    window = tk.Tk()
    window.withdraw()
    try:
        with SetupLock(root):
            launcher = Launcher(window, root, sdk)
            if not args.settings and launcher.current_version() and launcher.settings.get('runtime') and remembered_disc_ok(launcher.settings.get('disc', {})):
                window.after(50, launcher.play)
            else:
                window.deiconify()
            window.mainloop()
    except Exception as exc:
        messagebox.showerror('Shinka', str(exc), parent=window)
        window.destroy()


if __name__ == '__main__':
    main()

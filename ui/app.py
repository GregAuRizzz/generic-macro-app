"""
GenericMacro v1.0 — Main Application Controller
"""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import webbrowser
import logging

from models.macro import Macro, Action
from core.engine import ExecutionEngine
from core.hotkeys import HotkeyManager
from core.recorder import Recorder
from ui.theme import *
from ui.sidebar import SidebarPanel
from ui.timeline import TimelinePanel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)

GITHUB_URL = "https://github.com/GregAuRizzz/generic-macro-app"

class GenericMacroApp:
    def __init__(self):
        self._macro = Macro(name="New Macro")
        self._engine = ExecutionEngine()
        self._hotkeys = HotkeyManager()
        self._recorder = Recorder()
        self._root: tk.Tk | None = None
        self._setup_engine_cbs()
        self._setup_recorder_cbs()

    def _setup_engine_cbs(self):
        def safe(fn):
            def wrap(*a, **kw):
                if self._root:
                    self._root.after(0, lambda: fn(*a, **kw))
            return wrap
            
        self._engine.on_start  = safe(self._on_eng_start)
        self._engine.on_stop   = safe(self._on_eng_stop)
        self._engine.on_action = safe(self._on_eng_action)
        self._engine.on_loop   = safe(self._on_eng_loop)
        self._engine.on_error  = safe(self._on_eng_error)

    def _setup_recorder_cbs(self):
        def safe(fn):
            def wrap(*a, **kw):
                if self._root:
                    self._root.after(0, lambda: fn(*a, **kw))
            return wrap
            
        self._recorder.on_action_recorded = safe(self._on_rec_action)
        self._recorder.on_stop            = safe(self._on_rec_stop)

    def _build_ui(self):
        root = tk.Tk()
        self._root = root
        root.title("⚡ GenericMacro v1.0")
        root.geometry("1180x740")
        root.minsize(900, 580)
        root.configure(bg=BG_DARKEST)

        # Left sidebar
        self._sidebar = SidebarPanel(root, callbacks={
            "on_run":             self._run,
            "on_stop":            self._stop,
            "on_record":          self._toggle_record,
            "on_macro_changed":   self._macro_changed,
            "on_hotkeys_changed": self._reconfigure_hotkeys,
            "on_import":          self._import_macro,
        })
        self._sidebar.pack(side="left", fill="y")

        # Right panel container
        right = tk.Frame(root, bg=BG_DARKEST)
        right.pack(side="left", fill="both", expand=True)

        # Toolbar
        self._toolbar = self._build_toolbar(right)
        self._toolbar.pack(fill="x")
        
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x")

        # Timeline (full area)
        self._timeline = TimelinePanel(right, on_changed=self._timeline_changed)
        self._timeline.pack(fill="both", expand=True)

        # Load initial state
        self._sidebar.load_macro(self._macro)
        self._timeline.set_actions(self._macro.actions)

        # Global Hotkey Binds (Internal to UI)
        root.bind("<Control-n>", lambda e: self._add_action())
        root.bind("<F7>", lambda e: self._toggle_record())
        root.bind("<F8>", lambda e: self._run())
        root.bind("<F9>", lambda e: self._stop())

        return root

    def _build_toolbar(self, parent) -> tk.Frame:
        bar = tk.Frame(parent, bg=BG_TOOLBAR, padx=PAD, pady=9)
        tk.Label(bar, text="🎯  Sequence Editor", bg=BG_TOOLBAR, fg=TEXT_PRIMARY, font=FONT_H2).pack(side="left")
        
        right = tk.Frame(bar, bg=BG_TOOLBAR)
        right.pack(side="right")
        
        from ui.widgets import FlatButton
        
        FlatButton(right, "⌥  GitHub", command=lambda: webbrowser.open(GITHUB_URL), bg=BG_CARD, hover_bg=BORDER_BRIGHT, font=FONT_SMALL, padx=10, pady=5).pack(side="right", padx=(4, 0))
        tk.Frame(right, bg=BORDER, width=1).pack(side="right", fill="y", padx=6)
        FlatButton(right, "🗑  Clear All", command=self._clear_all, bg=BG_CARD, hover_bg=RED_DIM, font=FONT_SMALL, padx=10, pady=5).pack(side="right", padx=2)
        FlatButton(right, "＋  Add Action", command=self._add_action, bg=ACCENT, hover_bg=ACCENT_HOVER, font=FONT_H3, padx=12, pady=5).pack(side="right", padx=4)
        
        return bar

    def run(self):
        root = self._build_ui()
        self._reconfigure_hotkeys()
        self._hotkeys.start_listening()
        root.protocol("WM_DELETE_WINDOW", self._on_close)
        root.mainloop()

    def _on_close(self):
        if self._engine.is_running: self._engine.stop()
        if self._recorder.is_recording: self._recorder.stop()
        self._hotkeys.stop_listening()
        self._root.destroy()

    # ── Engine Callbacks ──
    def _on_eng_start(self):
        self._sidebar.set_running(True)
        self._sidebar.set_status("▶  Running...", GREEN)

    def _on_eng_stop(self):
        self._sidebar.set_running(False)
        self._sidebar.set_status("Idle", TEXT_MUTED)
        self._timeline.highlight_action(None)

    def _on_eng_action(self, index: int, action: Action):
        self._timeline.highlight_action(index)

    def _on_eng_loop(self, loop_num: int):
        self._sidebar.set_status("▶  Running...", GREEN, loop=f"Loop #{loop_num}")

    def _on_eng_error(self, msg: str):
        self._sidebar.set_running(False)
        self._sidebar.set_status("⚠  Error", ORANGE)
        messagebox.showerror("Execution Error", msg)

    # ── Recorder Callbacks ──
    def _on_rec_action(self, action: Action):
        pass

    def _on_rec_stop(self, actions):
        pass

    # ── Logic ──
    def _run(self):
        if self._recorder.is_recording:
            messagebox.showwarning("Recording", "Stop recording before running.")
            return
        if self._engine.is_running: return
        if not self._macro.actions:
            messagebox.showwarning("No actions", "Add at least one action to run.")
            return
        self._engine.start(self._macro)

    def _stop(self):
        if self._recorder.is_recording: 
            self._toggle_record()
            return
        self._engine.stop()

    def _toggle_record(self):
        if self._engine.is_running:
            messagebox.showwarning("Running", "Stop the macro before recording.")
            return

        if self._recorder.is_recording:
            actions = self._recorder.stop()
            self._sidebar.set_recording(False)
            if actions:
                self._macro.actions = actions
                self._timeline.set_actions(actions)
                messagebox.showinfo("Recording Finished", f"✅  {len(actions)} actions recorded!")
        else:
            self._recorder.start()
            self._sidebar.set_recording(True)
            messagebox.showinfo("Recording Started", "⏺  Recording in progress! Press F7 to stop.")

    def _add_action(self):
        from ui.action_editor import ActionEditorDialog
        dlg = ActionEditorDialog(self._root)
        self._root.wait_window(dlg)
        if dlg.result: 
            self._timeline.add_action(dlg.result)

    def _clear_all(self):
        if not self._macro.actions: return
        if messagebox.askyesno("Confirm", "Clear all actions?"):
            self._macro.actions = []
            self._timeline.set_actions([])

    def _timeline_changed(self):
        self._macro.actions = self._timeline.get_actions()

    def _macro_changed(self): 
        pass

    def _reconfigure_hotkeys(self):
        self._hotkeys.configure(
            start_key=self._macro.hotkey_start, 
            stop_key=self._macro.hotkey_stop, 
            record_key=self._macro.hotkey_record, 
            on_start=self._run, 
            on_stop=self._stop, 
            on_record=self._toggle_record
        )

    def _import_macro(self, macro: Macro):
        self._macro = macro
        self._sidebar.load_macro(macro)
        self._timeline.set_actions(macro.actions)
        self._reconfigure_hotkeys()
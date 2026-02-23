"""
Sidebar panel — macro settings, hotkeys, humanization, anti-AFK, run controls, share.
Scrollable to adapt to all screen heights.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Callable, Optional, Dict
import pyperclip
import os

from models.macro import Macro
from ui.theme import *
from ui.widgets import FlatButton, StyledEntry, SectionLabel, Divider, Tooltip

from utils.storage import save_macro, load_macro, MACROS_DIR, ensure_dir

class SidebarPanel(tk.Frame):

    def __init__(self, parent, callbacks: Dict[str, Callable], **kw):
        super().__init__(parent, bg=BG_PANEL, width=SIDEBAR_W, **kw)
        self.pack_propagate(False)
        self._cb = callbacks
        self._macro: Optional[Macro] = None
        self._build()

    def _build(self):
        # ── Fixed logo (always visible at top) ──
        self._logo_frame = tk.Frame(self, bg=BG_DARKEST)
        self._logo_frame.pack(fill="x", side="top")
        self._logo()

        # ── Fixed controls (always visible at bottom) ──
        self._bottom_frame = tk.Frame(self, bg=BG_PANEL)
        self._bottom_frame.pack(fill="x", side="bottom")
        self._controls_section()
        self._footer()

        # ── Scrollable middle (all settings) ──
        self._scroll_canvas = tk.Canvas(self, bg=BG_PANEL, highlightthickness=0, bd=0)
        self._scrollbar = tk.Scrollbar(self, orient="vertical", command=self._scroll_canvas.yview)
        self._scroll_canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side="right", fill="y")
        self._scroll_canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._scroll_canvas, bg=BG_PANEL)
        self._canvas_window = self._scroll_canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._scroll_canvas.bind("<Configure>", self._on_canvas_configure)

        # Build scrollable sections
        self._macro_info()
        self._hotkeys_section()
        self._loop_section()
        self._humanize_section()
        self._anti_afk_section()
        self._share_section()
        
        # Correction du scroll : Liaison récursive
        self._bind_scroll(self._inner)

    def _on_inner_configure(self, _=None):
        self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._scroll_canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._scroll_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_scroll(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self._bind_scroll(child)

    def _logo(self):
        f = self._logo_frame
        tk.Label(f, text="⚡ GENERICMACRO", bg=BG_DARKEST, fg=ACCENT, font=(FONT_FAMILY, 15, "bold"), padx=PAD, pady=12).pack(side="left")
        tk.Label(f, text="v1.0", bg=ACCENT_DIM, fg=ACCENT, font=FONT_BADGE, padx=6, pady=3).pack(side="right", padx=PAD)

    def _macro_info(self):
        f = tk.Frame(self._inner, bg=BG_PANEL, padx=PAD, pady=8)
        f.pack(fill="x")
        SectionLabel(f, "Macro Name").pack(fill="x")
        self._name_entry = StyledEntry(f, placeholder="My Epic Macro")
        self._name_entry.pack(fill="x", ipady=6, pady=(3, 0))
        self._name_entry.bind("<KeyRelease>", self._name_changed)

        SectionLabel(f, "Target Game").pack(fill="x", pady=(8, 0))
        self._game_var = tk.StringVar(value="Generic")
        games = ["Generic", "Roblox", "Minecraft", "Fortnite", "Other"]
        om = tk.OptionMenu(f, self._game_var, *games, command=self._game_changed)
        om.config(bg=BG_INPUT, fg=TEXT_PRIMARY, activebackground=ACCENT_DIM, highlightthickness=1, highlightbackground=BORDER, relief="flat", font=FONT_BODY)
        om.pack(fill="x", pady=3)

    def _hotkeys_section(self):
        Divider(self._inner).pack(fill="x", padx=PAD)
        f = tk.Frame(self._inner, bg=BG_PANEL, padx=PAD, pady=8)
        f.pack(fill="x")
        SectionLabel(f, "Global Hotkeys").pack(fill="x")
        rows = [("▶ Start:", "_hk_start", "f8"), ("■ Stop:", "_hk_stop", "f9"), ("⏺ Record:", "_hk_rec", "f7")]
        for lbl_txt, attr, _default in rows:
            row = tk.Frame(f, bg=BG_PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=lbl_txt, bg=BG_PANEL, fg=TEXT_SECONDARY, font=FONT_SMALL, width=10, anchor="w").pack(side="left")
            e = StyledEntry(row)
            e.pack(side="left", fill="x", expand=True, ipady=4)
            e.bind("<KeyRelease>", self._hk_changed)
            setattr(self, attr, e)

    def _loop_section(self):
        Divider(self._inner).pack(fill="x", padx=PAD)
        f = tk.Frame(self._inner, bg=BG_PANEL, padx=PAD, pady=8)
        f.pack(fill="x")
        SectionLabel(f, "Loop").pack(fill="x")
        self._loop_var = tk.BooleanVar(value=False)
        tk.Checkbutton(f, text="Repeat Sequence", variable=self._loop_var, bg=BG_PANEL, fg=TEXT_PRIMARY, selectcolor=BG_INPUT, activebackground=BG_PANEL, font=FONT_BODY, command=self._loop_changed).pack(anchor="w", pady=4)
        row = tk.Frame(f, bg=BG_PANEL)
        row.pack(fill="x")
        tk.Label(row, text="Repetitions (0=∞):", bg=BG_PANEL, fg=TEXT_SECONDARY, font=FONT_SMALL).pack(side="left")
        self._loop_count = tk.IntVar(value=0)
        tk.Spinbox(row, from_=0, to=99999, textvariable=self._loop_count, bg=BG_INPUT, fg=TEXT_PRIMARY, relief="flat", font=FONT_BODY, highlightthickness=1, highlightbackground=BORDER, width=7, command=self._loop_changed).pack(side="right", ipady=3)

    def _humanize_section(self):
        Divider(self._inner).pack(fill="x", padx=PAD)
        f = tk.Frame(self._inner, bg=BG_PANEL, padx=PAD, pady=8)
        f.pack(fill="x")
        SectionLabel(f, "🛡 Humanization (Anti-Detection)").pack(fill="x")
        self._humanize_var = tk.DoubleVar(value=0.0)
        self._humanize_label = tk.Label(f, text="0% — Disabled", bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_SMALL)
        self._humanize_label.pack(fill="x", pady=(4, 2))
        slider = tk.Scale(f, variable=self._humanize_var, from_=0.0, to=1.0, resolution=0.05, orient="horizontal", showvalue=False, bg=BG_PANEL, fg=TEXT_PRIMARY, troughcolor=BG_INPUT, highlightthickness=0, activebackground=ACCENT, command=self._humanize_changed)
        slider.pack(fill="x")
        Tooltip(slider, "Adds random delays and micro mouse wobbles.\nMakes the macro undetectable.")

    def _anti_afk_section(self):
        Divider(self._inner).pack(fill="x", padx=PAD)
        f = tk.Frame(self._inner, bg=BG_PANEL, padx=PAD, pady=8)
        f.pack(fill="x")
        SectionLabel(f, "🛡 Anti-AFK").pack(fill="x")
        self._afk_var = tk.BooleanVar(value=False)
        tk.Checkbutton(f, text="Enable Anti-AFK", variable=self._afk_var, bg=BG_PANEL, fg=TEXT_PRIMARY, selectcolor=BG_INPUT, activebackground=BG_PANEL, font=FONT_BODY, command=self._afk_changed).pack(anchor="w", pady=4)
        row = tk.Frame(f, bg=BG_PANEL)
        row.pack(fill="x")
        tk.Label(row, text="Interval (s):", bg=BG_PANEL, fg=TEXT_SECONDARY, font=FONT_SMALL).pack(side="left")
        self._afk_interval = tk.IntVar(value=900)
        tk.Spinbox(row, from_=60, to=3600, textvariable=self._afk_interval, bg=BG_INPUT, fg=TEXT_PRIMARY, relief="flat", font=FONT_BODY, highlightthickness=1, highlightbackground=BORDER, width=7, command=self._afk_changed).pack(side="right", ipady=3)

    def _share_section(self):
        Divider(self._inner).pack(fill="x", padx=PAD)
        f = tk.Frame(self._inner, bg=BG_PANEL, padx=PAD, pady=8)
        f.pack(fill="x")
        SectionLabel(f, "File & Share").pack(fill="x", pady=(0, 4))
        row1 = tk.Frame(f, bg=BG_PANEL)
        row1.pack(fill="x", pady=2)
        FlatButton(row1, "⬆ Export", command=self._export, bg=BG_CARD, hover_bg=BORDER_BRIGHT, font=FONT_SMALL, padx=10, pady=5).pack(side="left", fill="x", expand=True, padx=(0, 3))
        FlatButton(row1, "⬇ Import", command=self._import, bg=BG_CARD, hover_bg=BORDER_BRIGHT, font=FONT_SMALL, padx=10, pady=5).pack(side="left", fill="x", expand=True)
        row2 = tk.Frame(f, bg=BG_PANEL)
        row2.pack(fill="x", pady=2)
        FlatButton(row2, "💾 Save", command=self._save, bg=ACCENT_DIM, hover_bg=ACCENT, font=FONT_SMALL, padx=10, pady=5).pack(side="left", fill="x", expand=True, padx=(0, 3))
        FlatButton(row2, "📂 Load", command=self._load, bg=ACCENT_DIM, hover_bg=ACCENT, font=FONT_SMALL, padx=10, pady=5).pack(side="left", fill="x", expand=True)
        tk.Frame(self._inner, bg=BG_PANEL, height=16).pack()

    def _controls_section(self):
        Divider(self._bottom_frame).pack(fill="x", padx=PAD)
        f = tk.Frame(self._bottom_frame, bg=BG_PANEL, padx=PAD, pady=10)
        f.pack(fill="x")
        SectionLabel(f, "Controls").pack(fill="x", pady=(0, 6))
        self._run_btn = FlatButton(f, "▶ START (F8)", command=self._cb.get("on_run"), bg=GREEN, hover_bg=GREEN_HOVER, font=FONT_H3)
        self._run_btn.pack(fill="x", pady=2)
        self._rec_btn = FlatButton(f, "⏺ RECORD (F7)", command=self._cb.get("on_record"), bg=REC_RED, hover_bg=REC_RED_GLOW, font=FONT_H3)
        self._rec_btn.pack(fill="x", pady=2)
        self._stop_btn = FlatButton(f, "■ STOP (F9)", command=self._cb.get("on_stop"), bg=BG_CARD, hover_bg=RED, font=FONT_H3)
        self._stop_btn.pack(fill="x", pady=2)

        status_row = tk.Frame(f, bg=BG_PANEL, pady=4)
        status_row.pack(fill="x")
        self._dot = tk.Label(status_row, text="●", bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_BODY)
        self._dot.pack(side="left")
        self._status_lbl = tk.Label(status_row, text="Idle", bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_SMALL)
        self._status_lbl.pack(side="left", padx=4)
        self._loop_lbl = tk.Label(status_row, text="", bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_SMALL)
        self._loop_lbl.pack(side="right")

    def _footer(self):
        f = tk.Frame(self._bottom_frame, bg=BG_DARKEST, pady=7)
        f.pack(fill="x")
        tk.Label(f, text="⚡ GenericMacro v1.0", bg=BG_DARKEST, fg=TEXT_MUTED, font=(FONT_FAMILY, 8)).pack()

    def load_macro(self, macro: Macro):
        self._macro = macro
        self._name_entry.set_value(macro.name)
        self._game_var.set(macro.game or "Generic")
        self._hk_start.set_value(macro.hotkey_start)
        self._hk_stop.set_value(macro.hotkey_stop)
        self._hk_rec.set_value(macro.hotkey_record)
        self._loop_var.set(macro.loop)
        self._loop_count.set(macro.loop_count)
        self._humanize_var.set(macro.humanize_level)
        self._humanize_changed(macro.humanize_level)
        self._afk_var.set(macro.anti_afk)
        self._afk_interval.set(macro.anti_afk_interval_s)

    def set_status(self, text: str, color: str = TEXT_MUTED, loop: str = ""):
        self._dot.config(fg=color)
        self._status_lbl.config(text=text, fg=color)
        self._loop_lbl.config(text=loop)

    def set_running(self, running: bool):
        if running: self._run_btn.set_colors(GREEN_DIM, GREEN_DIM)
        else: self._run_btn.set_colors(GREEN, GREEN_HOVER)

    def set_recording(self, recording: bool):
        if recording:
            self._rec_btn.set_colors(REC_RED_GLOW, REC_RED_GLOW)
            self._rec_btn.set_text("⏹ STOP REC. (F7)")
        else:
            self._rec_btn.set_colors(REC_RED, REC_RED_GLOW)
            self._rec_btn.set_text("⏺ RECORD (F7)")

    def _name_changed(self, _=None):
        if self._macro: self._macro.name = self._name_entry.get_value() or "Macro"
            
    def _game_changed(self, _=None):
        if self._macro: self._macro.game = self._game_var.get()
            
    def _hk_changed(self, _=None):
        if self._macro:
            self._macro.hotkey_start  = self._hk_start.get_value() or "f8"
            self._macro.hotkey_stop   = self._hk_stop.get_value() or "f9"
            self._macro.hotkey_record = self._hk_rec.get_value() or "f7"
            if self._cb.get("on_hotkeys_changed"): self._cb["on_hotkeys_changed"]()
                
    def _loop_changed(self):
        if self._macro:
            self._macro.loop = self._loop_var.get()
            try: self._macro.loop_count = self._loop_count.get()
            except: pass
                
    def _humanize_changed(self, val=None):
        v = float(val) if val is not None else self._humanize_var.get()
        pct = int(v * 100)
        label = f"{pct}% — Enabled" if pct > 0 else "0% — Disabled"
        self._humanize_label.config(text=label)
        if self._macro: self._macro.humanize_level = v
            
    def _afk_changed(self):
        if self._macro:
            self._macro.anti_afk = self._afk_var.get()
            try: self._macro.anti_afk_interval_s = self._afk_interval.get()
            except: pass

    def _export(self):
        if not self._macro: return
        code = self._macro.to_share_code()
        pyperclip.copy(code)
        messagebox.showinfo("Exported", "Code copied to clipboard!")

    def _import(self):
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("Import Macro")
        dlg.configure(bg=BG_DARK)
        dlg.geometry("460x190")
        tk.Label(dlg, text="Paste code here:", bg=BG_DARK, fg=TEXT_PRIMARY).pack(pady=10)
        e = StyledEntry(dlg)
        e.pack(fill="x", padx=16)
        def do():
            try:
                macro = Macro.from_share_code(e.get_value().strip())
                dlg.destroy()
                if self._cb.get("on_import"): self._cb["on_import"](macro)
            except Exception as ex: messagebox.showerror("Error", str(ex))
        FlatButton(dlg, "Import", command=do).pack(pady=10)

    def _save(self):
        if not self._macro: return
        save_macro(self._macro) # Utilisation de l'import global
        self._status_lbl.config(text="Saved ✓", fg=GREEN)
        self.after(2000, lambda: self._status_lbl.config(text="Idle", fg=TEXT_MUTED))

    def _load(self):
        ensure_dir() # Utilisation de l'import global
        path = filedialog.askopenfilename(initialdir=MACROS_DIR, filetypes=[("Macro JSON", "*.json")])
        if path:
            try:
                macro = load_macro(path) # Utilisation de l'import global
                if self._cb.get("on_import"): self._cb["on_import"](macro)
            except Exception as ex: messagebox.showerror("Error", str(ex))
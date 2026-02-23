"""
Reusable styled widgets for BloxMacro UI.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from ui.theme import *


class FlatButton(tk.Label):
    """Modern flat button with hover/active states."""

    def __init__(self, parent, text: str, command=None,
                 bg=ACCENT, fg=TEXT_PRIMARY, hover_bg=ACCENT_HOVER,
                 font=None, padx=16, pady=7, radius=0, **kw):
        super().__init__(parent, text=text, bg=bg, fg=fg,
                         font=font or FONT_H3, cursor="hand2",
                         padx=padx, pady=pady, **kw)
        self._bg = bg
        self._hover = hover_bg
        self._cmd = command
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self.config(bg=hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=bg))

    def _click(self, _=None):
        if self._cmd: self._cmd()

    def set_text(self, t): self.config(text=t)

    def set_colors(self, bg: str, hover: str):
        self._bg = bg
        self._hover = hover
        self.config(bg=bg)
        self.unbind("<Enter>"); self.unbind("<Leave>")
        self.bind("<Enter>", lambda e: self.config(bg=hover))
        self.bind("<Leave>", lambda e: self.config(bg=bg))


class IconBtn(tk.Label):
    def __init__(self, parent, text, command=None, color=TEXT_SECONDARY,
                 hover=TEXT_PRIMARY, bg=BG_CARD, font_size=13, **kw):
        super().__init__(parent, text=text, bg=bg, fg=color,
                         font=(FONT_FAMILY, font_size), cursor="hand2", **kw)
        self._cmd = command
        self.bind("<Button-1>", lambda e: command() if command else None)
        self.bind("<Enter>", lambda e: self.config(fg=hover))
        self.bind("<Leave>", lambda e: self.config(fg=color))


class StyledEntry(tk.Entry):
    def __init__(self, parent, placeholder="", **kw):
        super().__init__(parent, bg=BG_INPUT, fg=TEXT_PRIMARY,
                         insertbackground=TEXT_PRIMARY, relief="flat",
                         font=FONT_BODY, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT, **kw)
        self._ph = placeholder
        self._ph_on = False
        if placeholder:
            self._show_ph()
            self.bind("<FocusIn>", self._focus_in)
            self.bind("<FocusOut>", self._focus_out)

    def _show_ph(self):
        self.insert(0, self._ph)
        self.config(fg=TEXT_MUTED)
        self._ph_on = True

    def _focus_in(self, _=None):
        if self._ph_on:
            self.delete(0, "end")
            self.config(fg=TEXT_PRIMARY)
            self._ph_on = False

    def _focus_out(self, _=None):
        if not self.get():
            self._show_ph()

    def get_value(self) -> str:
        return "" if self._ph_on else self.get()

    def set_value(self, v: str):
        self._ph_on = False
        self.delete(0, "end")
        self.config(fg=TEXT_PRIMARY)
        self.insert(0, v)


class StyledSpinbox(tk.Spinbox):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_INPUT, fg=TEXT_PRIMARY,
                         insertbackground=TEXT_PRIMARY, relief="flat",
                         font=FONT_BODY, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=ACCENT,
                         buttonbackground=BG_CARD, **kw)


class SectionLabel(tk.Label):
    def __init__(self, parent, text, **kw):
        super().__init__(parent, text=text.upper(), bg=BG_PANEL,
                         fg=TEXT_MUTED, font=(FONT_FAMILY, 8, "bold"), pady=4, **kw)


class Divider(tk.Frame):
    def __init__(self, parent, color=BORDER, **kw):
        super().__init__(parent, height=1, bg=color, **kw)


class ScrollableFrame(tk.Frame):
    """Vertically scrollable container."""

    def __init__(self, parent, bg=BG_PANEL, **kw):
        super().__init__(parent, bg=bg, **kw)
        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self._sb = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._sb.set)
        self._sb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self._canvas, bg=bg)
        self._win = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_cfg)
        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<MouseWheel>", self._scroll)
        self.inner.bind("<MouseWheel>", self._scroll)

    def _on_cfg(self, _=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_resize(self, e):
        self._canvas.itemconfig(self._win, width=e.width)

    def _scroll(self, e):
        self._canvas.yview_scroll(-1 * (e.delta // 120), "units")

    def scroll_to_bottom(self):
        self._canvas.update_idletasks()
        self._canvas.yview_moveto(1.0)

    def bind_scroll(self, widget):
        widget.bind("<MouseWheel>", self._scroll)


class Tooltip:
    """Simple hover tooltip."""

    def __init__(self, widget, text: str):
        self._widget = widget
        self._text = text
        self._tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        x = self._widget.winfo_rootx() + 20
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._tip = tk.Toplevel(self._widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self._tip, text=self._text, bg="#1A1D27", fg=TEXT_PRIMARY,
                       font=FONT_SMALL, relief="flat", padx=8, pady=4,
                       wraplength=260, justify="left",
                       highlightthickness=1, highlightbackground=BORDER_BRIGHT)
        lbl.pack()

    def _hide(self, _=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None

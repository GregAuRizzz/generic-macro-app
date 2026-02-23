"""
Timeline: scrollable list of action cards with drag-and-drop reordering.
"""
from __future__ import annotations
import tkinter as tk
from typing import List, Callable, Optional

from models.macro import Action, ActionType
from ui.theme import *
from ui.widgets import ScrollableFrame, IconBtn

class ActionCard(tk.Frame):
    HEIGHT = 52

    def __init__(self, parent, action: Action, index: int, on_edit, on_delete, on_drag_start, on_drag_motion, on_drag_end, active=False):
        super().__init__(parent, bg=BG_CARD, highlightthickness=1, highlightbackground=BORDER)
        self.action = action
        self.index = index
        self._active = active
        self._build(on_edit, on_delete, on_drag_start, on_drag_motion, on_drag_end)
        
        if active: 
            self._set_active(True)

    def _build(self, on_edit, on_delete, on_drag_start, on_drag_motion, on_drag_end):
        color = self.action.accent_color()
        tk.Frame(self, bg=color, width=4).pack(side="left", fill="y")
        
        handle = tk.Label(self, text="⠿", bg=BG_CARD, fg=TEXT_MUTED, font=(FONT_FAMILY, 15), cursor="fleur", padx=3)
        handle.pack(side="left")
        
        handle.bind("<ButtonPress-1>", on_drag_start)
        handle.bind("<B1-Motion>", on_drag_motion)
        handle.bind("<ButtonRelease-1>", on_drag_end)
        
        tk.Label(self, text=f"{self.index+1:02d}", bg=BG_CARD, fg=TEXT_MUTED, font=FONT_MONO_S, padx=4).pack(side="left")
        
        lbl = tk.Label(self, text=self.action.label(), bg=BG_CARD, fg=TEXT_PRIMARY, font=FONT_BODY, anchor="w")
        lbl.pack(side="left", fill="x", expand=True, pady=10)
        
        tk.Label(self, text=f"+{self.action.delay_after_ms}ms", bg=BG_CARD, fg=TEXT_MUTED, font=FONT_TINY, padx=6).pack(side="left")
        
        bf = tk.Frame(self, bg=BG_CARD, padx=4)
        bf.pack(side="right")
        
        IconBtn(bf, "✏", command=on_edit, bg=BG_CARD).pack(side="left", padx=1)
        IconBtn(bf, "✕", command=on_delete, bg=BG_CARD, color=RED, hover=RED_HOVER).pack(side="left", padx=1)
        
        for w in (self, lbl): 
            w.bind("<Enter>", self._hover_on)
            w.bind("<Leave>", self._hover_off)

    def _hover_on(self, _=None):
        if not self._active: 
            self.config(bg=BG_CARD_HOVER, highlightbackground=BORDER_BRIGHT)
            
    def _hover_off(self, _=None):
        if not self._active: 
            self.config(bg=BG_CARD, highlightbackground=BORDER)
            
    def _set_active(self, v: bool):
        self._active = v
        if v: 
            self.config(bg=ACCENT_DIM, highlightbackground=ACCENT)
        else: 
            self.config(bg=BG_CARD, highlightbackground=BORDER)


class TimelinePanel(tk.Frame):
    def __init__(self, parent, on_changed: Callable, **kw):
        super().__init__(parent, bg=BG_PANEL, **kw)
        self._on_changed = on_changed
        self._actions: List[Action] = []
        self._cards: List[ActionCard] = []
        self._active_index: Optional[int] = None
        self._drag_index: int = 0
        self._drag_start_y: int = 0
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG_PANEL, padx=PAD, pady=6)
        hdr.pack(fill="x")
        
        tk.Label(hdr, text="ACTION SEQUENCE", bg=BG_PANEL, fg=TEXT_MUTED, font=(FONT_FAMILY, 8, "bold")).pack(side="left")
        self._count_lbl = tk.Label(hdr, text="0 action", bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_TINY)
        self._count_lbl.pack(side="right")
        
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        self._scroll = ScrollableFrame(self, bg=BG_PANEL)
        self._scroll.pack(fill="both", expand=True)

        self._empty = tk.Frame(self._scroll.inner, bg=BG_PANEL)
        self._empty.pack(fill="both", expand=True, pady=80)
        
        tk.Label(self._empty, text="🎮", bg=BG_PANEL, fg=TEXT_MUTED, font=(FONT_FAMILY, 40)).pack()
        tk.Label(self._empty, text="No actions in the sequence", bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_H3).pack(pady=(8,4))
        tk.Label(self._empty, text="Click ＋ Add Action or use the ⏺ RECORD button", bg=BG_PANEL, fg=TEXT_MUTED, font=FONT_SMALL, wraplength=380).pack()

    def set_actions(self, actions: List[Action]):
        self._actions = list(actions)
        self._refresh()
        
    def get_actions(self) -> List[Action]: 
        return list(self._actions)
        
    def add_action(self, action: Action):
        self._actions.append(action)
        self._refresh()
        self._scroll.scroll_to_bottom()
        self._on_changed()

    def highlight_action(self, index: Optional[int]):
        self._active_index = index
        for i, card in enumerate(self._cards): 
            card._set_active(i == index)

    def _refresh(self):
        for card in self._cards: 
            card.destroy()
        self._cards.clear()
        
        if self._actions: 
            self._empty.pack_forget()
        else: 
            self._empty.pack(fill="both", expand=True, pady=80)

        for i, action in enumerate(self._actions):
            card = ActionCard(
                self._scroll.inner, 
                action=action, 
                index=i,
                on_edit=lambda a=action: self._edit(a), 
                on_delete=lambda a=action: self._delete(a),
                on_drag_start=lambda e, idx=i: self._ds(e, idx), 
                on_drag_motion=self._dm, 
                on_drag_end=self._de, 
                active=(i == self._active_index)
            )
            card.pack(fill="x", padx=PAD, pady=2)
            self._cards.append(card)

        n = len(self._actions)
        self._count_lbl.config(text=f"{n} action{'s' if n!=1 else ''}")

    def _edit(self, action: Action):
        from ui.action_editor import ActionEditorDialog
        root = self.winfo_toplevel()
        dlg = ActionEditorDialog(root, action)
        root.wait_window(dlg)
        if dlg.result:
            idx = next((i for i,a in enumerate(self._actions) if a.id==action.id), None)
            if idx is not None: 
                self._actions[idx] = dlg.result
                self._refresh()
                self._on_changed()

    def _delete(self, action: Action):
        self._actions = [a for a in self._actions if a.id != action.id]
        self._refresh()
        self._on_changed()

    def _ds(self, event, index): 
        self._drag_index = index
        self._drag_start_y = event.y_root
        
    def _dm(self, event):
        delta = event.y_root - self._drag_start_y
        step = ActionCard.HEIGHT + 4
        steps = int(delta // step)
        
        new_idx = max(0, min(len(self._actions) - 1, self._drag_index + steps))
        
        if new_idx != self._drag_index:
            self._actions.insert(new_idx, self._actions.pop(self._drag_index))
            self._drag_index = new_idx
            self._drag_start_y = event.y_root
            self._refresh()
            
    def _de(self, event): 
        self._on_changed()
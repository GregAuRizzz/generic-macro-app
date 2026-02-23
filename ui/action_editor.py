"""
Modal dialog for creating or editing an Action.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, filedialog
from typing import Optional
import base64
import os

from models.macro import Action, ActionType
from ui.theme import *
from ui.widgets import FlatButton, StyledEntry, StyledSpinbox

ACTION_DEFS = [
    (ActionType.MOUSE_CLICK,  "🖱  Mouse Click",         "#4FC3F7"),
    (ActionType.MOUSE_MOVE,   "➡  Mouse Move",          "#4DD0E1"),
    (ActionType.MOUSE_SCROLL, "⟳  Mouse Scroll",        "#80DEEA"),
    (ActionType.KEY_PRESS,    "⌨  Key Press",           "#81C784"),
    (ActionType.KEY_HOLD,     "⌨  Key Hold",            "#A5D6A7"),
    (ActionType.WAIT,         "⏳  Wait",                 "#FFD54F"),
    (ActionType.TYPE_TEXT,    "💬  Type Text",            "#CE93D8"),
    (ActionType.IMAGE_WAIT,   "👁  Wait for Image (CV)", "#FF8A65"),
    (ActionType.IMAGE_CLICK,  "👁  Click Image (CV)",    "#FFAB40"),
]

class ActionEditorDialog(tk.Toplevel):
    def __init__(self, parent, action: Optional[Action] = None):
        super().__init__(parent)
        self.result: Optional[Action] = None
        self._action = action
        self._template_b64: Optional[str] = None
        
        self.title("Edit Action" if action else "New Action")
        self.configure(bg=BG_DARK)
        self.resizable(False, True)
        self.grab_set()
        
        w, h = 540, 720
        px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{px}+{py}")
        
        self._build()
        if action: 
            self._populate(action)

    def _build(self):
        hdr = tk.Frame(self, bg=BG_DARKEST, padx=PAD, pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ACTION TYPE", bg=BG_DARKEST, fg=TEXT_MUTED, font=(FONT_FAMILY, 8, "bold")).pack(anchor="w")
        tk.Label(hdr, text="Select the type and configure the parameters below.", bg=BG_DARKEST, fg=TEXT_SECONDARY, font=FONT_SMALL).pack(anchor="w")

        self._type_var = tk.StringVar(value=ACTION_DEFS[0][0])
        grid_frame = tk.Frame(self, bg=BG_DARK, padx=PAD, pady=6)
        grid_frame.pack(fill="x")
        self._type_btns: dict[str, tk.Label] = {}
        
        for i, (atype, label, color) in enumerate(ACTION_DEFS):
            r, c = divmod(i, 3)
            btn = tk.Label(grid_frame, text=label, bg=BG_CARD, fg=TEXT_SECONDARY, font=(FONT_FAMILY, 9), padx=8, pady=6, cursor="hand2", anchor="w", highlightthickness=1, highlightbackground=BORDER)
            btn.grid(row=r, column=c, padx=2, pady=2, sticky="ew")
            grid_frame.grid_columnconfigure(c, weight=1)
            btn.bind("<Button-1>", lambda e, t=atype: self._select(t))
            self._type_btns[atype] = btn

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=PAD)
        self._params = tk.Frame(self, bg=BG_DARK, padx=PAD)
        self._params.pack(fill="both", expand=True, pady=4)

        footer = tk.Frame(self, bg=BG_DARKEST, padx=PAD, pady=10)
        footer.pack(fill="x", side="bottom")
        FlatButton(footer, "✕  Cancel", command=self.destroy, bg=BG_CARD, hover_bg=BORDER_BRIGHT).pack(side="left")
        FlatButton(footer, "✓  Confirm", command=self._confirm, bg=ACCENT, hover_bg=ACCENT_HOVER).pack(side="right")
        self._select(ACTION_DEFS[0][0])

    def _select(self, atype: str):
        self._type_var.set(atype)
        for t, btn in self._type_btns.items():
            if t == atype: 
                btn.config(bg=ACCENT_DIM, fg=TEXT_PRIMARY, highlightbackground=ACCENT)
            else: 
                btn.config(bg=BG_CARD, fg=TEXT_SECONDARY, highlightbackground=BORDER)
        self._build_params(atype)

    def _build_params(self, atype: str):
        for w in self._params.winfo_children(): 
            w.destroy()
        self._pw: dict = {}
        
        def lbl(text): 
            tk.Label(self._params, text=text, bg=BG_DARK, fg=TEXT_SECONDARY, font=FONT_SMALL, anchor="w").pack(fill="x", pady=(8, 1))
            
        def entry(key, ph=""): 
            e = StyledEntry(self._params, placeholder=ph)
            e.pack(fill="x", ipady=5)
            self._pw[key] = e
            return e
            
        def spin(key, from_=0, to=999999, default=0): 
            v = tk.IntVar(value=default)
            s = StyledSpinbox(self._params, from_=from_, to=to, textvariable=v, width=14)
            s.pack(fill="x", ipady=4)
            self._pw[key] = v
            return v
            
        def radio(key, opts):
            v = tk.StringVar(value=opts[0][0])
            f = tk.Frame(self._params, bg=BG_DARK)
            f.pack(fill="x", pady=4)
            for val, txt in opts: 
                tk.Radiobutton(f, text=txt, variable=v, value=val, bg=BG_DARK, fg=TEXT_PRIMARY, selectcolor=BG_INPUT, activebackground=BG_DARK, font=FONT_BODY).pack(side="left", padx=6)
            self._pw[key] = v
            return v

        if atype == ActionType.MOUSE_CLICK:
            lbl("Button:")
            radio("button", [("left","Left"),("right","Right"),("middle","Middle")])
            lbl("Clicks:")
            spin("clicks", 1, 20, 1)
            lbl("Position X (empty = current cursor):")
            entry("x", "ex: 960")
            lbl("Position Y:")
            entry("y", "ex: 540")
            lbl("Delay after (ms):")
            spin("delay_after_ms", 0, 60000, 100)
            
        elif atype == ActionType.MOUSE_MOVE:
            lbl("Position X:")
            entry("x", "ex: 960")
            lbl("Position Y:")
            entry("y", "ex: 540")
            lbl("Delay after (ms):")
            spin("delay_after_ms", 0, 60000, 100)
            
        elif atype == ActionType.MOUSE_SCROLL:
            lbl("Direction:")
            radio("scroll_dir", [("up","↑ Up"),("down","↓ Down")])
            lbl("Amount:")
            spin("scroll_amount", 1, 50, 3)
            lbl("Delay after (ms):")
            spin("delay_after_ms", 0, 60000, 100)
            
        elif atype == ActionType.KEY_PRESS:
            lbl("Key (e.g., w, space, enter, f1, shift):")
            entry("key", "ex: w")
            lbl("Delay after (ms):")
            spin("delay_after_ms", 0, 60000, 100)
            
        elif atype == ActionType.KEY_HOLD:
            lbl("Key to hold:")
            entry("key", "ex: shift")
            lbl("Duration (ms):")
            spin("duration_ms", 1, 60000, 500)
            lbl("Delay after (ms):")
            spin("delay_after_ms", 0, 60000, 100)
            
        elif atype == ActionType.WAIT:
            lbl("Wait Duration (ms):")
            spin("duration_ms", 1, 300000, 1000)
            
        elif atype == ActionType.TYPE_TEXT:
            lbl("Text to type:")
            t = tk.Text(self._params, bg=BG_INPUT, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY, relief="flat", font=FONT_BODY, height=4, highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
            t.pack(fill="x", pady=4)
            self._pw["text"] = t
            lbl("Delay after (ms):")
            spin("delay_after_ms", 0, 60000, 100)
            
        elif atype in (ActionType.IMAGE_WAIT, ActionType.IMAGE_CLICK):
            self._build_cv_params(atype)

        if atype in (ActionType.MOUSE_CLICK, ActionType.MOUSE_MOVE):
            tk.Label(self._params, text="💡 Tip: Leave empty to use the current mouse position.", bg=BG_DARK, fg=TEXT_MUTED, font=FONT_SMALL, wraplength=480, justify="left").pack(anchor="w", pady=(6,0))

    def _build_cv_params(self, atype: str):
        tk.Label(self._params, text="👁  Computer Vision\nThe macro continuously scans the screen until the image is found.", bg=BG_DARK, fg=ORANGE, font=FONT_SMALL, justify="left", wraplength=490).pack(anchor="w", pady=6)
        
        self._cv_preview_label = tk.Label(self._params, text="📷  No image captured", bg=BG_INPUT, fg=TEXT_MUTED, font=FONT_SMALL, height=4, relief="flat", highlightthickness=1, highlightbackground=BORDER)
        self._cv_preview_label.pack(fill="x", pady=4)
        
        btn_row = tk.Frame(self._params, bg=BG_DARK)
        btn_row.pack(fill="x", pady=2)
        
        FlatButton(btn_row, "📷  Capture Screen Region", command=self._capture_screen_region, bg=ACCENT_DIM, hover_bg=ACCENT, font=FONT_SMALL, padx=10, pady=5).pack(side="left", padx=(0, 6))
        FlatButton(btn_row, "📁  Load Image (PNG)", command=self._load_image_file, bg=BG_CARD, hover_bg=BORDER_BRIGHT, font=FONT_SMALL, padx=10, pady=5).pack(side="left")
        
        tk.Label(self._params, text="Confidence (0.7 = loose, 0.95 = strict):", bg=BG_DARK, fg=TEXT_SECONDARY, font=FONT_SMALL, anchor="w").pack(fill="x", pady=(10,1))
        cv_conf = tk.DoubleVar(value=0.85)
        tk.Scale(self._params, variable=cv_conf, from_=0.5, to=1.0, resolution=0.01, orient="horizontal", bg=BG_DARK, fg=TEXT_PRIMARY, troughcolor=BG_INPUT, highlightthickness=0, activebackground=ACCENT, showvalue=True).pack(fill="x")
        self._pw["cv_confidence"] = cv_conf
        
        tk.Label(self._params, text="Timeout (ms):", bg=BG_DARK, fg=TEXT_SECONDARY, font=FONT_SMALL, anchor="w").pack(fill="x", pady=(8,1))
        cv_timeout = tk.IntVar(value=30000)
        StyledSpinbox(self._params, from_=1000, to=300000, textvariable=cv_timeout).pack(fill="x", ipady=4)
        self._pw["cv_timeout_ms"] = cv_timeout
        
        tk.Label(self._params, text="Delay after (ms):", bg=BG_DARK, fg=TEXT_SECONDARY, font=FONT_SMALL, anchor="w").pack(fill="x", pady=(8,1))
        delay = tk.IntVar(value=200)
        StyledSpinbox(self._params, from_=0, to=60000, textvariable=delay).pack(fill="x", ipady=4)
        self._pw["delay_after_ms"] = delay

    def _capture_screen_region(self):
        try: 
            from PIL import ImageGrab
        except ImportError: 
            messagebox.showerror("Error", "Pillow required: pip install Pillow", parent=self)
            return
            
        overlay = tk.Toplevel(self)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.3)
        overlay.attributes("-topmost", True)
        overlay.config(cursor="crosshair")
        
        canvas = tk.Canvas(overlay, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        rect_id = None
        start_x = 0
        start_y = 0
        
        def on_press(e): 
            nonlocal start_x, start_y, rect_id
            start_x = e.x_root
            start_y = e.y_root
            rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)
            
        def on_drag(e): 
            nonlocal rect_id
            if rect_id: 
                canvas.coords(rect_id, start_x, start_y, e.x_root, e.y_root)
                
        def on_release(e):
            end_x = e.x_root
            end_y = e.y_root
            overlay.destroy()
            
            x0 = min(start_x, end_x)
            x1 = max(start_x, end_x)
            y0 = min(start_y, end_y)
            y1 = max(start_y, end_y)
            
            if x1 - x0 < 5 or y1 - y0 < 5: 
                return
                
            try:
                import io
                screenshot = ImageGrab.grab(bbox=(x0, y0, x1, y1))
                buf = io.BytesIO()
                screenshot.save(buf, format="PNG")
                self._template_b64 = base64.b64encode(buf.getvalue()).decode()
                if hasattr(self, "_cv_preview_label"): 
                    self._cv_preview_label.config(text=f"✅  Region captured: {x1-x0}×{y1-y0} px", fg=GREEN)
            except Exception as ex: 
                messagebox.showerror("Capture Error", str(ex), parent=self)
                
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        overlay.bind("<Escape>", lambda e: overlay.destroy())

    def _load_image_file(self):
        path = filedialog.askopenfilename(filetypes=[("PNG/JPG Images", "*.png *.jpg *.jpeg"), ("All", "*.*")], parent=self)
        if path:
            with open(path, "rb") as f: 
                self._template_b64 = base64.b64encode(f.read()).decode()
            if hasattr(self, "_cv_preview_label"): 
                self._cv_preview_label.config(text=f"✅  {os.path.basename(path)}", fg=GREEN)

    def _populate(self, a: Action):
        self._select(a.type)
        
        def set_(key, val):
            if key not in self._pw or val is None: 
                return
            w = self._pw[key]
            if isinstance(w, StyledEntry): 
                w.set_value(str(val))
            elif isinstance(w, (tk.IntVar, tk.DoubleVar)):
                try: 
                    w.set(val)
                except: 
                    pass
            elif isinstance(w, tk.StringVar): 
                w.set(str(val))
            elif isinstance(w, tk.Text): 
                w.delete("1.0", "end")
                w.insert("1.0", str(val))
                
        set_("button", a.button)
        set_("clicks", a.clicks)
        set_("x", a.x)
        set_("y", a.y)
        set_("key", a.key)
        set_("duration_ms", a.duration_ms)
        set_("delay_after_ms", a.delay_after_ms)
        set_("text", a.text)
        set_("scroll_amount", abs(a.scroll_amount or 3))
        set_("cv_confidence", a.cv_confidence)
        set_("cv_timeout_ms", a.cv_timeout_ms)
        
        if "scroll_dir" in self._pw and a.scroll_amount is not None: 
            self._pw["scroll_dir"].set("up" if a.scroll_amount >= 0 else "down")
            
        if a.template_b64: 
            self._template_b64 = a.template_b64
            self._cv_preview_label.config(text="✅  Image configured", fg=GREEN)

    def _confirm(self):
        atype = self._type_var.get()
        pw = self._pw
        
        def gi(key, default=None):
            if key not in pw: 
                return default
            w = pw[key]
            if isinstance(w, StyledEntry): 
                v = w.get_value()
                return v if v else default
            elif isinstance(w, (tk.IntVar, tk.DoubleVar)): 
                return w.get()
            elif isinstance(w, tk.StringVar): 
                return w.get() or default
            elif isinstance(w, tk.Text): 
                return w.get("1.0","end-1c") or default
            return default
            
        def gint(key, default=0):
            try: 
                return int(gi(key, default))
            except: 
                return default
                
        kwargs = {"type": atype}
        
        if atype == ActionType.MOUSE_CLICK:
            kwargs.update(button=gi("button","left"), clicks=gint("clicks",1), delay_after_ms=gint("delay_after_ms",100))
            try: 
                kwargs["x"] = int(gi("x",""))
                kwargs["y"] = int(gi("y",""))
            except: 
                pass
                
        elif atype == ActionType.MOUSE_MOVE:
            try: 
                kwargs["x"] = int(gi("x",0))
                kwargs["y"] = int(gi("y",0))
            except: 
                pass
            kwargs["delay_after_ms"] = gint("delay_after_ms", 100)
            
        elif atype == ActionType.MOUSE_SCROLL:
            amt = gint("scroll_amount", 3)
            d = gi("scroll_dir", "up")
            kwargs.update(scroll_amount=amt if d=="up" else -amt, delay_after_ms=gint("delay_after_ms",100))
            
        elif atype == ActionType.KEY_PRESS: 
            kwargs.update(key=gi("key",""), delay_after_ms=gint("delay_after_ms",100))
            
        elif atype == ActionType.KEY_HOLD: 
            kwargs.update(key=gi("key",""), duration_ms=gint("duration_ms",500), delay_after_ms=gint("delay_after_ms",100))
            
        elif atype == ActionType.WAIT: 
            kwargs["duration_ms"] = gint("duration_ms", 1000)
            
        elif atype == ActionType.TYPE_TEXT: 
            kwargs.update(text=gi("text",""), delay_after_ms=gint("delay_after_ms",100))
            
        elif atype in (ActionType.IMAGE_WAIT, ActionType.IMAGE_CLICK): 
            kwargs.update(template_b64=self._template_b64, cv_confidence=float(gi("cv_confidence", 0.85)), cv_timeout_ms=gint("cv_timeout_ms", 30000), delay_after_ms=gint("delay_after_ms", 200))

        if self._action: 
            kwargs["id"] = self._action.id
            
        self.result = Action(**kwargs)
        self.destroy()
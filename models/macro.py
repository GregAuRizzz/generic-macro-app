"""
Data models for GenericMacro.
"""
from __future__ import annotations
import uuid
import json
import base64
import zlib
from dataclasses import dataclass, field, asdict
from typing import List, Optional

class ActionType:
    MOUSE_CLICK  = "mouse_click"
    MOUSE_MOVE   = "mouse_move"
    MOUSE_SCROLL = "mouse_scroll"
    KEY_PRESS    = "key_press"
    KEY_HOLD     = "key_hold"
    WAIT         = "wait"
    TYPE_TEXT    = "type_text"
    IMAGE_WAIT   = "image_wait"   
    IMAGE_CLICK  = "image_click"  

    ALL = [
        MOUSE_CLICK, MOUSE_MOVE, MOUSE_SCROLL,
        KEY_PRESS, KEY_HOLD,
        WAIT, TYPE_TEXT,
        IMAGE_WAIT, IMAGE_CLICK,
    ]

@dataclass
class Action:
    type: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    button: str = "left"
    x: Optional[int] = None
    y: Optional[int] = None
    clicks: int = 1
    scroll_amount: int = 3
    key: Optional[str] = None
    duration_ms: int = 0
    text: Optional[str] = None
    template_path: Optional[str] = None
    template_b64: Optional[str] = None
    cv_confidence: float = 0.85
    cv_timeout_ms: int = 30000
    delay_after_ms: int = 100
    humanize: Optional[bool] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> Action:
        valid = {k for k in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in valid})

    def label(self) -> str:
        t = self.type
        if t == ActionType.MOUSE_CLICK:
            btn = (self.button or "left").capitalize()
            pos = f" @({self.x},{self.y})" if self.x is not None else ""
            n = f" ×{self.clicks}" if self.clicks > 1 else ""
            return f"🖱  Click {btn}{pos}{n}"
        elif t == ActionType.MOUSE_MOVE:
            return f"➡  Move to ({self.x}, {self.y})"
        elif t == ActionType.MOUSE_SCROLL:
            d = "↑" if self.scroll_amount >= 0 else "↓"
            return f"🖱  Scroll {d} ×{abs(self.scroll_amount)}"
        elif t == ActionType.KEY_PRESS:
            return f"⌨  Press [{self.key}]"
        elif t == ActionType.KEY_HOLD:
            return f"⌨  Hold [{self.key}] {self.duration_ms}ms"
        elif t == ActionType.WAIT:
            return f"⏳  Wait {self.duration_ms}ms"
        elif t == ActionType.TYPE_TEXT:
            preview = (self.text or "")[:18]
            dots = "…" if len(self.text or "") > 18 else ""
            return f"💬  Type \"{preview}{dots}\""
        elif t == ActionType.IMAGE_WAIT:
            return f"👁  Wait for image (±{int(self.cv_confidence*100)}%)"
        elif t == ActionType.IMAGE_CLICK:
            return f"👁  Click on image (±{int(self.cv_confidence*100)}%)"
        return f"❓  {t}"

    def accent_color(self) -> str:
        from ui.theme import ACTION_COLORS
        return ACTION_COLORS.get(self.type, "#888888")

@dataclass
class Macro:
    name: str = "New Macro"
    description: str = ""
    game: str = "Generic"
    loop: bool = False
    loop_count: int = 0
    hotkey_start: str = "f8"
    hotkey_stop: str = "f9"
    hotkey_record: str = "f7"
    humanize_level: float = 0.0
    anti_afk: bool = False
    anti_afk_interval_s: int = 900
    actions: List[Action] = field(default_factory=list)
    author: str = ""
    downloads: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description, "game": self.game,
            "loop": self.loop, "loop_count": self.loop_count,
            "hotkey_start": self.hotkey_start, "hotkey_stop": self.hotkey_stop, "hotkey_record": self.hotkey_record,
            "humanize_level": self.humanize_level, "anti_afk": self.anti_afk, "anti_afk_interval_s": self.anti_afk_interval_s,
            "author": self.author, "tags": self.tags,
            "actions": [a.to_dict() for a in self.actions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Macro:
        actions = [Action.from_dict(a) for a in data.get("actions", [])]
        valid = {k for k in cls.__dataclass_fields__ if k != "actions"}
        kwargs = {k: v for k, v in data.items() if k in valid}
        return cls(actions=actions, **kwargs)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> Macro:
        return cls.from_dict(json.loads(text))

    def to_share_code(self) -> str:
        raw = json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False).encode()
        compressed = zlib.compress(raw, level=9)
        b64 = base64.urlsafe_b64encode(compressed).decode().rstrip("=")
        return f"GMAC-{b64}"

    @classmethod
    def from_share_code(cls, code: str) -> Macro:
        code = code.strip()
        if code.upper().startswith("GMAC-"): code = code[5:]
        pad = 4 - len(code) % 4
        if pad != 4: code += "=" * pad
        return cls.from_dict(json.loads(zlib.decompress(base64.urlsafe_b64decode(code))))
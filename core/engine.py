"""
Execution engine — runs macro actions via OS-level pynput.
Supports humanization (random delays + micro mouse jitter) and Anti-AFK.
"""
from __future__ import annotations
import time
import math
import random
import threading
import logging
from typing import Optional, Callable

from pynput.mouse import Button, Controller as MouseCtrl
from pynput.keyboard import Key, Controller as KeyCtrl

from models.macro import Macro, Action, ActionType

log = logging.getLogger(__name__)

SPECIAL_KEYS: dict[str, Key] = {
    "enter": Key.enter, "return": Key.enter,
    "space": Key.space, "backspace": Key.backspace,
    "delete": Key.delete, "del": Key.delete,
    "tab": Key.tab, "escape": Key.esc, "esc": Key.esc,
    "shift": Key.shift, "ctrl": Key.ctrl, "control": Key.ctrl,
    "alt": Key.alt, "win": Key.cmd, "cmd": Key.cmd,
    "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
    "home": Key.home, "end": Key.end,
    "page_up": Key.page_up, "page_down": Key.page_down,
    **{f"f{i}": getattr(Key, f"f{i}") for i in range(1, 13)},
    "caps_lock": Key.caps_lock, "insert": Key.insert,
    "num_lock": Key.num_lock, "print_screen": Key.print_screen,
}

MOUSE_BUTTONS = {"left": Button.left, "right": Button.right, "middle": Button.middle}


class ExecutionEngine:
    def __init__(self):
        self._mouse = MouseCtrl()
        self._keyboard = KeyCtrl()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Anti-AFK
        self._afk_thread: Optional[threading.Thread] = None
        self._afk_stop = threading.Event()

        # Callbacks (called on main thread via after())
        self.on_start:   Optional[Callable] = None
        self.on_stop:    Optional[Callable] = None
        self.on_action:  Optional[Callable[[int, Action], None]] = None
        self.on_loop:    Optional[Callable[[int], None]] = None
        self.on_error:   Optional[Callable[[str], None]] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, macro: Macro):
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run, args=(macro,), daemon=True, name="MacroEngine")
        self._thread.start()

        if macro.anti_afk:
            self._start_anti_afk(macro.anti_afk_interval_s)

    def stop(self):
        self._stop_event.set()
        self._running = False
        self._stop_anti_afk()

    # ── Main loop ────────────────────────────────────────────────────
    def _run(self, macro: Macro):
        try:
            if self.on_start:
                self.on_start()

            loop_num = 0
            while not self._stop_event.is_set():
                loop_num += 1
                if self.on_loop:
                    self.on_loop(loop_num)

                for idx, action in enumerate(macro.actions):
                    if self._stop_event.is_set():
                        break
                    if self.on_action:
                        self.on_action(idx, action)
                    self._execute(action, macro.humanize_level)

                if not macro.loop:
                    break
                if macro.loop_count > 0 and loop_num >= macro.loop_count:
                    break

        except Exception as e:
            log.exception("Engine error")
            if self.on_error:
                self.on_error(str(e))
        finally:
            self._running = False
            self._stop_anti_afk()
            if self.on_stop:
                self.on_stop()

    # ── Action dispatch ──────────────────────────────────────────────
    def _execute(self, action: Action, humanize: float = 0.0):
        t = action.type

        if t == ActionType.MOUSE_CLICK:
            self._mouse_click(action, humanize)
        elif t == ActionType.MOUSE_MOVE:
            self._mouse_move(action, humanize)
        elif t == ActionType.MOUSE_SCROLL:
            self._mouse.scroll(0, action.scroll_amount)
        elif t == ActionType.KEY_PRESS:
            k = self._resolve_key(action.key or "")
            if k:
                self._keyboard.press(k)
                self._sleep(50)
                self._keyboard.release(k)
        elif t == ActionType.KEY_HOLD:
            k = self._resolve_key(action.key or "")
            if k:
                self._keyboard.press(k)
                self._sleep(action.duration_ms or 500)
                self._keyboard.release(k)
        elif t == ActionType.WAIT:
            self._sleep(action.duration_ms or 1000)
        elif t == ActionType.TYPE_TEXT:
            if action.text:
                self._keyboard.type(action.text)
        elif t in (ActionType.IMAGE_WAIT, ActionType.IMAGE_CLICK):
            self._execute_cv(action, humanize)

        # Post-action delay with humanization
        delay = action.delay_after_ms
        if humanize > 0 and delay > 0:
            jitter = int(delay * humanize * 0.5 * random.uniform(-1, 1))
            delay = max(10, delay + jitter)
        self._sleep(delay)

    def _mouse_click(self, action: Action, humanize: float):
        btn = MOUSE_BUTTONS.get(action.button or "left", Button.left)
        if action.x is not None and action.y is not None:
            tx, ty = action.x, action.y
            if humanize > 0:
                tx += int(humanize * random.uniform(-3, 3))
                ty += int(humanize * random.uniform(-3, 3))
            self._smooth_move(tx, ty, humanize)
        for _ in range(action.clicks or 1):
            if self._stop_event.is_set():
                return
            self._mouse.press(btn)
            self._sleep(int(40 + humanize * random.uniform(0, 30)))
            self._mouse.release(btn)
            if action.clicks > 1:
                self._sleep(int(60 + humanize * random.uniform(0, 40)))

    def _mouse_move(self, action: Action, humanize: float):
        if action.x is None or action.y is None:
            return
        tx, ty = action.x, action.y
        if humanize > 0:
            tx += int(humanize * random.uniform(-2, 2))
            ty += int(humanize * random.uniform(-2, 2))
        self._smooth_move(tx, ty, humanize)

    def _smooth_move(self, tx: int, ty: int, humanize: float):
        """Move mouse smoothly (with optional curve if humanize > 0)."""
        if humanize < 0.1:
            self._mouse.position = (tx, ty)
            return
        cx, cy = self._mouse.position
        steps = max(8, int(30 * humanize))
        for i in range(1, steps + 1):
            if self._stop_event.is_set():
                return
            t = i / steps
            # Ease in-out curve
            t_ease = t * t * (3 - 2 * t)
            nx = int(cx + (tx - cx) * t_ease)
            ny = int(cy + (ty - cy) * t_ease)
            # Slight bezier wobble
            wobble = math.sin(t * math.pi) * humanize * random.uniform(-2, 2)
            self._mouse.position = (nx + int(wobble), ny + int(wobble))
            time.sleep(0.005)

    def _execute_cv(self, action: Action, humanize: float):
        """Computer Vision: wait for template image on screen, optionally click."""
        try:
            import cv2
            import numpy as np
            from PIL import ImageGrab
        except ImportError:
            log.error("OpenCV/Pillow not installed for CV actions")
            if self.on_error:
                self.on_error("OpenCV requis : pip install opencv-python numpy Pillow")
            return

        # Load template
        template_img = None
        if action.template_b64:
            import base64
            from PIL import Image
            import io
            img_bytes = base64.b64decode(action.template_b64)
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            template_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        elif action.template_path:
            template_img = cv2.imread(action.template_path)

        if template_img is None:
            log.warning("CV action: no template image configured")
            return

        h, w = template_img.shape[:2]
        timeout_s = (action.cv_timeout_ms or 30000) / 1000.0
        confidence = action.cv_confidence or 0.85
        start = time.time()

        while not self._stop_event.is_set():
            if time.time() - start > timeout_s:
                log.warning("CV: timeout — image not found on screen")
                return

            # Screenshot
            screenshot = ImageGrab.grab()
            screen_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # Template matching
            result = cv2.matchTemplate(screen_np, template_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= confidence:
                # Found!
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                if action.type == ActionType.IMAGE_CLICK:
                    if humanize > 0:
                        center_x += int(humanize * random.uniform(-3, 3))
                        center_y += int(humanize * random.uniform(-3, 3))
                    self._smooth_move(center_x, center_y, humanize)
                    self._sleep(50)
                    self._mouse.press(Button.left)
                    self._sleep(60)
                    self._mouse.release(Button.left)
                return

            self._sleep(200)  # poll every 200ms

    # ── Anti-AFK ─────────────────────────────────────────────────────
    def _start_anti_afk(self, interval_s: int):
        self._afk_stop.clear()
        self._afk_thread = threading.Thread(
            target=self._afk_loop, args=(interval_s,), daemon=True, name="AntiAFK"
        )
        self._afk_thread.start()
        log.info("Anti-AFK started (interval=%ds)", interval_s)

    def _stop_anti_afk(self):
        self._afk_stop.set()

    def _afk_loop(self, interval_s: int):
        elapsed = 0
        while not self._afk_stop.is_set() and not self._stop_event.is_set():
            time.sleep(1)
            elapsed += 1
            if elapsed >= interval_s:
                elapsed = 0
                self._do_afk_ping()

    def _do_afk_ping(self):
        """Send a micro camera movement to prevent Roblox AFK disconnect."""
        log.debug("Anti-AFK ping")
        cx, cy = self._mouse.position
        self._mouse.press(Button.right)
        time.sleep(0.05)
        self._mouse.move(1, 0)
        time.sleep(0.05)
        self._mouse.move(-1, 0)
        time.sleep(0.05)
        self._mouse.release(Button.right)

    # ── Helpers ──────────────────────────────────────────────────────
    def _sleep(self, ms: int):
        """Interruptible sleep in milliseconds."""
        end = time.time() + ms / 1000.0
        while time.time() < end and not self._stop_event.is_set():
            time.sleep(min(0.05, end - time.time()))

    def _resolve_key(self, key_str: str):
        key_str = key_str.lower().strip()
        if key_str in SPECIAL_KEYS:
            return SPECIAL_KEYS[key_str]
        if len(key_str) == 1:
            return key_str
        return None

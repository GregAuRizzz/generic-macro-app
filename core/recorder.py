"""
Record & Translate engine.
Listens to real mouse/keyboard events and translates them into Action blocks.
"""
from __future__ import annotations
import time
import threading
import logging
from typing import List, Optional, Callable

from pynput import mouse as pmouse, keyboard as pkeyboard
from models.macro import Action, ActionType

log = logging.getLogger(__name__)

# Keys to ignore during recording (meta keys we don't want to capture)
IGNORE_KEYS = {"f7", "f8", "f9", "f10", "f11", "f12"}


class Recorder:
    """
    Records user input and converts it to a list of Action objects.
    Merges consecutive waits and filters noise.
    """

    def __init__(self):
        self._recording = False
        self._actions: List[Action] = []
        self._last_event_time: float = 0.0
        self._mouse_listener: Optional[pmouse.Listener] = None
        self._keyboard_listener: Optional[pkeyboard.Listener] = None
        self._lock = threading.Lock()
        self._last_mouse_pos: Optional[tuple] = None

        # Callbacks
        self.on_action_recorded: Optional[Callable[[Action], None]] = None
        self.on_stop: Optional[Callable[[List[Action]], None]] = None

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self):
        if self._recording:
            return
        log.info("Recording started")
        self._actions = []
        self._last_event_time = time.time()
        self._recording = True

        self._mouse_listener = pmouse.Listener(
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._keyboard_listener = pkeyboard.Listener(
            on_press=self._on_key_press,
        )
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def stop(self) -> List[Action]:
        if not self._recording:
            return []
        self._recording = False
        log.info("Recording stopped — %d actions", len(self._actions))

        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()

        actions = self._post_process(self._actions)
        if self.on_stop:
            self.on_stop(actions)
        return actions

    def _add_wait(self):
        """Insert a Wait action for the time elapsed since last event."""
        now = time.time()
        elapsed_ms = int((now - self._last_event_time) * 1000)
        self._last_event_time = now

        if elapsed_ms > 80:  # Only add waits > 80ms (filter noise)
            wait = Action(type=ActionType.WAIT, duration_ms=elapsed_ms, delay_after_ms=0)
            with self._lock:
                self._actions.append(wait)
            if self.on_action_recorded:
                self.on_action_recorded(wait)

    def _on_click(self, x, y, button, pressed):
        if not self._recording or not pressed:
            return
        self._add_wait()
        btn_map = {
            pmouse.Button.left: "left",
            pmouse.Button.right: "right",
            pmouse.Button.middle: "middle",
        }
        action = Action(
            type=ActionType.MOUSE_CLICK,
            button=btn_map.get(button, "left"),
            x=x, y=y,
            clicks=1,
            delay_after_ms=0,
        )
        with self._lock:
            self._actions.append(action)
        if self.on_action_recorded:
            self.on_action_recorded(action)

    def _on_scroll(self, x, y, dx, dy):
        if not self._recording:
            return
        self._add_wait()
        action = Action(
            type=ActionType.MOUSE_SCROLL,
            scroll_amount=int(dy * 3),
            delay_after_ms=0,
        )
        with self._lock:
            self._actions.append(action)
        if self.on_action_recorded:
            self.on_action_recorded(action)

    def _on_key_press(self, key):
        if not self._recording:
            return
        key_str = self._key_to_str(key)
        if not key_str or key_str in IGNORE_KEYS:
            return
        self._add_wait()
        action = Action(type=ActionType.KEY_PRESS, key=key_str, delay_after_ms=0)
        with self._lock:
            self._actions.append(action)
        if self.on_action_recorded:
            self.on_action_recorded(action)

    def _key_to_str(self, key) -> str:
        try:
            if hasattr(key, "name"):
                return key.name.lower()
            return key.char.lower() if key.char else ""
        except AttributeError:
            return ""

    def _post_process(self, actions: List[Action]) -> List[Action]:
        """
        Post-process: merge consecutive waits, remove zero-duration waits,
        convert large wait runs into a single wait.
        """
        result = []
        i = 0
        while i < len(actions):
            a = actions[i]
            if a.type == ActionType.WAIT:
                total = a.duration_ms
                while i + 1 < len(actions) and actions[i + 1].type == ActionType.WAIT:
                    i += 1
                    total += actions[i].duration_ms
                if total > 80:
                    merged = Action(type=ActionType.WAIT, duration_ms=total, delay_after_ms=0)
                    result.append(merged)
            else:
                result.append(a)
            i += 1
        return result

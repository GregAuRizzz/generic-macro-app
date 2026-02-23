"""
Global hotkey listener using pynput — works even when app is in background.
"""
from __future__ import annotations
import threading
import logging
from typing import Callable, Optional, Set

from pynput import keyboard as kb

log = logging.getLogger(__name__)


class HotkeyManager:
    def __init__(self):
        self._listener: Optional[kb.Listener] = None
        self._start_key: Optional[str] = None
        self._stop_key: Optional[str] = None
        self._record_key: Optional[str] = None
        self._on_start: Optional[Callable] = None
        self._on_stop: Optional[Callable] = None
        self._on_record: Optional[Callable] = None
        self._active = False

    def configure(self, start_key: str, stop_key: str, record_key: str,
                  on_start: Callable, on_stop: Callable, on_record: Callable):
        self._start_key   = start_key.lower()
        self._stop_key    = stop_key.lower()
        self._record_key  = record_key.lower()
        self._on_start    = on_start
        self._on_stop     = on_stop
        self._on_record   = on_record

    def start_listening(self):
        if self._active:
            return
        self._active = True
        self._listener = kb.Listener(on_press=self._on_press)
        self._listener.start()

    def stop_listening(self):
        self._active = False
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _key_str(self, key) -> str:
        try:
            if hasattr(key, "name"):
                return key.name.lower()
            return key.char.lower() if key.char else ""
        except AttributeError:
            return str(key).lower()

    def _on_press(self, key):
        k = self._key_str(key)
        if k == self._start_key and self._on_start:
            try: self._on_start()
            except Exception as e: log.error("on_start hotkey error: %s", e)
        if k == self._stop_key and self._on_stop:
            try: self._on_stop()
            except Exception as e: log.error("on_stop hotkey error: %s", e)
        if k == self._record_key and self._on_record:
            try: self._on_record()
            except Exception as e: log.error("on_record hotkey error: %s", e)

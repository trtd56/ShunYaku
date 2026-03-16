from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock

from pynput import keyboard


class DoubleCopyWatcher:
    def __init__(self, window_ms: int, on_trigger: Callable[[], None]) -> None:
        self._window_seconds = window_ms / 1000
        self._on_trigger = on_trigger
        self._listener: keyboard.Listener | None = None
        self._lock = Lock()
        self._ctrl_pressed = False
        self._cmd_pressed = False
        self._last_copy_at = 0.0

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        self._listener = None

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        with self._lock:
            if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self._ctrl_pressed = True
                return
            if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
                self._cmd_pressed = True
                return

            if not (self._ctrl_pressed or self._cmd_pressed):
                return

            char = getattr(key, "char", None)
            if char is None or char.lower() != "c":
                return

            now = time.monotonic()
            if now - self._last_copy_at <= self._window_seconds:
                self._last_copy_at = 0.0
                self._on_trigger()
                return

            self._last_copy_at = now

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        with self._lock:
            if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self._ctrl_pressed = False
            if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
                self._cmd_pressed = False

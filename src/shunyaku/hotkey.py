from __future__ import annotations

import sys
import time
from collections.abc import Callable
from threading import Lock

from pynput import keyboard

MACOS_CHARACTER_VKS = {
    "c": 8,
    "t": 17,
}


class GlobalShortcutWatcher:
    def __init__(
        self,
        window_ms: int,
        on_clipboard_trigger: Callable[[], None],
        on_ocr_trigger: Callable[[], None],
    ) -> None:
        self._window_seconds = window_ms / 1000
        self._on_clipboard_trigger = on_clipboard_trigger
        self._on_ocr_trigger = on_ocr_trigger
        self._listener: keyboard.Listener | None = None
        self._lock = Lock()
        self._is_macos = sys.platform == "darwin"
        self._ctrl_pressed = False
        self._cmd_pressed = False
        self._alt_pressed = False
        self._last_copy_at = 0.0
        self._ocr_latched = False

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
            if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                self._alt_pressed = True
                return

            if self._matches_character_key(key, "c") and self._copy_modifier_pressed():
                now = time.monotonic()
                if now - self._last_copy_at <= self._window_seconds:
                    self._last_copy_at = 0.0
                    self._on_clipboard_trigger()
                    return
                self._last_copy_at = now
                return

            if (
                self._matches_character_key(key, "t")
                and self._ocr_modifier_pressed()
                and not self._ocr_latched
            ):
                self._ocr_latched = True
                self._on_ocr_trigger()

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        with self._lock:
            if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                self._ctrl_pressed = False
            if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
                self._cmd_pressed = False
            if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                self._alt_pressed = False

            if self._matches_character_key(key, "t"):
                self._ocr_latched = False

            if not self._ocr_modifier_pressed():
                self._ocr_latched = False

    def _copy_modifier_pressed(self) -> bool:
        if self._is_macos:
            return self._cmd_pressed
        return self._ctrl_pressed or self._cmd_pressed

    def _ocr_modifier_pressed(self) -> bool:
        return self._is_macos and self._cmd_pressed and self._alt_pressed

    def _matches_character_key(
        self,
        key: keyboard.Key | keyboard.KeyCode,
        expected: str,
    ) -> bool:
        char = getattr(key, "char", None)
        if isinstance(char, str) and char.lower() == expected:
            return True

        vk = getattr(key, "vk", None)
        if self._is_macos and vk is not None:
            return vk == MACOS_CHARACTER_VKS.get(expected)
        return False


DoubleCopyWatcher = GlobalShortcutWatcher

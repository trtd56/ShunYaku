from __future__ import annotations

import unittest
from unittest.mock import patch

from pynput import keyboard

from shunyaku.hotkey import GlobalShortcutWatcher


class GlobalShortcutWatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clipboard_triggers = 0
        self.ocr_triggers = 0
        self.watcher = GlobalShortcutWatcher(
            window_ms=750,
            on_clipboard_trigger=self._on_clipboard_trigger,
            on_ocr_trigger=self._on_ocr_trigger,
        )
        self.watcher._is_macos = True

    def _on_clipboard_trigger(self) -> None:
        self.clipboard_triggers += 1

    def _on_ocr_trigger(self) -> None:
        self.ocr_triggers += 1

    def test_double_copy_triggers_when_presses_are_close(self) -> None:
        with patch("shunyaku.hotkey.time.monotonic", side_effect=[1.0, 1.4]):
            self.watcher._on_press(keyboard.Key.cmd)
            self.watcher._on_press(keyboard.KeyCode.from_char("c"))
            self.watcher._on_release(keyboard.KeyCode.from_char("c"))
            self.watcher._on_release(keyboard.Key.cmd)

            self.watcher._on_press(keyboard.Key.cmd)
            self.watcher._on_press(keyboard.KeyCode.from_char("c"))

        self.assertEqual(self.clipboard_triggers, 1)

    def test_ocr_shortcut_triggers_once_until_t_is_released(self) -> None:
        self.watcher._on_press(keyboard.Key.cmd)
        self.watcher._on_press(keyboard.Key.alt)
        self.watcher._on_press(keyboard.KeyCode.from_char("t"))
        self.watcher._on_press(keyboard.KeyCode.from_char("t"))

        self.assertEqual(self.ocr_triggers, 1)

        self.watcher._on_release(keyboard.KeyCode.from_char("t"))
        self.watcher._on_press(keyboard.KeyCode.from_char("t"))

        self.assertEqual(self.ocr_triggers, 2)

    def test_ocr_shortcut_accepts_macos_vk_for_t_with_option_modified_char(self) -> None:
        self.watcher._on_press(keyboard.Key.cmd)
        self.watcher._on_press(keyboard.Key.alt)
        self.watcher._on_press(keyboard.KeyCode.from_vk(17))

        self.assertEqual(self.ocr_triggers, 1)

        self.watcher._on_release(keyboard.KeyCode.from_vk(17))
        self.watcher._on_press(keyboard.KeyCode.from_vk(17))

        self.assertEqual(self.ocr_triggers, 2)

    def test_ocr_shortcut_requires_option_and_command(self) -> None:
        self.watcher._on_press(keyboard.Key.cmd)
        self.watcher._on_press(keyboard.KeyCode.from_char("t"))
        self.watcher._on_release(keyboard.KeyCode.from_char("t"))
        self.watcher._on_release(keyboard.Key.cmd)

        self.watcher._on_press(keyboard.Key.alt)
        self.watcher._on_press(keyboard.KeyCode.from_char("t"))

        self.assertEqual(self.ocr_triggers, 0)


if __name__ == "__main__":
    unittest.main()

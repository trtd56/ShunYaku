from __future__ import annotations

import sys
from concurrent.futures import Future

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

from .config import AppConfig
from .hotkey import DoubleCopyWatcher
from .translator import TranslationError, Translator
from .ui import TranslationPopup, TrayController


class AppSignals(QObject):
    translation_requested = Signal()


class ShunYakuApp:
    def __init__(self) -> None:
        self._qt_app = QApplication(sys.argv)
        self._qt_app.setQuitOnLastWindowClosed(False)
        self._is_shutting_down = False
        self._config = AppConfig()
        self._translator = Translator(self._config)
        self._signals = AppSignals()
        self._popup = TranslationPopup()
        self._tray = TrayController(self._qt_app, self._popup, self.shutdown)
        self._watcher = DoubleCopyWatcher(
            window_ms=self._config.double_copy_window_ms,
            on_trigger=self._emit_translation_request,
        )
        self._signals.translation_requested.connect(self._handle_translation_request)
        self._warmup_future: Future[None] | None = None

    def run(self) -> int:
        self._tray.show()
        shortcut = "Cmd+C" if sys.platform == "darwin" else "Ctrl+C"
        self._popup.show_message(
            "起動完了",
            f"ShunYaku は常駐中です。\n{shortcut} を 2 回押すと翻訳します。",
        )
        self._warmup_future = self._translator.warmup_async()
        self._watcher.start()
        return self._qt_app.exec()

    def shutdown(self) -> None:
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        self._watcher.stop()
        self._translator.shutdown()
        self._qt_app.quit()

    def _emit_translation_request(self) -> None:
        self._signals.translation_requested.emit()

    def _handle_translation_request(self) -> None:
        clipboard = self._qt_app.clipboard()
        text = clipboard.text().strip()
        if not text:
            self._popup.show_message("翻訳できません", "クリップボードが空です。")
            return

        self._popup.show_loading(text)
        future = self._translator.translate_async(text)
        self._attach_future(future)

    def _attach_future(self, future: Future[str]) -> None:
        timer = QTimer()
        timer.setInterval(120)

        def poll() -> None:
            if not future.done():
                return
            timer.stop()
            timer.deleteLater()
            try:
                result = future.result()
            except TranslationError as exc:
                self._popup.show_message("翻訳できません", str(exc))
            except Exception as exc:  # noqa: BLE001
                self._popup.show_message("エラー", f"翻訳中に例外が発生しました。\n{exc}")
            else:
                self._popup.show_message("翻訳結果", result)

        timer.timeout.connect(poll)
        timer.start()


def main() -> int:
    app = ShunYakuApp()
    try:
        return app.run()
    except KeyboardInterrupt:
        app.shutdown()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

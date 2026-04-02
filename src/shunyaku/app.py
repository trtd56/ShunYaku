from __future__ import annotations

import sys
from concurrent.futures import Future
from collections.abc import Callable
from typing import TypeVar

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication

from .config import AppConfig
from .hotkey import GlobalShortcutWatcher
from .ocr import (
    OCRCaptureError,
    OCRNoTextError,
    OCRPermissionError,
    OCRUnavailableError,
    ScreenOCR,
)
from .translator import TranslationError, Translator
from .assets import load_app_icon
from .ui import TranslationPopup, TrayController

T = TypeVar("T")


class AppSignals(QObject):
    translation_requested = Signal()
    ocr_requested = Signal()


class ShunYakuApp:
    def __init__(self) -> None:
        self._qt_app = QApplication(sys.argv)
        self._qt_app.setQuitOnLastWindowClosed(False)
        self._qt_app.setWindowIcon(load_app_icon())
        self._is_shutting_down = False
        self._config = AppConfig()
        self._translator = Translator(self._config)
        self._ocr = ScreenOCR()
        self._signals = AppSignals()
        self._popup = TranslationPopup()
        self._tray = TrayController(self._qt_app, self._popup, self.shutdown)
        self._watcher = GlobalShortcutWatcher(
            window_ms=self._config.double_copy_window_ms,
            on_clipboard_trigger=self._emit_translation_request,
            on_ocr_trigger=self._emit_ocr_request,
        )
        self._signals.translation_requested.connect(self._handle_translation_request)
        self._signals.ocr_requested.connect(self._handle_ocr_request)
        self._warmup_future: Future[None] | None = None

    def run(self) -> int:
        self._tray.show()
        shortcut = "Cmd+C" if sys.platform == "darwin" else "Ctrl+C"
        startup_lines = [
            "ShunYaku は常駐中です。",
            f"{shortcut} を 2 回押すと翻訳します。",
        ]
        if sys.platform == "darwin":
            startup_lines.append("Option+Cmd+T で OCR 翻訳します。")
        self._popup.show_message(
            "起動完了",
            "\n".join(startup_lines),
        )
        self._warmup_future = self._translator.warmup_async()
        self._watcher.start()
        return self._qt_app.exec()

    def shutdown(self) -> None:
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        self._watcher.stop()
        self._ocr.shutdown()
        self._translator.shutdown()
        self._qt_app.quit()

    def _emit_translation_request(self) -> None:
        self._signals.translation_requested.emit()

    def _emit_ocr_request(self) -> None:
        self._signals.ocr_requested.emit()

    def _handle_translation_request(self) -> None:
        self._popup.set_anchor(QCursor.pos())
        clipboard = self._qt_app.clipboard()
        text = clipboard.text().strip()
        if not text:
            self._popup.show_message("翻訳できません", "クリップボードが空です。")
            return

        self._start_translation(text)

    def _handle_ocr_request(self) -> None:
        future = self._ocr.capture_text_async()
        self._attach_future(
            future,
            on_success=self._handle_ocr_result,
            on_error=self._handle_ocr_error,
        )

    def _handle_ocr_result(self, text: str | None) -> None:
        if text is None:
            return
        self._popup.set_anchor(QCursor.pos())
        self._start_translation(text, loading_title="OCR + 翻訳中...")

    def _start_translation(self, text: str, loading_title: str = "翻訳中...") -> None:
        self._popup.show_loading(text, title=loading_title)
        future = self._translator.translate_async(text)
        self._attach_future(
            future,
            on_success=self._handle_translation_result,
            on_error=self._handle_translation_error,
        )

    def _attach_future(
        self,
        future: Future[T],
        on_success: Callable[[T], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        timer = QTimer(self._qt_app)
        timer.setInterval(120)

        def poll() -> None:
            if not future.done():
                return
            timer.stop()
            timer.deleteLater()
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                on_error(exc)
            else:
                on_success(result)

        timer.timeout.connect(poll)
        timer.start()

    def _handle_translation_result(self, result: str) -> None:
        self._popup.show_message("翻訳結果", result)

    def _handle_translation_error(self, exc: Exception) -> None:
        if isinstance(exc, TranslationError):
            self._popup.show_message("翻訳できません", str(exc))
            return
        self._popup.show_message("エラー", f"翻訳中に例外が発生しました。\n{exc}")

    def _handle_ocr_error(self, exc: Exception) -> None:
        if isinstance(exc, OCRUnavailableError):
            self._popup.show_message("OCR を使えません", str(exc))
            return
        if isinstance(exc, OCRPermissionError):
            self._popup.show_message("OCR を使えません", str(exc))
            return
        if isinstance(exc, OCRNoTextError):
            self._popup.show_message("文字を検出できません", str(exc))
            return
        if isinstance(exc, OCRCaptureError):
            self._popup.show_message("キャプチャに失敗しました", str(exc))
            return
        self._popup.show_message("エラー", f"OCR 中に例外が発生しました。\n{exc}")


def main() -> int:
    app = ShunYakuApp()
    try:
        return app.run()
    except KeyboardInterrupt:
        app.shutdown()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

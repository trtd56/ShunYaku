from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QPushButton,
    QStyle,
    QSystemTrayIcon,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class TranslationPopup(QWidget):
    closed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ShunYaku")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setMinimumSize(520, 280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        self.status_label = QLabel("待機中")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        self.translation_view = QTextEdit()
        self.translation_view.setReadOnly(True)
        self.translation_view.setPlaceholderText("ここに翻訳結果が表示されます。")
        layout.addWidget(self.translation_view, 1)

        self.close_button = QPushButton("閉じる")
        self.close_button.clicked.connect(self.hide)
        layout.addWidget(self.close_button)

        self.setStyleSheet(
            """
            QWidget {
                background: #101418;
                color: #f5f7fa;
                font-family: "Hiragino Sans";
                font-size: 14px;
            }
            #statusLabel {
                color: #8dd3c7;
                font-weight: 600;
            }
            QTextEdit {
                background: #182028;
                border: 1px solid #28323d;
                border-radius: 10px;
                padding: 10px;
            }
            QPushButton {
                background: #8dd3c7;
                border: none;
                border-radius: 8px;
                color: #101418;
                font-weight: 700;
                min-height: 36px;
            }
            QPushButton:hover {
                background: #9ce2d7;
            }
            """
        )

    def show_message(self, title: str, body: str) -> None:
        self.status_label.setText(title)
        self.translation_view.setPlainText(body)
        self._show_centered()

    def show_loading(self, source_text: str) -> None:
        preview = source_text.strip()
        if len(preview) > 300:
            preview = preview[:300] + "..."
        self.status_label.setText("翻訳中...")
        self.translation_view.setPlainText(preview)
        self._show_centered()

    def _show_centered(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            screen_geometry: QRect = screen.availableGeometry()
            center = screen_geometry.center()
            target = QPoint(
                center.x() - self.width() // 2,
                center.y() - self.height() // 2,
            )
            self.move(target)
        self.show()
        self.raise_()
        self.activateWindow()

    def hideEvent(self, event: QEvent) -> None:
        self.closed.emit()
        super().hideEvent(event)


class TrayController:
    def __init__(self, app: QApplication, popup: TranslationPopup, on_quit) -> None:
        self._app = app
        self._popup = popup
        tray_icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self._tray = QSystemTrayIcon(tray_icon)
        self._tray.setToolTip("ShunYaku")

        menu = QMenu()
        open_action = QAction("ポップアップを開く", menu)
        open_action.triggered.connect(self._popup.show)
        menu.addAction(open_action)

        quit_action = QAction("終了", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_activated)

    def show(self) -> None:
        self._tray.show()

    def notify(self, title: str, message: str) -> None:
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._popup.show()

import sys
import html
import csv
import json
import re
import subprocess
import shutil
import ssl
import urllib.error
import urllib.request
from math import ceil, sqrt
from dataclasses import dataclass, field
from pathlib import Path
import tempfile

from backend.local_api import (
    API_BASE_URL,
    ensure_api_server,
    get_content as api_get_content,
    get_settings as api_get_settings,
    login as api_login,
    record_activity,
    record_browser_session,
    delete_content as api_delete_content,
    save_content as api_save_content,
    update_content as api_update_content,
    upsert_setting,
)
from PySide6.QtCore import (
    QDateTime,
    QEasingCurve,
    QObject,
    Property,
    QPropertyAnimation,
    QTimer,
    Qt,
    QEvent,
    QPoint,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QGraphicsOpacityEffect,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QTextEdit,
    QDoubleSpinBox,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QTextBrowser,
    QWidget,
)


APP_TITLE = "EzyMailer"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
IS_MAC = sys.platform == "darwin"
MAX_BODY_TABS = 50


def _scaled_int(value: float, scale: float, minimum: int = 1) -> int:
    return max(minimum, int(round(value * scale)))


def _compute_layout_scale(screen) -> float:
    if screen is None:
        return 1.00

    geometry = screen.availableGeometry()
    width_boost = max(0.0, (geometry.width() - 1280.0) / 8000.0)
    height_boost = max(0.0, (geometry.height() - 768.0) / 8000.0)
    scale = 1.0 + min(0.06, width_boost + height_boost)
    return max(1.0, min(1.06, scale))


def _compute_text_scale(screen) -> float:
    if screen is None:
        return 1.28

    geometry = screen.availableGeometry()
    width_boost = max(0.0, (geometry.width() - 1280.0) / 2200.0)
    height_boost = max(0.0, (geometry.height() - 768.0) / 2600.0)
    scale = 1.28 + min(0.12, (width_boost + height_boost) * 0.8)
    return max(1.28, min(1.40, scale))


@dataclass
class AppState:
    username: str = ""
    logged_in: bool = False
    auth_token: str = ""
    browser_mode: str = "Incognito"
    window_count: int = 1
    launch_preset: str = "Default"
    active_sessions: list[str] = field(default_factory=list)
    activity_log: list[str] = field(default_factory=list)
    pending_recipients: list[str] = field(default_factory=list)
    body_mode: str = "Normal Message"
    subject_text: str = ""
    plain_body_text: str = ""
    html_message_text: str = ""
    html_template_text: str = ""
    ai_provider: str = "ChatGPT"
    ai_model: str = ""
    ai_connected: bool = False


@dataclass
class BrowserSessionHandle:
    session_id: str
    title: str
    mode: str
    process: subprocess.Popen[str] | None = None
    status: str = "Starting"
    profile_dir: Path | None = None

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None


class AIValidationWorker(QObject):
    finished = Signal(str, list)
    failed = Signal(str)

    def __init__(self, provider: str, api_key: str):
        super().__init__()
        self.provider = provider
        self.api_key = api_key

    def run(self) -> None:
        try:
            models = self._fetch_models()
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(self.provider, models)

    def _fetch_models(self) -> list[str]:
        provider = self.provider
        context = self._ssl_context()
        if provider == "Claude":
            request = urllib.request.Request(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "accept": "application/json",
                },
                method="GET",
            )
        elif provider == "DeepSeek":
            request = urllib.request.Request(
                "https://api.deepseek.com/models",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "accept": "application/json",
                },
                method="GET",
            )
        else:
            request = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "accept": "application/json",
                },
                method="GET",
            )

        with urllib.request.urlopen(request, timeout=20, context=context) as response:
            payload = json.loads(response.read().decode("utf-8"))

        return self._extract_model_ids(payload)

    def _ssl_context(self) -> ssl.SSLContext:
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return ssl.create_default_context()

    def _extract_model_ids(self, payload) -> list[str]:
        models: list[str] = []
        if isinstance(payload, dict):
            entries = payload.get("data") or payload.get("models") or []
        elif isinstance(payload, list):
            entries = payload
        else:
            entries = []

        for item in entries:
            if isinstance(item, dict):
                model_id = item.get("id") or item.get("name") or item.get("model")
                if model_id:
                    models.append(str(model_id))

        unique_models = list(dict.fromkeys(models))
        if not unique_models:
            raise ValueError("No models were returned by the provider.")
        return unique_models


class AnimatedLogoBadge(QWidget):
    def __init__(self, parent=None, scale: float = 1.0):
        super().__init__(parent)
        self._scale = scale
        self._pulse = 0.0
        self.setFixedSize(_scaled_int(40, self._scale), _scaled_int(40, self._scale))
        self._anim = QPropertyAnimation(self, b"pulse", self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(1800)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.start()

    def getPulse(self) -> float:
        return self._pulse

    def setPulse(self, value: float) -> None:
        self._pulse = value
        self.update()

    pulse = Property(float, getPulse, setPulse)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pulse = 0.35 + (self._pulse * 0.65)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(37, 99, 235, int(42 + pulse * 80)))
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))

        painter.setBrush(QColor("#2563eb"))
        painter.drawEllipse(self.rect().adjusted(5, 5, -5, -5))

        pen_width = max(1.0, 1.4 * self._scale)
        painter.setPen(QPen(QColor("#67e8f9"), pen_width))
        painter.drawLine(_scaled_int(18, self._scale), _scaled_int(10, self._scale), _scaled_int(15, self._scale), _scaled_int(19, self._scale))
        painter.drawLine(_scaled_int(15, self._scale), _scaled_int(19, self._scale), _scaled_int(21, self._scale), _scaled_int(19, self._scale))
        painter.drawLine(_scaled_int(21, self._scale), _scaled_int(19, self._scale), _scaled_int(18, self._scale), _scaled_int(29, self._scale))

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", _scaled_int(10, self._scale), QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, "EZ")


class MacTrafficLightButton(QPushButton):
    def __init__(self, kind: str, scale: float = 1.0, parent=None):
        super().__init__(parent)
        self._kind = kind
        self._scale = scale
        self._hover = False
        self.setObjectName("macTrafficLightButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        self.setText("")
        size = _scaled_int(14, self._scale)
        self.setFixedSize(size, size)
        self.setToolTip({
            "close": "Close the window",
            "minimize": "Minimize the window",
            "maximize": "Maximize or restore the window",
        }.get(kind, "Window control"))

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        colors = {
            "close": QColor("#ff5f57"),
            "minimize": QColor("#febc2e"),
            "maximize": QColor("#28c840"),
        }
        base = colors.get(self._kind, QColor("#7a7a7a"))
        if self._hover:
            base = base.lighter(110)

        painter.setPen(Qt.NoPen)
        painter.setBrush(base)
        painter.drawEllipse(self.rect().adjusted(0, 0, -1, -1))

        if self._hover:
            painter.setPen(QPen(QColor(0, 0, 0, 180), max(1, _scaled_int(1, self._scale))))
            w = self.width()
            h = self.height()
            if self._kind == "close":
                painter.drawLine(_scaled_int(4, self._scale), _scaled_int(4, self._scale), w - _scaled_int(4, self._scale), h - _scaled_int(4, self._scale))
                painter.drawLine(w - _scaled_int(4, self._scale), _scaled_int(4, self._scale), _scaled_int(4, self._scale), h - _scaled_int(4, self._scale))
            elif self._kind == "minimize":
                painter.drawLine(_scaled_int(4, self._scale), h // 2, w - _scaled_int(4, self._scale), h // 2)
            else:
                painter.drawLine(_scaled_int(4, self._scale), h // 2, w - _scaled_int(4, self._scale), h // 2)
                painter.drawLine(w // 2, _scaled_int(4, self._scale), w // 2, h - _scaled_int(4, self._scale))


class TitleBar(QWidget):
    def __init__(self, window, on_close, scale: float = 1.0):
        super().__init__()
        self._window = window
        self._on_close = on_close
        self._drag_pos = None
        self._is_maximized = False
        self._scale = scale
        self.setObjectName("topBar")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        if IS_MAC:
            layout.setContentsMargins(_scaled_int(8, self._scale), _scaled_int(1, self._scale), _scaled_int(8, self._scale), _scaled_int(1, self._scale))
            layout.setSpacing(_scaled_int(4, self._scale))
        else:
            layout.setContentsMargins(_scaled_int(4, self._scale), _scaled_int(2, self._scale), _scaled_int(4, self._scale), _scaled_int(2, self._scale))
            layout.setSpacing(_scaled_int(6, self._scale))

        controls = None
        if IS_MAC:
            controls = QHBoxLayout()
            controls.setSpacing(_scaled_int(5, self._scale))
            self.close_button = MacTrafficLightButton("close", self._scale)
            self.close_button.clicked.connect(self._on_close)
            self.minimize_button = MacTrafficLightButton("minimize", self._scale)
            self.minimize_button.clicked.connect(self._window.showMinimized)
            self.maximize_button = MacTrafficLightButton("maximize", self._scale)
            self.maximize_button.clicked.connect(self._toggle_maximize)
            controls.addWidget(self.close_button)
            controls.addWidget(self.minimize_button)
            controls.addWidget(self.maximize_button)
            controls.addSpacing(_scaled_int(6, self._scale))

        brand = QHBoxLayout()
        brand.setSpacing(_scaled_int(6, self._scale))
        self.logo = AnimatedLogoBadge(scale=self._scale)
        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        title = QLabel("EzyMailer")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Desktop workspace for email automation")
        subtitle.setObjectName("brandSubtitle")
        if IS_MAC:
            title.setStyleSheet("font-weight: 800;")
            brand.addWidget(title)
        else:
            title_block.addWidget(title)
            title_block.addWidget(subtitle)
            brand.addWidget(self.logo)
            brand.addLayout(title_block)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        version_badge = QLabel("v2.0")
        version_badge.setObjectName("versionBadge")
        self.status_badge = QLabel("LOCKED")
        self.status_badge.setObjectName("statusBadge")
        for badge in (version_badge, self.status_badge):
            badge.setFixedHeight(_scaled_int(24 if IS_MAC else 28, self._scale))
            badge.setMinimumWidth(_scaled_int(58 if IS_MAC else 64, self._scale))
            badge.setAlignment(Qt.AlignCenter)
        version_badge.setToolTip("Application version")
        self.status_badge.setToolTip("Current login status")
        if IS_MAC:
            version_badge.hide()
            self.status_badge.hide()

        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("secondaryButton")
        self.logout_button.setFixedHeight(_scaled_int(24 if IS_MAC else 28, self._scale))
        self.logout_button.setMinimumWidth(_scaled_int(58 if IS_MAC else 64, self._scale))
        self.logout_button.setToolTip("Sign out and return to login")

        if not IS_MAC:
            self.minimize_button = QPushButton("−")
            self.minimize_button.setObjectName("windowControlButton")
            self.minimize_button.setFixedSize(_scaled_int(28, self._scale), _scaled_int(28, self._scale))
            self.minimize_button.clicked.connect(self._window.showMinimized)
            self.minimize_button.setToolTip("Minimize window")
            self.maximize_button = QPushButton("▢")
            self.maximize_button.setObjectName("windowControlButton")
            self.maximize_button.setFixedSize(_scaled_int(28, self._scale), _scaled_int(28, self._scale))
            self.maximize_button.clicked.connect(self._toggle_maximize)
            self.maximize_button.setToolTip("Maximize or restore window")
            self.close_button = QPushButton("✕")
            self.close_button.setObjectName("closeButton")
            self.close_button.setFixedSize(_scaled_int(28, self._scale), _scaled_int(28, self._scale))
            self.close_button.setText("✕")
            self.close_button.clicked.connect(self._on_close)
            self.close_button.setToolTip("Close application")

        if controls is not None:
            layout.addLayout(controls)
        layout.addLayout(brand)
        layout.addWidget(spacer)
        if not IS_MAC:
            layout.addWidget(version_badge)
            layout.addWidget(self.status_badge)
        if not IS_MAC:
            layout.addWidget(self.minimize_button)
            layout.addWidget(self.maximize_button)
        layout.addWidget(self.logout_button)
        if not IS_MAC:
            layout.addWidget(self.close_button)

    def set_state(self, username: str, logged_in: bool) -> None:
        self.status_badge.setText("READY" if logged_in else "LOCKED")
        self.logout_button.setVisible(logged_in)

    def sync_window_state(self) -> None:
        self._is_maximized = self._window.isMaximized()
        if not IS_MAC:
            self.maximize_button.setText("❐" if self._is_maximized else "▢")

    def _toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()
        self.sync_window_state()

    def set_logout_handler(self, handler) -> None:
        self.logout_button.clicked.connect(handler)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._toggle_maximize()
            event.accept()


class Toast(QFrame):
    def __init__(self, parent: QWidget, message: str, kind: str = "info", scale: float = 1.0):
        super().__init__(parent)
        self._scale = scale
        self.setObjectName("toast")
        self.setProperty("kind", kind)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setFixedWidth(_scaled_int(360, self._scale))
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._effect.setOpacity(0.0)
        self._build_ui(message, kind)

        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(180)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)

        self._fade_out = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_out.setDuration(220)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.finished.connect(self.deleteLater)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close_out)

    def _build_ui(self, message: str, kind: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(8, self._scale), _scaled_int(12, self._scale), _scaled_int(8, self._scale))
        layout.setSpacing(_scaled_int(8, self._scale))

        icon = QLabel("●")
        icon.setObjectName("toastIcon")
        icon.setFixedSize(_scaled_int(14, self._scale), _scaled_int(14, self._scale))
        icon.setAlignment(Qt.AlignCenter)
        if kind == "warning":
            icon.setText("!")
        elif kind == "success":
            icon.setText("✓")
        elif kind == "error":
            icon.setText("×")

        text = QLabel(message)
        text.setWordWrap(False)
        text.setObjectName("toastText")
        text.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout.addWidget(icon)
        layout.addWidget(text, 1)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fade_in.start()
        self._timer.start(2200)

    def close_out(self) -> None:
        self._fade_out.start()


class RobotLoaderBadge(QWidget):
    def __init__(self, parent=None, scale: float = 1.0):
        super().__init__(parent)
        self._scale = scale
        self._pulse = 0.0
        self._blink = False
        self.setFixedSize(_scaled_int(104, self._scale), _scaled_int(104, self._scale))
        self._pulse_anim = QPropertyAnimation(self, b"pulse", self)
        self._pulse_anim.setStartValue(0.0)
        self._pulse_anim.setEndValue(1.0)
        self._pulse_anim.setDuration(1500)
        self._pulse_anim.setLoopCount(-1)
        self._pulse_anim.setEasingCurve(QEasingCurve.InOutSine)
        self._pulse_anim.start()

        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(520)
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._blink_timer.start()

    def _toggle_blink(self) -> None:
        self._blink = not self._blink
        self.update()

    def getPulse(self) -> float:
        return self._pulse

    def setPulse(self, value: float) -> None:
        self._pulse = value
        self.update()

    pulse = Property(float, getPulse, setPulse)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        pulse = 0.35 + (self._pulse * 0.65)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(14, 99, 156, int(34 + pulse * 60)))
        inset = _scaled_int(4, self._scale)
        painter.drawEllipse(rect.adjusted(inset, inset, -inset, -inset))

        # antenna
        painter.setPen(QPen(QColor("#8bd5ff"), 2))
        painter.drawLine(rect.center().x(), _scaled_int(10, self._scale), rect.center().x(), _scaled_int(24, self._scale))
        painter.setBrush(QColor("#f9fafb"))
        painter.drawEllipse(rect.center().x() - _scaled_int(4, self._scale), _scaled_int(6, self._scale), _scaled_int(8, self._scale), _scaled_int(8, self._scale))

        # head
        head = rect.adjusted(_scaled_int(18, self._scale), _scaled_int(24, self._scale), -_scaled_int(18, self._scale), -_scaled_int(24, self._scale))
        painter.setBrush(QColor("#2d2d30"))
        painter.setPen(QPen(QColor("#4b4b4b"), 1))
        painter.drawRoundedRect(head, 18, 18)

        # eyes
        eye_y = head.center().y() - _scaled_int(10, self._scale)
        eye_color = QColor("#9cdcfe") if not self._blink else QColor("#3a3d41")
        painter.setBrush(eye_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(head.center().x() - _scaled_int(19, self._scale), eye_y, _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(4, self._scale), _scaled_int(4, self._scale))
        painter.drawRoundedRect(head.center().x() + _scaled_int(7, self._scale), eye_y, _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(4, self._scale), _scaled_int(4, self._scale))

        # mouth / badge line
        painter.setBrush(QColor("#0e639c"))
        painter.drawRoundedRect(head.center().x() - _scaled_int(18, self._scale), head.center().y() + _scaled_int(10, self._scale), _scaled_int(36, self._scale), _scaled_int(8, self._scale), _scaled_int(4, self._scale), _scaled_int(4, self._scale))

        # body
        body = rect.adjusted(_scaled_int(30, self._scale), _scaled_int(56, self._scale), -_scaled_int(30, self._scale), -_scaled_int(16, self._scale))
        painter.setBrush(QColor("#1e1e1e"))
        painter.setPen(QPen(QColor("#3c3c3c"), 1))
        painter.drawRoundedRect(body, 10, 10)
        painter.setPen(QPen(QColor("#6b7280"), 2))
        painter.drawLine(body.left() + 10, body.bottom() - 8, body.right() - 10, body.bottom() - 8)
        painter.drawLine(body.left() + 14, body.bottom() - 4, body.left() + 14, body.bottom() + 4)
        painter.drawLine(body.right() - 14, body.bottom() - 4, body.right() - 14, body.bottom() + 4)


class LaunchLoaderDialog(QDialog):
    def __init__(self, parent=None, scale: float = 1.0):
        super().__init__(parent)
        self._scale = scale
        self.setModal(False)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("launchLoader")
        self._dots = 0
        self._build_ui()

        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(_scaled_int(260, self._scale))
        self._dot_timer.timeout.connect(self._animate_dots)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(_scaled_int(24, self._scale), _scaled_int(24, self._scale), _scaled_int(24, self._scale), _scaled_int(24, self._scale))
        root.setSpacing(0)

        root.addStretch()

        card = QFrame()
        card.setObjectName("loaderCard")
        card.setFixedWidth(_scaled_int(360, self._scale))
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(_scaled_int(18, self._scale), _scaled_int(18, self._scale), _scaled_int(18, self._scale), _scaled_int(18, self._scale))
        card_layout.setSpacing(_scaled_int(10, self._scale))
        card_layout.setAlignment(Qt.AlignCenter)

        self.robot = RobotLoaderBadge(scale=self._scale)
        self.loader_title = QLabel("Launching browser windows")
        self.loader_title.setObjectName("loaderTitle")
        self.loader_title.setAlignment(Qt.AlignCenter)
        self.loader_subtitle = QLabel("Applying browser mode and launch preset.")
        self.loader_subtitle.setObjectName("loaderSubtitle")
        self.loader_subtitle.setAlignment(Qt.AlignCenter)
        self.loader_subtitle.setWordWrap(True)
        self.loader_status = QLabel("Preparing")
        self.loader_status.setObjectName("loaderStatus")
        self.loader_status.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(self.robot, alignment=Qt.AlignCenter)
        card_layout.addWidget(self.loader_title)
        card_layout.addWidget(self.loader_subtitle)
        card_layout.addWidget(self.loader_status)

        root.addWidget(card, alignment=Qt.AlignCenter)
        root.addStretch()

    def set_message(self, title: str, subtitle: str | None = None) -> None:
        self.loader_title.setText(title)
        if subtitle:
            self.loader_subtitle.setText(subtitle)

    def _animate_dots(self) -> None:
        self._dots = (self._dots + 1) % 4
        self.loader_status.setText("Preparing" + ("." * self._dots))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.frameGeometry())
        self._dot_timer.start()

    def closeEvent(self, event) -> None:
        self._dot_timer.stop()
        super().closeEvent(event)


class ConfirmDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, message: str, scale: float = 1.0):
        super().__init__(parent)
        self._scale = scale
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("confirmDialog")
        self._build_ui(title, message)

    def _build_ui(self, title: str, message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_scaled_int(16, self._scale), _scaled_int(16, self._scale), _scaled_int(16, self._scale), _scaled_int(16, self._scale))
        layout.setSpacing(_scaled_int(10, self._scale))

        card = QFrame()
        card.setObjectName("confirmCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(_scaled_int(16, self._scale), _scaled_int(16, self._scale), _scaled_int(16, self._scale), _scaled_int(16, self._scale))
        card_layout.setSpacing(_scaled_int(10, self._scale))

        title_label = QLabel(title)
        title_label.setObjectName("confirmTitle")
        title_label.setAlignment(Qt.AlignCenter)
        message_label = QLabel(message)
        message_label.setObjectName("confirmText")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)

        buttons = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        buttons.button(QDialogButtonBox.Yes).setText("Confirm")
        buttons.button(QDialogButtonBox.No).setText("Cancel")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        card_layout.addWidget(title_label)
        card_layout.addWidget(message_label)
        card_layout.addWidget(buttons)
        layout.addWidget(card)


class BodyDraftEditor(QWidget):
    contentChanged = Signal()
    titleChanged = Signal(str)
    modeChanged = Signal(str)
    previewRequested = Signal()

    def __init__(self, scale: float = 1.0):
        super().__init__()
        self._scale = scale
        self.draft_id: int | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_scaled_int(10, self._scale), _scaled_int(10, self._scale), _scaled_int(10, self._scale), _scaled_int(10, self._scale))
        layout.setSpacing(_scaled_int(8, self._scale))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        title_row = QHBoxLayout()
        title_label = QLabel("Tab label")
        title_label.setObjectName("fieldLabel")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Tab label")
        self.title_input.setToolTip("Name this body tab")
        title_row.addWidget(title_label)
        title_row.addWidget(self.title_input, 1)
        layout.addLayout(title_row)

        mode_row = QHBoxLayout()
        mode_label = QLabel("Mode")
        mode_label.setObjectName("fieldLabel")
        self.plain_button = QPushButton("Plain Text")
        self.html_button = QPushButton("HTML Body")
        self.preview_button = QPushButton("Preview")
        self.plain_button.setCheckable(True)
        self.html_button.setCheckable(True)
        self.plain_button.setChecked(True)
        self._plain_group = QButtonGroup(self)
        self._plain_group.setExclusive(True)
        self._plain_group.addButton(self.plain_button)
        self._plain_group.addButton(self.html_button)
        self.plain_button.clicked.connect(lambda: self.set_mode("Normal Message"))
        self.html_button.clicked.connect(lambda: self.set_mode("HTML Message"))
        self.preview_button.setObjectName("secondaryButton")
        self.preview_button.setVisible(False)
        self.preview_button.clicked.connect(self.previewRequested.emit)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.plain_button)
        mode_row.addWidget(self.html_button)
        mode_row.addStretch()
        mode_row.addWidget(self.preview_button)
        layout.addLayout(mode_row)

        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.plain_editor = QTextEdit()
        self.plain_editor.setObjectName("bodyEditor")
        self.plain_editor.setPlaceholderText("Type the plain text body here...")
        self.plain_editor.setToolTip("Compose the plain text body")
        self.plain_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.html_editor = QTextEdit()
        self.html_editor.setObjectName("bodyEditor")
        self.html_editor.setPlaceholderText("<!-- Paste HTML body here -->")
        self.html_editor.setToolTip("Compose the HTML body")
        self.html_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.stack.addWidget(self.plain_editor)
        self.stack.addWidget(self.html_editor)
        layout.addWidget(self.stack, 1)

        self.title_input.textChanged.connect(lambda _text: self.titleChanged.emit(self.title_text()))
        self.title_input.textChanged.connect(self.contentChanged.emit)
        self.plain_editor.textChanged.connect(self.contentChanged.emit)
        self.html_editor.textChanged.connect(self.contentChanged.emit)
        self.html_editor.textChanged.connect(self._sync_preview_button_state)
        self.modeChanged.connect(lambda _mode: self._sync_preview_button_state())
        self._sync_preview_button_state()

    def title_text(self) -> str:
        return self.title_input.text().strip()

    def mode_text(self) -> str:
        return "HTML Message" if self.html_button.isChecked() else "Normal Message"

    def set_mode(self, mode: str) -> None:
        self.plain_button.setChecked(mode != "HTML Message")
        self.html_button.setChecked(mode == "HTML Message")
        self.stack.setCurrentIndex(1 if mode == "HTML Message" else 0)
        self.modeChanged.emit(self.mode_text())
        self.contentChanged.emit()
        self._sync_preview_button_state()

    def set_content(self, title: str, mode: str, plain_text: str, html_text: str) -> None:
        self.blockSignals(True)
        self.title_input.blockSignals(True)
        self.plain_editor.blockSignals(True)
        self.html_editor.blockSignals(True)
        try:
            self.title_input.setText(title)
            self.plain_editor.setPlainText(plain_text)
            self.html_editor.setPlainText(html_text)
            self.set_mode(mode)
            self._sync_preview_button_state()
        finally:
            self.title_input.blockSignals(False)
            self.plain_editor.blockSignals(False)
            self.html_editor.blockSignals(False)
            self.blockSignals(False)

    def payload(self) -> dict[str, str]:
        return {
            "title": self.title_text(),
            "mode": self.mode_text(),
            "plain_text": self.plain_editor.toPlainText(),
            "html_text": self.html_editor.toPlainText(),
        }

    def _sync_preview_button_state(self) -> None:
        has_html = bool(self.html_editor.toPlainText().strip())
        self.preview_button.setVisible(self.mode_text() == "HTML Message" and has_html)

class SubjectDraftsDialog(QDialog):
    def __init__(self, parent: QWidget, auth_token: str, scale: float = 1.0):
        super().__init__(parent)
        self._scale = scale
        self._auth_token = auth_token
        self._applied_subject = ""
        self.setWindowTitle("Subjects")
        self.setModal(True)
        self.setObjectName("confirmDialog")
        self._build_ui()
        self._load_subjects()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale))
        layout.setSpacing(_scaled_int(10, self._scale))

        header = QLabel("Manage Subjects")
        header.setObjectName("sectionTitle")
        subtitle = QLabel("Select, edit, create, or remove subjects.")
        subtitle.setObjectName("sectionSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(header)
        layout.addWidget(subtitle)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)

        left_card = QFrame()
        left_card.setObjectName("dialogCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale))
        left_layout.setSpacing(_scaled_int(8, self._scale))

        self.subject_list = QListWidget()
        self.subject_list.currentItemChanged.connect(self._on_selection_changed)
        self.subject_list.itemDoubleClicked.connect(lambda _item: self._apply_subject())
        left_layout.addWidget(self.subject_list, 1)

        right_card = QFrame()
        right_card.setObjectName("dialogCard")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale))
        right_layout.setSpacing(_scaled_int(8, self._scale))

        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Type or edit a subject")
        self.subject_input.setToolTip("Edit the selected subject")
        right_layout.addWidget(QLabel("Subject"))
        right_layout.addWidget(self.subject_input)

        actions = QHBoxLayout()
        self.new_button = QPushButton("New")
        self.save_button = QPushButton("Save")
        self.delete_button = QPushButton("Delete")
        self.apply_button = QPushButton("Use Subject")
        self.refresh_button = QPushButton("Refresh")
        for button in (self.new_button, self.save_button, self.delete_button, self.apply_button, self.refresh_button):
            actions.addWidget(button)
        right_layout.addLayout(actions)

        self.count_label = QLabel("0 subjects")
        self.count_label.setObjectName("sectionSubtitle")
        right_layout.addWidget(self.count_label)
        right_layout.addStretch()

        self.new_button.clicked.connect(self._new_subject)
        self.save_button.clicked.connect(self._save_subject)
        self.delete_button.clicked.connect(self._delete_subject)
        self.apply_button.clicked.connect(self._apply_subject)
        self.refresh_button.clicked.connect(self._load_subjects)

        split.addWidget(left_card)
        split.addWidget(right_card)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        layout.addWidget(split, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_subject(self) -> str:
        return self._applied_subject.strip()

    def _item_record_id(self, item: QListWidgetItem | None) -> int | None:
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return int(value) if value else None

    def _item_subject(self, item: QListWidgetItem | None) -> str:
        if item is None:
            return ""
        return str(item.data(Qt.UserRole + 2) or "")

    def _set_item_data(self, item: QListWidgetItem, record_id: int | None, title: str, subject: str) -> None:
        item.setData(Qt.UserRole, record_id)
        item.setData(Qt.UserRole + 1, title)
        item.setData(Qt.UserRole + 2, subject)
        item.setText(title or subject or "Untitled Subject")

    def _load_subjects(self) -> None:
        try:
            payload = api_get_content(self._auth_token)
        except Exception as exc:
            self.count_label.setText("Unable to load subjects")
            return

        rows = payload.get("content") or []
        filtered_rows: list[dict[str, object]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            details = row.get("details_json")
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except Exception:
                    details = {}
            kind = ""
            if isinstance(details, dict):
                kind = str(details.get("kind") or "")
            content_type = str(row.get("content_type") or "")
            if content_type in {"subject", "subject-draft"} or kind in {"subject", "subject-draft"}:
                filtered_rows.append(row)
        self.subject_list.blockSignals(True)
        try:
            self.subject_list.clear()
            for row in reversed(filtered_rows):
                item = QListWidgetItem()
                record_id = int(row.get("id") or 0) or None
                title = str(row.get("title") or row.get("subject") or "Subject")
                subject = str(row.get("subject") or row.get("title") or "")
                self._set_item_data(item, record_id, title, subject)
                self.subject_list.addItem(item)
            if self.subject_list.count() > 0:
                self.subject_list.setCurrentRow(self.subject_list.count() - 1)
        finally:
            self.subject_list.blockSignals(False)

        self.count_label.setText(f"{self.subject_list.count()} subject(s)")
        if self.subject_list.currentItem() is not None:
            self.subject_input.setText(self._item_subject(self.subject_list.currentItem()))

    def _on_selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        self.subject_input.setText(self._item_subject(current))

    def _new_subject(self) -> None:
        self.subject_list.blockSignals(True)
        try:
            self.subject_list.clearSelection()
        finally:
            self.subject_list.blockSignals(False)
        self.subject_input.clear()

    def _save_subject(self) -> None:
        subject = self.subject_input.text().strip()
        if not subject:
            return

        current_item = self.subject_list.currentItem()
        title = subject[:64] or "Subject"
        details = {"kind": "subject"}
        try:
            if current_item is not None and current_item.data(Qt.UserRole):
                record_id = int(current_item.data(Qt.UserRole))
                api_update_content(
                    self._auth_token,
                    record_id,
                    "subject",
                    title,
                    subject=subject,
                    details=details,
                )
            else:
                api_save_content(
                    self._auth_token,
                    "subject",
                    title,
                    subject=subject,
                    details=details,
                )
        except Exception:
            return
        self._load_subjects()
        self.subject_input.setText(subject)

    def _delete_subject(self) -> None:
        current_item = self.subject_list.currentItem()
        if current_item is None:
            return
        record_id = current_item.data(Qt.UserRole)
        if not record_id:
            self._new_subject()
            return
        try:
            api_delete_content(self._auth_token, int(record_id))
        except Exception:
            return
        self._load_subjects()
        self.subject_input.clear()

    def _apply_subject(self) -> None:
        self._applied_subject = self.subject_input.text().strip()
        if self._applied_subject:
            self.accept()


class OutputOptionsDialog(QDialog):
    def __init__(self, parent=None, scale: float = 1.0):
        super().__init__(parent)
        self._scale = scale
        self.setWindowTitle("Export Options")
        self.setModal(True)
        self.setObjectName("outputDialog")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale))
        layout.setSpacing(_scaled_int(10, self._scale))

        layout.addWidget(self._dialog_card("EXPORT FORMAT", [
            "PDF document",
            "Excel spreadsheet (XLSX)",
            "Excel template (XLTX)",
            "PowerPoint presentation (PPTX)",
            "PowerPoint slideshow (PPSX)",
            "Word document (DOCX)",
        ]))

        file_card = QFrame()
        file_card.setObjectName("dialogCard")
        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale))
        file_layout.setSpacing(_scaled_int(8, self._scale))
        title = QLabel("FILE NAME")
        title.setObjectName("sectionTitle")
        file_layout.addWidget(title)

        self.auto_name = QRadioButton("Auto-generate a unique name")
        self.custom_name = QRadioButton("Use a custom name:")
        self.auto_name.setChecked(True)
        file_layout.addWidget(self.auto_name)
        custom_row = QHBoxLayout()
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText("Enter file name")
        custom_row.addWidget(self.custom_name)
        custom_row.addWidget(self.custom_name_input, 1)
        custom_row.addWidget(QLabel(".pptx"))
        file_layout.addLayout(custom_row)
        layout.addWidget(file_card)

        image_card = QFrame()
        image_card.setObjectName("dialogCard")
        image_layout = QVBoxLayout(image_card)
        image_layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale))
        image_layout.setSpacing(_scaled_int(8, self._scale))
        image_title = QLabel("IMAGE")
        image_title.setObjectName("sectionTitle")
        image_layout.addWidget(image_title)
        image_layout.addWidget(QLabel("Image format used to capture the preview before export."))
        image_layout.addWidget(QLabel("Supported formats: PNG, JPG, WEBP"))
        layout.addWidget(image_card)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None:
            self.adjustSize()
            parent_center = parent.frameGeometry().center()
            self.move(
                parent_center.x() - self.width() // 2,
                parent_center.y() - self.height() // 2,
            )

    def _dialog_card(self, title: str, options: list[str]) -> QFrame:
        card = QFrame()
        card.setObjectName("dialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale))
        card_layout.setSpacing(_scaled_int(8, self._scale))
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        card_layout.addWidget(title_label)
        for option in options:
            card_layout.addWidget(QRadioButton(option))
        return card


class HtmlPreviewDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, html: str, source_label: str = "", scale: float = 1.0):
        super().__init__(parent)
        self._scale = scale
        self.setModal(False)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setObjectName("previewDialog")
        self._source_html = html
        self._source_visible = False
        self._build_ui(title, source_label, html)

    def _build_ui(self, title: str, source_label: str, html: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale))
        layout.setSpacing(_scaled_int(10, self._scale))

        card = QFrame()
        card.setObjectName("previewCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(_scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale))
        card_layout.setSpacing(_scaled_int(10, self._scale))

        header_row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        header_row.addWidget(title_label)
        header_row.addStretch()
        reload_button = QPushButton("Reload")
        reload_button.setObjectName("secondaryButton")
        reload_button.setFixedHeight(_scaled_int(28, self._scale))
        reload_button.setToolTip("Reload the preview from the current HTML source")
        reload_button.clicked.connect(self._reload_preview)

        source_button = QPushButton("Source")
        source_button.setObjectName("secondaryButton")
        source_button.setFixedHeight(_scaled_int(28, self._scale))
        source_button.setCheckable(True)
        source_button.setToolTip("Show or hide the raw HTML source")
        source_button.clicked.connect(self._toggle_source_view)
        self.source_button = source_button

        zoom_out_button = QPushButton("A-")
        zoom_out_button.setObjectName("secondaryButton")
        zoom_out_button.setFixedHeight(_scaled_int(28, self._scale))
        zoom_out_button.setToolTip("Zoom out the rendered preview")
        zoom_out_button.clicked.connect(lambda: self._zoom_preview(-1))

        zoom_reset_button = QPushButton("100%")
        zoom_reset_button.setObjectName("secondaryButton")
        zoom_reset_button.setFixedHeight(_scaled_int(28, self._scale))
        zoom_reset_button.setToolTip("Reset the preview zoom level")
        zoom_reset_button.clicked.connect(self._reset_zoom)

        zoom_in_button = QPushButton("A+")
        zoom_in_button.setObjectName("secondaryButton")
        zoom_in_button.setFixedHeight(_scaled_int(28, self._scale))
        zoom_in_button.setToolTip("Zoom in the rendered preview")
        zoom_in_button.clicked.connect(lambda: self._zoom_preview(1))

        for button in (reload_button, source_button, zoom_out_button, zoom_reset_button, zoom_in_button):
            header_row.addWidget(button)

        close_button = QPushButton("Close")
        close_button.setObjectName("secondaryButton")
        close_button.setFixedHeight(_scaled_int(28, self._scale))
        close_button.clicked.connect(self.close)
        header_row.addWidget(close_button)
        card_layout.addLayout(header_row)

        if source_label:
            meta_label = QLabel(source_label)
            meta_label.setObjectName("previewMeta")
            meta_label.setWordWrap(True)
            card_layout.addWidget(meta_label)

        self.preview_browser = QTextBrowser()
        self.preview_browser.setObjectName("previewBrowser")
        self.preview_browser.setOpenExternalLinks(True)
        self.preview_browser.setHtml(html)
        self._base_font = self.preview_browser.font()
        self.preview_browser.document().setDefaultFont(self._base_font)
        card_layout.addWidget(self.preview_browser, 1)

        self.source_view = QTextEdit()
        self.source_view.setObjectName("sourceEditor")
        self.source_view.setReadOnly(True)
        self.source_view.setPlainText(html)
        self.source_view.setVisible(False)
        self.source_view.setMinimumHeight(_scaled_int(180, self._scale))
        card_layout.addWidget(self.source_view)

        layout.addWidget(card)
        self.resize(_scaled_int(920, self._scale), _scaled_int(680, self._scale))

    def _reload_preview(self) -> None:
        self.preview_browser.setHtml(self._source_html)
        self.source_view.setPlainText(self._source_html)

    def _toggle_source_view(self, checked: bool) -> None:
        self._source_visible = checked
        self.source_view.setVisible(checked)

    def _zoom_preview(self, step: int) -> None:
        if step > 0:
            self.preview_browser.zoomIn(step)
        elif step < 0:
            self.preview_browser.zoomOut(abs(step))

    def _reset_zoom(self) -> None:
        self.preview_browser.setFont(self._base_font)
        self.preview_browser.document().setDefaultFont(self._base_font)
        self.preview_browser.setHtml(self._source_html)
        self.source_view.setPlainText(self._source_html)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None:
            self.adjustSize()
            parent_center = parent.frameGeometry().center()
            self.move(
                parent_center.x() - self.width() // 2,
                parent_center.y() - self.height() // 2,
            )

class LoginPage(QWidget):
    def __init__(self, on_login, scale: float = 1.0):
        super().__init__()
        self.on_login = on_login
        self._scale = scale
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.error_label = QLabel("")
        self.login_button = QPushButton("Sign In")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(_scaled_int(18, self._scale), _scaled_int(18, self._scale), _scaled_int(18, self._scale), _scaled_int(18, self._scale))
        root.setSpacing(0)

        root.addStretch()

        shell = QFrame()
        shell.setObjectName("loginShell")
        shell.setMaximumWidth(_scaled_int(480, self._scale))
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(_scaled_int(22, self._scale), _scaled_int(22, self._scale), _scaled_int(22, self._scale), _scaled_int(22, self._scale))
        shell_layout.setSpacing(_scaled_int(12, self._scale))

        header = QHBoxLayout()
        header.setSpacing(_scaled_int(10, self._scale))
        logo = AnimatedLogoBadge(scale=self._scale)
        logo.setFixedSize(_scaled_int(48, self._scale), _scaled_int(48, self._scale))

        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        brand = QLabel("EzyMailer")
        brand.setObjectName("loginAppName")
        kicker = QLabel("Desktop email automation workspace")
        kicker.setObjectName("loginKicker")
        title_block.addWidget(brand)
        title_block.addWidget(kicker)

        header.addWidget(logo)
        header.addLayout(title_block)
        header.addStretch()

        intro = QLabel("Sign in to continue")
        intro.setObjectName("loginTitle")
        intro.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Local access for this build only.")
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.username_input.setPlaceholderText("Username")
        self.username_input.setText(DEFAULT_USERNAME)
        self.username_input.setToolTip("Enter the local login username")
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText(DEFAULT_PASSWORD)
        self.password_input.setToolTip("Enter the local login password")

        form.addRow("Username", self.username_input)
        form.addRow("Password", self.password_input)

        self.error_label.setObjectName("loginError")
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignCenter)

        self.login_button.setObjectName("primaryButton")
        self.login_button.setMinimumHeight(_scaled_int(38, self._scale))
        self.login_button.clicked.connect(lambda: self._attempt_login())
        self.login_button.setToolTip("Authenticate and open the workspace")

        footer = QLabel("Local login: admin / admin")
        footer.setObjectName("loginHint")
        footer.setAlignment(Qt.AlignCenter)
        footer.setWordWrap(True)

        shell_layout.addLayout(header)
        shell_layout.addWidget(intro)
        shell_layout.addWidget(subtitle)
        shell_layout.addLayout(form)
        shell_layout.addWidget(self.error_label)
        shell_layout.addWidget(self.login_button)
        shell_layout.addWidget(footer)

        root.addWidget(shell, alignment=Qt.AlignHCenter)
        root.addStretch()

        self.username_input.returnPressed.connect(self._attempt_login)
        self.password_input.returnPressed.connect(self._attempt_login)

    def _set_busy(self, busy: bool) -> None:
        self.username_input.setEnabled(not busy)
        self.password_input.setEnabled(not busy)
        self.login_button.setEnabled(not busy)
        self.login_button.setText("Signing In..." if busy else "Sign In")
        if busy:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    def _attempt_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.error_label.setText("Please enter both a username and password.")
            return

        self.error_label.setText("")
        self._set_busy(True)
        QApplication.processEvents()
        try:
            payload = api_login(username, password, timeout=5.0)
        except urllib.error.HTTPError as exc:
            message = "The username or password is incorrect."
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
                message = str(error_payload.get("error", message))
            except Exception:
                pass
            self.error_label.setText(message)
            return
        except Exception:
            self.error_label.setText("Unable to reach the local login API.")
            return
        finally:
            self._set_busy(False)

        if not payload.get("ok"):
            self.error_label.setText(str(payload.get("error", "Login failed.")))
            return

        user = payload.get("user") or {}
        self.on_login(str(user.get("username", username)), str(payload.get("access_token", "")))


class DashboardPage(QWidget):
    def __init__(self, state: AppState, on_logout, notify, scale: float = 1.0):
        super().__init__()
        self.state = state
        self.on_logout = on_logout
        self.notify = notify
        self._scale = scale
        self.session_list = QListWidget()
        self.window_spin = QSpinBox()
        self.incognito_button = QPushButton("Incognito")
        self.normal_button = QPushButton("Normal Mode")
        self.normal_message_button = QPushButton("Plain Text")
        self.html_message_button = QPushButton("HTML Body")
        self.data_summary_labels: dict[str, QLabel] = {}
        self.subject_drafts_list = QListWidget()
        self.subject_toggle_button = QPushButton("More")
        self.subject_new_button = QPushButton("New Subject")
        self.subject_save_button = QPushButton("Save Subject")
        self.subject_delete_button = QPushButton("Delete Subject")
        self.subject_refresh_button = QPushButton("Refresh")
        self.subject_count_label = QLabel("0")
        self.body_tabs = QTabWidget()
        self.body_add_button = QPushButton("+")
        self.body_upload_button = QPushButton("Upload")
        self.body_refresh_button = QPushButton("Refresh")
        self.pending_emails_editor = QTextEdit()
        self.subject_input = QLineEdit()
        self.body_editor = QTextEdit()
        self.html_message_editor = QTextEdit()
        self.html_editor = QTextEdit()
        self.send_log_view = QTextEdit()
        self.activity_log_view = QTextEdit()
        self.progress_bar = QProgressBar()
        self.active_windows_value = QLabel("0")
        self.launch_preset_label = QLabel("Default")
        self.custom1_input = QLineEdit()
        self.custom2_input = QLineEdit()
        self.custom_url_input = QLineEdit()
        self.proxy_input = QLineEdit()
        self.sender_limit = QSpinBox()
        self.delay_from = QDoubleSpinBox()
        self.delay_to = QDoubleSpinBox()
        self.retry_count = QSpinBox()
        self.ai_provider_combo = QComboBox()
        self.ai_api_key_input = QLineEdit()
        self.ai_connect_button = QPushButton("Connect")
        self.ai_status_label = QLabel("Not connected")
        self.ai_model_combo = QComboBox()
        self._available_ai_models: list[str] = []
        self.window_mode_group = QButtonGroup(self)
        self.delay_type_group = QButtonGroup(self)
        self.send_order_group = QButtonGroup(self)
        self.body_mode_group = QButtonGroup(self)
        self._browser_watch_timer = QTimer(self)
        self._browser_watch_timer.setInterval(2000)
        self._browser_watch_timer.timeout.connect(self._sync_browser_session_states)
        self._subject_body_save_timer = QTimer(self)
        self._subject_body_save_timer.setSingleShot(True)
        self._subject_body_save_timer.setInterval(700)
        self._subject_body_save_timer.timeout.connect(self._persist_subject_body_state)
        self._workspace_loading = False
        self._row_animations: list[QPropertyAnimation] = []
        self._floating_windows: list[QDialog] = []
        self._browser_sessions: list[BrowserSessionHandle] = []
        self._subject_list_visible = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        sidebar = self._build_sidebar()
        content = self._build_content()

        body.addWidget(sidebar)
        body.addWidget(content, 1)

        root.addLayout(body, 1)

        self.refresh()

    def _card(self, title: str, subtitle: str | None = None) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("panelCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("sectionTitle")
            layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("sectionSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        return card, layout

    def _section_title(self, title: str, subtitle: str | None = None) -> QWidget:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("sectionSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        return frame

    def _tab_scroll(self, content: QWidget) -> QScrollArea:
        content.setObjectName("tabPage")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("tabScroll")
        scroll.setWidget(content)
        return scroll

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(_scaled_int(300, self._scale))
        sidebar.setMaximumWidth(_scaled_int(320, self._scale))

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale))
        layout.setSpacing(_scaled_int(10, self._scale))

        launch_card, launch_layout = self._card("Browser Session Controls")
        self.window_spin.setRange(1, 99)
        self.window_spin.setValue(self.state.window_count)
        self.window_spin.setObjectName("windowSpin")
        self.window_spin.valueChanged.connect(self._window_count_changed)

        launch_row = QHBoxLayout()
        launch_row.setSpacing(8)

        launch_button = QPushButton("Start Browser")
        launch_button.setObjectName("primaryButton")
        launch_button.clicked.connect(lambda: self._handle_launch())
        launch_button.setToolTip("Launch browser windows for the selected session count")

        pause_button = QPushButton("Pause")
        pause_button.setObjectName("warningButton")
        pause_button.clicked.connect(lambda: self._handle_pause())
        pause_button.setToolTip("Pause the current browser session workflow")

        reset_button = QPushButton("Reset")
        reset_button.setObjectName("dangerButton")
        reset_button.clicked.connect(lambda: self._handle_reset())
        reset_button.setToolTip("Reset browser sessions and launch settings")

        launch_layout.addWidget(self._labeled_value_row("Windows", self.window_spin))
        launch_row.addWidget(launch_button)
        launch_row.addWidget(pause_button)
        launch_row.addWidget(reset_button)
        launch_layout.addLayout(launch_row)

        quick_row = QHBoxLayout()
        default_button = QPushButton("Default")
        default_button.setObjectName("secondaryButton")
        tile_button = QPushButton("Layout")
        tile_button.setObjectName("secondaryButton")
        clear_button = QPushButton("Clear")
        clear_button.setObjectName("secondaryButton")
        default_button.clicked.connect(lambda: self._set_launch_preset("Default"))
        tile_button.clicked.connect(lambda: self._set_launch_preset("Layout"))
        clear_button.clicked.connect(lambda: self._set_launch_preset(""))
        default_button.setToolTip("Restore the default launch preset")
        tile_button.setToolTip("Apply a layout-style launch preset")
        clear_button.setToolTip("Clear the preset selection")
        quick_row.addWidget(default_button)
        quick_row.addWidget(tile_button)
        quick_row.addWidget(clear_button)
        launch_layout.addLayout(quick_row)
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset"))
        self.launch_preset_label.setObjectName("windowPill")
        preset_row.addWidget(self.launch_preset_label)
        preset_row.addStretch()
        launch_layout.addLayout(preset_row)

        mode_card, mode_layout = self._card("Browser Mode", "Choose how sessions should open.")
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        self._configure_segmented_button(self.incognito_button, checked=True)
        self._configure_segmented_button(self.normal_button)
        mode_group.addButton(self.incognito_button)
        mode_group.addButton(self.normal_button)
        self.incognito_button.clicked.connect(lambda: self._set_browser_mode("Incognito"))
        self.normal_button.clicked.connect(lambda: self._set_browser_mode("Normal"))
        self.incognito_button.setToolTip("Open browser windows in private browsing mode")
        self.normal_button.setToolTip("Open browser windows in normal mode")
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.incognito_button)
        mode_row.addWidget(self.normal_button)
        mode_layout.addLayout(mode_row)

        sessions_card, sessions_layout = self._card("Active Sessions", "Open browser windows and their current state.")
        self.session_list.setObjectName("sessionList")
        self.session_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sessions_layout.addWidget(self.session_list)

        activity_card, activity_layout = self._card("Activity Log", "Recent actions and workflow updates.")
        self.activity_log_view.setObjectName("activityList")
        self.activity_log_view.setReadOnly(True)
        self.activity_log_view.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.activity_log_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        activity_layout.addWidget(self.activity_log_view)

        blast_button = QPushButton("Start Campaign")
        blast_button.setObjectName("blastButton")
        blast_button.clicked.connect(lambda: self._start_blast())
        blast_button.setToolTip("Start the main send workflow")

        layout.addWidget(launch_card)
        layout.addWidget(mode_card)
        layout.addWidget(sessions_card, 2)
        layout.addWidget(activity_card, 2)
        layout.addWidget(blast_button)

        return sidebar

    def _build_content(self) -> QWidget:
        content = QFrame()
        content.setObjectName("contentArea")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(_scaled_int(8, self._scale), _scaled_int(8, self._scale), _scaled_int(8, self._scale), _scaled_int(8, self._scale))
        layout.setSpacing(_scaled_int(8, self._scale))

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.addTab(self._build_data_tab(), "Data")
        self.tabs.addTab(self._build_subject_body_tab(), "Subject + Body")
        self.tabs.addTab(self._build_html_content_tab(), "Content")
        self.tabs.addTab(self._build_settings_tab(), "Settings")
        self.tabs.addTab(self._build_tags_tab(), "Tags")
        self.tabs.addTab(self._build_blaster_tab(), "Campaign")
        for index, tip in enumerate(
            [
                "Customer database and pending email list",
                "Subject and message composition",
                "HTML content and attachment setup",
                "Sending and runtime settings",
                "Dynamic tag management",
                "Launch and progress controls",
            ]
        ):
            self.tabs.setTabToolTip(index, tip)

        layout.addWidget(self.tabs)
        return content

    def _build_data_tab(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setSpacing(_scaled_int(10, self._scale))

        header = self._section_title("CUSTOMER EMAILS")
        page_layout.addWidget(header)

        self.pending_emails_editor.setPlaceholderText("Paste email addresses here, one per line...")
        self.pending_emails_editor.setObjectName("bodyEditor")
        self.pending_emails_editor.setMinimumHeight(_scaled_int(360, self._scale))
        self.pending_emails_editor.setToolTip("Paste recipient email addresses, one per line")
        self.pending_emails_editor.installEventFilter(self)
        page_layout.addWidget(self.pending_emails_editor, 1)

        filter_card, filter_layout = self._card(
            "EMAIL DOMAIN FILTER", "Choose whether to accept only Gmail addresses or allow all domains and aliases."
        )
        filter_row = QHBoxLayout()
        self.standard_email_radio = QRadioButton("Gmail only (@gmail.com)")
        self.mix_email_radio = QRadioButton("All domains and aliases")
        self.standard_email_radio.setChecked(True)
        self.standard_email_radio.setToolTip("Accept only Gmail addresses")
        self.mix_email_radio.setToolTip("Allow all domains and aliases")
        filter_row.addWidget(self.standard_email_radio)
        filter_row.addWidget(self.mix_email_radio)
        filter_row.addStretch()
        filter_layout.addLayout(filter_row)

        actions_row = QHBoxLayout()
        load_button = QPushButton("Load from File")
        load_button.setObjectName("secondaryButton")
        clear_button = QPushButton("Clear List")
        clear_button.setObjectName("secondaryButton")
        validate_button = QPushButton("Validate and Count")
        validate_button.setObjectName("primaryButton")
        load_button.setToolTip("Load recipient emails from a file")
        clear_button.setToolTip("Clear the current recipient list")
        validate_button.setToolTip("Validate the list and count the results")
        load_button.clicked.connect(self._load_pending_emails_from_file)
        clear_button.clicked.connect(lambda: self._clear_pending_emails())
        validate_button.clicked.connect(self._validate_pending_emails)
        actions_row.addWidget(load_button)
        actions_row.addWidget(clear_button)
        actions_row.addWidget(validate_button)
        actions_row.addStretch()
        filter_layout.addLayout(actions_row)

        counts_row = QHBoxLayout()
        for label_text in ("Total", "Valid", "Invalid", "Duplicates"):
            value = QLabel("0")
            value.setObjectName("countValue")
            self.data_summary_labels[label_text.lower()] = value
            card = QFrame()
            card.setObjectName("miniStat")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(_scaled_int(10, self._scale), _scaled_int(8, self._scale), _scaled_int(10, self._scale), _scaled_int(8, self._scale))
            stat_label = QLabel(label_text)
            stat_label.setObjectName("miniStatLabel")
            card_layout.addWidget(stat_label)
            card_layout.addWidget(value)
            counts_row.addWidget(card)
        counts_row.addStretch()
        filter_layout.addLayout(counts_row)

        page_layout.addWidget(filter_card)
        return self._tab_scroll(page)

    def _build_subject_body_tab(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setSpacing(_scaled_int(10, self._scale))

        subject_card, subject_layout = self._card("SUBJECT + BODY", "Keep the active subject visible. Use More to manage all subjects.")
        subject_box = QVBoxLayout()
        subject_box.setSpacing(_scaled_int(8, self._scale))

        subject_row = QHBoxLayout()
        subject_label = QLabel("Subject")
        subject_label.setObjectName("fieldLabel")
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Type your subject here")
        self.subject_input.setToolTip("Edit the active subject")
        self.subject_toggle_button.setObjectName("secondaryButton")
        self.subject_toggle_button.setToolTip("Open the subject manager modal")
        self.subject_toggle_button.clicked.connect(self._open_subject_manager)
        subject_row.addWidget(subject_label)
        subject_row.addWidget(self.subject_input, 1)
        subject_row.addWidget(self.subject_toggle_button)
        subject_box.addLayout(subject_row)

        subject_toolbar = QHBoxLayout()
        self.subject_new_button.setObjectName("secondaryButton")
        self.subject_save_button.setObjectName("primaryButton")
        self.subject_delete_button.setObjectName("dangerButton")
        self.subject_refresh_button.setObjectName("secondaryButton")
        self.subject_new_button.clicked.connect(self._new_subject_draft)
        self.subject_save_button.clicked.connect(self._save_subject_draft)
        self.subject_delete_button.clicked.connect(self._delete_subject_draft)
        self.subject_refresh_button.clicked.connect(self.load_user_workspace)
        self.subject_new_button.setToolTip("Start a new subject")
        self.subject_save_button.setToolTip("Save the active subject")
        self.subject_delete_button.setToolTip("Remove the selected subject")
        self.subject_refresh_button.setToolTip("Reload subjects from the local database")
        for button in (
            self.subject_new_button,
            self.subject_save_button,
            self.subject_delete_button,
            self.subject_refresh_button,
        ):
            subject_toolbar.addWidget(button)
        subject_toolbar.addStretch()
        subject_box.addLayout(subject_toolbar)
        subject_box.addWidget(self.subject_count_label)
        subject_layout.addLayout(subject_box)

        body_card, body_layout = self._card("BODY TABS", "Each body opens in a closable browser-style tab.")
        body_header = QHBoxLayout()
        body_title = QLabel("Bodies")
        body_title.setObjectName("sectionSubtitle")
        body_header.addWidget(body_title)
        body_header.addStretch()
        self.body_add_button.setObjectName("secondaryButton")
        self.body_add_button.setFixedWidth(_scaled_int(34, self._scale))
        self.body_add_button.setToolTip("Add a new body")
        self.body_add_button.clicked.connect(self._new_body_draft_tab)
        self.body_upload_button.setObjectName("secondaryButton")
        self.body_upload_button.clicked.connect(self._upload_body_files)
        self.body_upload_button.setToolTip("Upload CSV text bodies or HTML body files")
        self.body_refresh_button.setObjectName("secondaryButton")
        self.body_refresh_button.clicked.connect(self.load_user_workspace)
        self.body_refresh_button.setToolTip("Reload bodies from the local database")
        body_header.addWidget(self.body_add_button)
        body_header.addWidget(self.body_upload_button)
        body_header.addWidget(self.body_refresh_button)
        body_layout.addLayout(body_header)

        self.body_tabs.setTabsClosable(True)
        self.body_tabs.setMovable(True)
        self.body_tabs.setDocumentMode(True)
        self.body_tabs.setUsesScrollButtons(True)
        self.body_tabs.tabCloseRequested.connect(self._remove_body_draft_tab)
        self.body_tabs.currentChanged.connect(self._on_body_tab_changed)
        self.body_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        body_layout.addWidget(self.body_tabs, 1)

        page_layout.addWidget(subject_card)
        page_layout.addWidget(body_card, 1)
        self.subject_input.textChanged.connect(lambda _text: self._schedule_subject_body_save())
        return self._tab_scroll(page)

    def _build_html_content_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(_scaled_int(10, self._scale))

        header = self._section_title("HTML CONTENT EDITOR")
        layout.addWidget(header)

        status_banner = QFrame()
        status_banner.setObjectName("panelCard")
        status_layout = QHBoxLayout(status_banner)
        status_layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(10, self._scale), _scaled_int(12, self._scale), _scaled_int(10, self._scale))
        status_label = QLabel("No active windows")
        status_label.setObjectName("placeholderText")
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        layout.addWidget(status_banner)

        self.html_editor.setObjectName("bodyEditor")
        self.html_editor.setPlaceholderText("<!-- Paste your HTML template here... -->")
        self.html_editor.setToolTip("Paste the HTML template here")
        self.html_editor.setPlainText(
            "<html>\n  <body style='font-family: Segoe UI; background:#0f172a; color:#e5eefc;'>\n    <h1>Email Campaign Title</h1>\n    <p>Hello {{first_name}}, welcome to the preview.</p>\n  </body>\n</html>"
        )
        self.html_editor.setMinimumHeight(_scaled_int(300, self._scale))
        layout.addWidget(self.html_editor, 1)

        footer_row = QHBoxLayout()
        preview_html = QPushButton("Preview HTML")
        preview_html.setObjectName("primaryButton")
        convert_check = QCheckBox("Convert to file")
        convert_check.setChecked(True)
        convert_file = QPushButton("Export to file")
        convert_file.setObjectName("secondaryButton")
        convert_preview = QPushButton("Export and Preview")
        convert_preview.setObjectName("primaryButton")
        preview_html.setToolTip("Preview the HTML content")
        convert_check.setToolTip("Enable export to a file")
        convert_file.setToolTip("Open the file export options")
        convert_preview.setToolTip("Export the HTML and preview the result")
        preview_html.clicked.connect(lambda: self._preview_html_content())
        convert_file.clicked.connect(lambda: self._open_output_options_dialog())
        convert_preview.clicked.connect(lambda: self._open_output_options_dialog(preview=True))
        footer_row.addWidget(preview_html)
        footer_row.addWidget(convert_check)
        footer_row.addWidget(convert_file)
        footer_row.addWidget(convert_preview)
        footer_row.addStretch()
        layout.addLayout(footer_row)

        attach_card, attach_layout = self._card("ATTACHMENT", "Configure file naming and upload actions.")
        auto_radio = QRadioButton("Auto-generated (random unique name)")
        auto_radio.setChecked(True)
        auto_radio.setToolTip("Generate a random attachment name")
        attach_layout.addWidget(auto_radio)

        attach_actions = QHBoxLayout()
        upload_button = QPushButton("Upload Custom Attachment")
        upload_button.setObjectName("secondaryButton")
        remove_button = QPushButton("Remove")
        remove_button.setObjectName("dangerButton")
        upload_button.setToolTip("Upload a custom attachment")
        remove_button.setToolTip("Remove the selected attachment")
        upload_button.clicked.connect(lambda: self._log_action("Uploaded attachment"))
        remove_button.clicked.connect(lambda: self._log_action("Removed attachment"))
        attach_actions.addWidget(upload_button)
        attach_actions.addWidget(remove_button)
        attach_actions.addStretch()
        attach_layout.addLayout(attach_actions)

        attachment_hint = QLabel("PDFs, images, and other files can be attached later in the logic phase.")
        attachment_hint.setObjectName("sectionHint")
        attachment_hint.setWordWrap(True)
        attach_layout.addWidget(attachment_hint)

        layout.addWidget(attach_card)
        return self._tab_scroll(page)

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(_scaled_int(10, self._scale))

        header = self._section_title("SENDING SETTINGS")
        layout.addWidget(header)

        send_card, send_layout = self._card("Sending Settings", "Tune the execution behavior for each sender.")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        self.sender_limit.setRange(1, 5000)
        self.sender_limit.setValue(500)
        self.sender_limit.setObjectName("windowSpin")
        self.sender_limit.setToolTip("Set the maximum emails per sender")
        self.delay_from.setDecimals(1)
        self.delay_from.setRange(0.0, 60.0)
        self.delay_from.setSingleStep(0.1)
        self.delay_from.setValue(0.5)
        self.delay_to.setDecimals(1)
        self.delay_to.setRange(0.0, 60.0)
        self.delay_to.setSingleStep(0.1)
        self.delay_to.setValue(1.0)
        self.retry_count.setRange(0, 20)
        self.retry_count.setValue(3)
        self.delay_from.setToolTip("Minimum delay between emails")
        self.delay_to.setToolTip("Maximum delay between emails")
        self.retry_count.setToolTip("Number of retry attempts for failed sends")

        form.addRow("Per-sender limit", self.sender_limit)
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay between emails"))
        delay_row.addWidget(self.delay_from)
        delay_row.addWidget(QLabel("to"))
        delay_row.addWidget(self.delay_to)
        delay_row.addWidget(QLabel("seconds (random range)"))
        delay_holder = QFrame()
        delay_holder.setLayout(delay_row)
        form.addRow(delay_holder)
        send_layout.addLayout(form)

        delay_type_row = QHBoxLayout()
        fixed_radio = QRadioButton("Fixed")
        random_radio = QRadioButton("Random range")
        human_radio = QRadioButton("Human-like pattern")
        random_radio.setChecked(True)
        fixed_radio.setToolTip("Use the same delay for every send")
        random_radio.setToolTip("Use a random delay within the range")
        human_radio.setToolTip("Use a human-like delay pattern")
        self.delay_type_group = QButtonGroup(self)
        self.delay_type_group.setExclusive(True)
        for button in (fixed_radio, random_radio, human_radio):
            self.delay_type_group.addButton(button)
            delay_type_row.addWidget(button)
        delay_type_row.addStretch()
        send_layout.addWidget(self._labeled_value_row("Delay type", self._wrap_layout(delay_type_row)))

        retry_row = QHBoxLayout()
        retry_enable = QCheckBox("Enable")
        retry_enable.setChecked(True)
        retry_enable.setToolTip("Enable retry handling for failed sends")
        retry_row.addWidget(retry_enable)
        retry_row.addWidget(self.retry_count)
        retry_row.addWidget(QLabel("retries"))
        retry_row.addStretch()
        send_layout.addWidget(self._labeled_value_row("Retry failed sends", self._wrap_layout(retry_row)))

        order_row = QHBoxLayout()
        seq_radio = QRadioButton("Sequential")
        rand_radio = QRadioButton("Random shuffle")
        seq_radio.setChecked(True)
        seq_radio.setToolTip("Send in list order")
        rand_radio.setToolTip("Shuffle the send order")
        self.send_order_group = QButtonGroup(self)
        self.send_order_group.setExclusive(True)
        for button in (seq_radio, rand_radio):
            self.send_order_group.addButton(button)
            order_row.addWidget(button)
        order_row.addStretch()
        send_layout.addWidget(self._labeled_value_row("Email send order", self._wrap_layout(order_row)))

        window_mode_row = QHBoxLayout()
        parallel_radio = QRadioButton("Parallel (all windows at once)")
        sequential_window_radio = QRadioButton("Sequential (one window at a time)")
        parallel_radio.setChecked(True)
        parallel_radio.setToolTip("Launch and send in parallel")
        sequential_window_radio.setToolTip("Rotate through windows one at a time")
        self.window_mode_group = QButtonGroup(self)
        self.window_mode_group.setExclusive(True)
        for button in (parallel_radio, sequential_window_radio):
            self.window_mode_group.addButton(button)
            window_mode_row.addWidget(button)
        window_mode_row.addStretch()
        send_layout.addWidget(self._labeled_value_row("Window send mode", self._wrap_layout(window_mode_row)))

        layout.addWidget(send_card)

        proxy_card, proxy_layout = self._card("ADVANCED SETTINGS (PROXIES)", "Optional runtime safeguards.")
        proxy_row = QHBoxLayout()
        proxy_enable = QCheckBox("Enable Proxy (IP:Port per window)")
        self.proxy_input.setPlaceholderText("Proxy list or endpoint configuration")
        proxy_enable.setToolTip("Route sessions through a proxy per window")
        self.proxy_input.setToolTip("Enter proxy addresses or endpoint settings")
        proxy_row.addWidget(proxy_enable)
        proxy_row.addWidget(self.proxy_input, 1)
        proxy_layout.addLayout(proxy_row)
        layout.addWidget(proxy_card)

        startup_card, startup_layout = self._card("ADDITIONAL STARTUP TABS", "Open custom URLs when each session launches.")
        startup_checkbox = QCheckBox("Open custom URL in a new tab on startup")
        self.custom_url_input.setPlaceholderText("Custom URL")
        startup_checkbox.setToolTip("Open a custom page when each session starts")
        self.custom_url_input.setToolTip("Enter the startup URL to open")
        startup_layout.addWidget(startup_checkbox)
        startup_layout.addWidget(self.custom_url_input)
        layout.addWidget(startup_card)

        ai_card, ai_layout = self._card("AI ASSISTANT", "Connect an AI provider to unlock model selection.")
        ai_form = QFormLayout()
        ai_form.setLabelAlignment(Qt.AlignLeft)
        ai_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        ai_form.setHorizontalSpacing(_scaled_int(16, self._scale))
        ai_form.setVerticalSpacing(_scaled_int(12, self._scale))

        self.ai_provider_combo.clear()
        self.ai_provider_combo.addItems(["ChatGPT", "Claude", "DeepSeek"])
        self.ai_provider_combo.setCurrentText(self.state.ai_provider)
        self.ai_provider_combo.setToolTip("Select the AI provider")
        self.ai_provider_combo.currentTextChanged.connect(lambda _value: self._on_ai_provider_changed())
        self.ai_provider_combo.setMinimumWidth(_scaled_int(240, self._scale))
        self.ai_provider_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.ai_api_key_input.setPlaceholderText("Enter API key")
        self.ai_api_key_input.setEchoMode(QLineEdit.Password)
        self.ai_api_key_input.setToolTip("Enter the provider API key")
        self.ai_api_key_input.setMinimumWidth(_scaled_int(240, self._scale))
        self.ai_api_key_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.ai_model_combo.setEnabled(False)
        self.ai_model_combo.setToolTip("Choose a model after connecting")
        self.ai_model_combo.currentTextChanged.connect(lambda _value: self._on_ai_model_changed())
        self.ai_model_combo.setMinimumWidth(_scaled_int(240, self._scale))
        self.ai_model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.ai_connect_button.setObjectName("primaryButton")
        self.ai_connect_button.clicked.connect(lambda: self._connect_ai_provider())
        self.ai_connect_button.setToolTip("Validate the API key and connect")
        self.ai_connect_button.setMinimumWidth(_scaled_int(140, self._scale))
        self.ai_connect_button.setCursor(Qt.PointingHandCursor)

        self.ai_status_label.setObjectName("windowPill")
        self.ai_status_label.setAlignment(Qt.AlignCenter)
        self.ai_status_label.setMinimumHeight(_scaled_int(32, self._scale))
        self.ai_status_label.setMinimumWidth(_scaled_int(140, self._scale))
        self.ai_status_label.setText("Not connected")

        ai_form.addRow("Provider", self.ai_provider_combo)
        ai_form.addRow("API key", self.ai_api_key_input)
        ai_form.addRow("", self.ai_connect_button)
        ai_form.addRow("Model", self.ai_model_combo)
        ai_form.addRow("Status", self.ai_status_label)
        ai_layout.addLayout(ai_form)
        layout.addWidget(ai_card)

        save_button = QPushButton("Save Settings")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(lambda: self._log_action("Saved settings"))
        save_button.setToolTip("Save the current sending settings")
        layout.addWidget(save_button, alignment=Qt.AlignLeft)
        layout.addStretch()

        self._refresh_ai_models()
        self._sync_ai_connection_ui()

        return self._tab_scroll(page)

    def _refresh_ai_models(self) -> None:
        self.ai_model_combo.blockSignals(True)
        self.ai_model_combo.clear()
        self.ai_model_combo.addItems(self._available_ai_models)
        if self.state.ai_model and self.state.ai_model in self._available_ai_models:
            self.ai_model_combo.setCurrentText(self.state.ai_model)
        elif self._available_ai_models:
            self.ai_model_combo.setCurrentIndex(0)
            self.state.ai_model = self.ai_model_combo.currentText()
        self.ai_model_combo.blockSignals(False)

    def _sync_ai_connection_ui(self) -> None:
        connected = self.state.ai_connected
        self.ai_model_combo.setEnabled(connected and bool(self._available_ai_models))
        self.ai_connect_button.setText("Reconnect" if connected else "Connect")
        self.ai_connect_button.setEnabled(True)
        if connected:
            self.ai_status_label.setText("Connected")
            self.ai_status_label.setStyleSheet(
                "QLabel { background:#12351e; color:#7dff9a; border:1px solid #1e7a3a; border-radius:8px; padding:4px 10px; font-weight:700; }"
            )
        else:
            self.ai_status_label.setText("Not connected")
            self.ai_status_label.setStyleSheet(
                "QLabel { background:#2a1d1d; color:#f0a0a0; border:1px solid #7a3131; border-radius:8px; padding:4px 10px; font-weight:700; }"
            )
        self.ai_model_combo.blockSignals(True)
        if connected and self.state.ai_model:
            index = self.ai_model_combo.findText(self.state.ai_model)
            if index >= 0:
                self.ai_model_combo.setCurrentIndex(index)
        self.ai_model_combo.blockSignals(False)

    def _set_ai_busy(self, busy: bool) -> None:
        self.ai_provider_combo.setEnabled(not busy)
        self.ai_api_key_input.setEnabled(not busy)
        self.ai_model_combo.setEnabled((not busy) and self.state.ai_connected and bool(self._available_ai_models))
        self.ai_connect_button.setEnabled(not busy)
        if busy:
            self.ai_connect_button.setText("Connecting...")
            self.ai_connect_button.setStyleSheet(
                "QPushButton#primaryButton { background:#a87917; color:#ffffff; border:none; }"
            )
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            self.ai_connect_button.setStyleSheet("")
            QApplication.restoreOverrideCursor()

    def _on_ai_provider_changed(self) -> None:
        self.state.ai_provider = self.ai_provider_combo.currentText() or "ChatGPT"
        self.state.ai_connected = False
        self.state.ai_model = ""
        self._available_ai_models = []
        self._refresh_ai_models()
        self._sync_ai_connection_ui()
        self._log_action(f"AI provider selected: {self.state.ai_provider}")

    def _connect_ai_provider(self) -> None:
        provider = self.ai_provider_combo.currentText() or "ChatGPT"
        api_key = self.ai_api_key_input.text().strip()
        if not api_key:
            self.state.ai_connected = False
            self.state.ai_model = ""
            self._available_ai_models = []
            self._refresh_ai_models()
            self._sync_ai_connection_ui()
            self.notify("Enter an API key to connect")
            return

        self._set_ai_busy(True)
        QApplication.processEvents()
        self.state.ai_provider = provider
        self.state.ai_connected = False
        self.state.ai_model = ""
        self._available_ai_models = []
        self._refresh_ai_models()
        self._sync_ai_connection_ui()

        try:
            models = AIValidationWorker(provider, api_key)._fetch_models()
        except Exception as exc:
            self.state.ai_connected = False
            self.state.ai_model = ""
            self._available_ai_models = []
            self._refresh_ai_models()
            self._sync_ai_connection_ui()
            self._set_ai_busy(False)
            self._log_action(f"AI connection failed: {exc}")
            self.notify("AI connection failed")
            return

        self.state.ai_provider = provider
        self.state.ai_connected = True
        self._available_ai_models = models
        self._refresh_ai_models()
        if self._available_ai_models:
            if not self.state.ai_model or self.state.ai_model not in self._available_ai_models:
                self.state.ai_model = self._available_ai_models[0]
            self.ai_model_combo.setCurrentText(self.state.ai_model)
        self._sync_ai_connection_ui()
        self._set_ai_busy(False)
        self._log_action(f"Connected AI provider: {provider}")
        self.notify(f"{provider} connected")

    def _on_ai_model_changed(self) -> None:
        if not self.ai_model_combo.isEnabled():
            return
        self.state.ai_model = self.ai_model_combo.currentText().strip()
        if self.state.ai_model:
            self._log_action(f"AI model selected: {self.state.ai_model}")

    def _build_blaster_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(_scaled_int(10, self._scale))

        header = self._section_title("EMAIL BLASTING CONTROLS", "Send emails from all open Gmail windows.")
        layout.addWidget(header)

        controls_card, controls_layout = self._card("Active Gmail Windows")
        windows_row = QHBoxLayout()
        windows_row.addWidget(QLabel("Active Gmail Windows:"))
        self.active_windows_value.setObjectName("windowPill")
        self.active_windows_value.setToolTip("Count of active browser windows")
        windows_row.addWidget(self.active_windows_value)
        windows_row.addStretch()
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondaryButton")
        refresh_button.clicked.connect(lambda: self._log_action("Refreshed active Gmail windows"))
        refresh_button.setToolTip("Refresh the active Gmail window count")
        windows_row.addWidget(refresh_button)
        controls_layout.addLayout(windows_row)

        controls_layout.addWidget(QLabel("Campaign Progress:"))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        controls_layout.addWidget(self.progress_bar)
        progress_text = QLabel("0 / 0 sent")
        progress_text.setObjectName("sectionHint")
        controls_layout.addWidget(progress_text)
        layout.addWidget(controls_card)

        start_button = QPushButton("Start Campaign")
        start_button.setObjectName("blastButton")
        start_button.setMinimumHeight(_scaled_int(54, self._scale))
        start_button.clicked.connect(lambda: self._log_action("Start Campaign clicked"))
        start_button.setToolTip("Start the email sending workflow")
        layout.addWidget(start_button)

        log_card, log_layout = self._card("SEND LOG")
        self.send_log_view.setReadOnly(True)
        self.send_log_view.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.send_log_view.setObjectName("activityList")
        log_layout.addWidget(self.send_log_view)
        layout.addWidget(log_card, 1)

        return self._tab_scroll(page)

    def _build_tags_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(_scaled_int(10, self._scale))

        header = self._section_title("DYNAMIC TAGS", "Use these tags in Subject or Body. They generate random values when sending.")
        layout.addWidget(header)

        grid_card, grid_layout = self._card("", None)
        grid_layout.setContentsMargins(_scaled_int(6, self._scale), _scaled_int(6, self._scale), _scaled_int(6, self._scale), _scaled_int(6, self._scale))
        tag_scroll = QScrollArea()
        tag_scroll.setWidgetResizable(True)
        tag_scroll.setFrameShape(QFrame.NoFrame)
        tag_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        tag_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tag_scroll.setMaximumHeight(_scaled_int(430, self._scale))

        tag_host = QWidget()
        tag_host_layout = QGridLayout(tag_host)
        tag_host_layout.setContentsMargins(0, 0, 0, 0)
        tag_host_layout.setSpacing(_scaled_int(8, self._scale))
        samples = [
            ("VOIS", "$random4", "4 char alphanumeric uppercase"),
            ("V3EAJO", "$random6", "6 char alphanumeric uppercase"),
            ("0G2639Q", "$random8", "8 char alphanumeric uppercase"),
            ("I51VNI166P", "$random10", "10 char alphanumeric uppercase"),
            ("I520Z0QQQ7CN", "$random12", "12 char alphanumeric uppercase"),
            ("VIK", "$word3", "3-letter uppercase word"),
            ("POPE", "$word4", "4-letter word pattern"),
            ("FABEQ", "$word5", "5-letter uppercase word"),
            ("7575", "$num4", "4 digit number"),
            ("640296", "$num6", "6 digit number"),
            ("45250809", "$num8", "8 digit number"),
            ("1-800-181-7889", "$phone", "Phone-style sample"),
            ("QLRZ", "$word4a", "Alternative 4-letter word"),
            ("MOTION", "$word6", "6-letter uppercase word"),
            ("7A4F", "$mix4", "Mixed 4-character token"),
            ("DX8M2P", "$mix6", "Mixed 6-character token"),
            ("0314", "$day4", "4 digit day code"),
            ("202608", "$ym6", "Year-month code"),
            ("94-221-88", "$id9", "Structured numeric token"),
            ("support@ezymailer.com", "$email", "Email address sample"),
            ("https://ezymailer.app", "$url", "Website URL sample"),
            ("Alice Johnson", "$name", "Full name sample"),
            ("Seattle", "$city", "City sample"),
            ("hello-world", "$slug", "Slug sample"),
        ]
        for index, (title, token, description) in enumerate(samples):
            tag_host_layout.addWidget(self._tag_card(title, token, description), index // 3, index % 3)
        tag_scroll.setWidget(tag_host)
        grid_layout.addWidget(tag_scroll)
        layout.addWidget(grid_card)

        actions_row = QHBoxLayout()
        regenerate_button = QPushButton("Regenerate All")
        regenerate_button.setObjectName("secondaryButton")
        ai_button = QPushButton("Generate with AI")
        ai_button.setObjectName("warningButton")
        reset_button = QPushButton("Reset to Default")
        reset_button.setObjectName("secondaryButton")
        regenerate_button.setToolTip("Regenerate all sample tag values")
        ai_button.setToolTip("Generate new tag ideas with AI")
        reset_button.setToolTip("Restore the default tag set")
        regenerate_button.clicked.connect(lambda: self._log_action("Regenerated tags"))
        ai_button.clicked.connect(lambda: self._log_action("Generated tags with AI"))
        reset_button.clicked.connect(lambda: self._log_action("Reset tags to default"))
        actions_row.addWidget(regenerate_button)
        actions_row.addWidget(ai_button)
        actions_row.addWidget(reset_button)
        actions_row.addStretch()
        layout.addLayout(actions_row)

        manual_card, manual_layout = self._card("MANUAL CUSTOM TAGS", "Values entered here replace $custom1 and $custom2.")
        manual_layout.addWidget(QLabel("For example, you can add a phone number, email address, or any other text."))
        self.custom1_input.setPlaceholderText("$custom1 =")
        self.custom2_input.setPlaceholderText("$custom2 =")
        self.custom1_input.setToolTip("Define the first manual custom tag value")
        self.custom2_input.setToolTip("Define the second manual custom tag value")
        manual_layout.addWidget(self._line_with_copy(self.custom1_input))
        manual_layout.addWidget(self._line_with_copy(self.custom2_input))
        layout.addWidget(manual_card)
        layout.addStretch()

        return self._tab_scroll(page)

    def _configure_segmented_button(self, button: QPushButton, checked: bool = False) -> None:
        button.setCheckable(True)
        button.setChecked(checked)
        button.setCursor(Qt.PointingHandCursor)

    def _labeled_value_row(self, label_text: str, widget: QWidget) -> QWidget:
        row = QFrame()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(_scaled_int(10, self._scale))

        label = QLabel(label_text)
        label.setObjectName("fieldLabel")
        row_layout.addWidget(label)
        row_layout.addWidget(widget, 1)
        return row

    def _wrap_layout(self, layout: QHBoxLayout) -> QWidget:
        holder = QFrame()
        holder.setLayout(layout)
        return holder

    def _line_with_copy(self, line_edit: QLineEdit) -> QWidget:
        row = QFrame()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(_scaled_int(10, self._scale))

        line_edit.setObjectName("searchInput")
        copy_button = QPushButton("Copy")
        copy_button.setObjectName("secondaryButton")
        copy_button.clicked.connect(lambda: self._log_action("Copied custom tag value"))
        line_edit.setToolTip("Edit the manual custom tag value")
        copy_button.setToolTip("Copy the manual custom tag value")
        row_layout.addWidget(line_edit, 1)
        row_layout.addWidget(copy_button)
        return row

    def _open_output_options_dialog(self, preview: bool = False) -> None:
        dialog = OutputOptionsDialog(self.window(), scale=self._scale)
        if dialog.exec() == QDialog.Accepted:
            self._log_action("Opened export options")
            if preview:
                self._log_action("Exported HTML and opened preview")
                self.notify("HTML export preview ready")
                self._preview_html_content(title="Converted HTML Preview")
            else:
                self.notify("Export options confirmed")

    def _wrap_text_as_html(self, text: str, subject: str = "") -> str:
        safe_subject = html.escape(subject.strip())
        safe_text = html.escape(text).replace("\n", "<br>")
        return f"""
        <html>
          <body style="margin:0; padding:24px; background:#1e1e1e; color:#d4d4d4; font-family:'Segoe UI Variable Text','Segoe UI',sans-serif;">
            <div style="max-width: 820px; margin: 0 auto;">
              {f'<div style="color:#569cd6; font-size:12px; letter-spacing:.4px; font-weight:700; text-transform:uppercase; margin-bottom:10px;">{safe_subject}</div>' if safe_subject else ''}
              <div style="white-space:normal; line-height:1.7; font-size:14px;">{safe_text}</div>
            </div>
          </body>
        </html>
        """

    def _build_preview_dialog(self, title: str, html_content: str, source_label: str) -> HtmlPreviewDialog:
        dialog = HtmlPreviewDialog(self.window(), title, html_content, source_label, scale=self._scale)
        self._floating_windows.append(dialog)
        dialog.finished.connect(lambda _result, d=dialog: self._remove_floating_window(d))
        dialog.destroyed.connect(lambda *_args, d=dialog: self._remove_floating_window(d))
        return dialog

    def _remove_floating_window(self, dialog: QDialog) -> None:
        if dialog in self._floating_windows:
            self._floating_windows.remove(dialog)

    def _preview_subject_body(self) -> None:
        subject = self.subject_input.text().strip() or "Subject Preview"
        current_body = self._current_body_widget()
        if current_body is not None:
            body_payload = current_body.payload()
            if body_payload["mode"] == "HTML Message":
                html_content = body_payload["html_text"].strip()
                source = "Previewing the HTML message content."
                if not html_content:
                    html_content = "<html><body style='background:#1e1e1e; color:#d4d4d4; font-family:Segoe UI;'>No HTML content available.</body></html>"
            else:
                body_text = body_payload["plain_text"].strip()
                source = "Previewing the plain-text message as HTML."
                if not body_text:
                    body_text = "No message body available."
                html_content = self._wrap_text_as_html(body_text, subject)
        else:
            html_content = "<html><body style='background:#1e1e1e; color:#d4d4d4; font-family:Segoe UI;'>No message body available.</body></html>"
            source = "No active body is available."

        dialog = self._build_preview_dialog("Message Preview", html_content, source)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._log_action("Opened message preview")
        self.notify("Message preview opened")

    def _preview_body_editor_html(self, widget: BodyDraftEditor | None) -> None:
        if widget is None or widget.mode_text() != "HTML Message":
            self.notify("Switch to HTML body first")
            return

        html_content = widget.html_editor.toPlainText().strip()
        if not html_content:
            self.notify("Add HTML content first")
            return

        title = widget.title_text() or "HTML Body Preview"
        dialog = self._build_preview_dialog(title, html_content, "Previewing the selected HTML body.")
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._log_action(f"Opened body preview: {title}")
        self.notify("Body preview opened")

    def _preview_html_content(self, title: str = "HTML Preview") -> None:
        html_content = self.html_editor.toPlainText().strip()
        if not html_content:
            html_content = "<html><body style='background:#1e1e1e; color:#d4d4d4; font-family:Segoe UI;'>No HTML template available.</body></html>"
        dialog = self._build_preview_dialog(
            title,
            html_content,
            "Previewing the HTML template in a separate window.",
        )
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._log_action(f"Opened {title.lower()}")
        self.notify("HTML preview opened")

    def _tag_card(self, title: str, token: str, description: str) -> QWidget:
        card = QFrame()
        card.setObjectName("panelCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale))
        layout.setSpacing(_scaled_int(6, self._scale))

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        token_label = QLabel(token)
        token_label.setObjectName("windowPill")
        header.addWidget(title_label)
        header.addStretch()
        header.addWidget(token_label)
        layout.addLayout(header)

        row = QHBoxLayout()
        token_value = QLabel(token)
        token_value.setObjectName("sectionSubtitle")
        remove_button = QPushButton("X")
        remove_button.setObjectName("dangerButton")
        remove_button.setFixedWidth(_scaled_int(36, self._scale))
        copy_button = QPushButton("Copy")
        copy_button.setObjectName("secondaryButton")
        copy_button.clicked.connect(lambda: self._log_action(f"Copied tag {token}"))
        remove_button.clicked.connect(lambda: self._log_action(f"Removed tag {token}"))
        token_value.setToolTip(f"Token value for {token}")
        remove_button.setToolTip(f"Remove {token} from the grid")
        copy_button.setToolTip(f"Copy {token} to clipboard")
        row.addWidget(token_value)
        row.addStretch()
        row.addWidget(remove_button)
        row.addWidget(copy_button)
        layout.addLayout(row)

        desc = QLabel(description)
        desc.setObjectName("sectionHint")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        return card

    def _set_browser_mode(self, mode: str) -> None:
        self.state.browser_mode = mode
        self.incognito_button.setChecked(mode == "Incognito")
        self.normal_button.setChecked(mode == "Normal")
        if self.state.username:
            try:
                upsert_setting(self.state.username, "browser_mode", mode)
            except Exception:
                pass
        self._log_action(f"Browser mode set to {mode}")
        self.notify(f"Browser mode changed to {mode}")

    def _set_body_mode(self, mode: str) -> None:
        self.state.body_mode = mode
        self.normal_message_button.setChecked(mode == "Normal Message")
        self.html_message_button.setChecked(mode == "HTML Message")
        current_body = self._current_body_widget()
        if current_body is not None:
            current_body.set_mode(mode)
        if self.state.username:
            try:
                upsert_setting(self.state.username, "body_mode", mode)
            except Exception:
                pass
        self._schedule_subject_body_save()
        label = "Plain Text" if mode == "Normal Message" else "HTML Body"
        self._log_action(f"Body mode set to {label}")
        self.notify(f"Body mode changed to {label}")

    def _set_launch_preset(self, preset: str | None) -> None:
        self.state.launch_preset = preset or ""
        label = preset if preset else "None"
        self.launch_preset_label.setText(label)
        if self.state.username:
            try:
                upsert_setting(self.state.username, "launch_preset", self.state.launch_preset)
            except Exception:
                pass
        self._log_action(f"Launch preset set to {label}")
        self.notify(f"Launch preset updated: {label}")

    def _window_count_changed(self, value: int) -> None:
        self.state.window_count = max(1, value)

    def _browser_binary(self) -> Path | None:
        candidates = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _browser_launch_rect(self, index: int, total: int) -> tuple[int, int, int, int]:
        screen = self.window().screen() or QApplication.primaryScreen()
        if screen is None:
            return (80, 80, 1280, 800)

        geometry = screen.availableGeometry()
        margin = _scaled_int(18, self._scale)
        gap = _scaled_int(14, self._scale)
        cols = max(1, ceil(sqrt(total)))
        rows = max(1, ceil(total / cols))

        usable_width = max(800, geometry.width() - (margin * 2) - (gap * (cols - 1)))
        usable_height = max(600, geometry.height() - (margin * 2) - (gap * (rows - 1)))
        cell_width = max(360, usable_width // cols)
        cell_height = max(280, usable_height // rows)

        row = (index - 1) // cols
        col = (index - 1) % cols
        x = geometry.x() + margin + (col * (cell_width + gap))
        y = geometry.y() + margin + (row * (cell_height + gap))
        return x, y, cell_width, cell_height

    def _create_browser_profile_dir(self, index: int) -> Path:
        prefix = f"ezymailer-{self.state.username or 'guest'}-{index}-"
        profile_dir = Path(tempfile.mkdtemp(prefix=prefix))
        self._seed_browser_profile_dir(profile_dir)
        return profile_dir

    def _seed_browser_profile_dir(self, profile_dir: Path) -> None:
        """Pre-populate a fresh Chrome profile to suppress first-run prompts."""
        try:
            profile_dir.mkdir(parents=True, exist_ok=True)
            (profile_dir / "First Run").touch(exist_ok=True)
            local_state_path = profile_dir / "Local State"
            if not local_state_path.exists():
                local_state_path.write_text(
                    json.dumps(
                        {
                            "user_experience_metrics": {
                                "reporting_enabled": False,
                            },
                            "browser": {
                                "check_default_browser": False,
                            },
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
        except Exception:
            pass

    def _cleanup_browser_profile_dir(self, profile_dir: Path | None) -> None:
        if profile_dir is None:
            return
        try:
            shutil.rmtree(profile_dir, ignore_errors=True)
        except Exception:
            pass

    def _launch_browser_process(self, index: int) -> BrowserSessionHandle:
        binary = self._browser_binary()
        if binary is None:
            raise RuntimeError("Google Chrome was not found in /Applications.")

        incognito = self.state.browser_mode == "Incognito"
        session_id = f"chrome-{QDateTime.currentMSecsSinceEpoch()}-{index}"
        title = f"Chrome Window {index}"
        profile_dir = self._create_browser_profile_dir(index)
        args = [str(binary), "--new-window", f"--user-data-dir={profile_dir}"]
        # Suppress Chrome's first-run welcome dialog and default-browser prompt.
        args.extend(
            [
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-default-apps",
                "--disable-features=ChromeWhatsNewUI",
            ]
        )
        if incognito:
            args.append("--incognito")
        x, y, width, height = self._browser_launch_rect(index, max(1, self.window_spin.value()))
        args.append(f"--window-position={x},{y}")
        args.append(f"--window-size={width},{height}")
        args.append("about:blank")
        process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return BrowserSessionHandle(
            session_id=session_id,
            title=title,
            mode="Incognito" if incognito else "Normal",
            process=process,
            status="Running",
            profile_dir=profile_dir,
        )

    def _sync_browser_session_states(self) -> None:
        removed_sessions: list[BrowserSessionHandle] = []
        alive_sessions: list[BrowserSessionHandle] = []
        for session in self._browser_sessions:
            if session.is_alive():
                if session.status != "Paused":
                    session.status = "Running"
                alive_sessions.append(session)
                continue
            removed_sessions.append(session)

        if removed_sessions:
            self._browser_sessions = alive_sessions
            self._sync_session_state_from_handles()
            self._refresh_sessions()
            for session in removed_sessions:
                if self.state.username:
                    try:
                        record_browser_session(
                            self.state.username,
                            session.session_id,
                            session.title,
                            "Google Chrome",
                            self.state.browser_mode,
                            "Closed",
                            None,
                            self.state.launch_preset or "Default",
                            {
                                "browser_mode": self.state.browser_mode,
                                "profile_dir": str(session.profile_dir) if session.profile_dir else "",
                            },
                        )
                    except Exception:
                        pass
                self._cleanup_browser_profile_dir(session.profile_dir)
                self._log_action(f"Browser window closed: {session.title}")
        else:
            self._sync_session_state_from_handles()

        if not self._browser_sessions:
            self._browser_watch_timer.stop()

    def _sync_session_state_from_handles(self) -> None:
        self.state.active_sessions = [
            f"{session.title} - {session.status}" for session in self._browser_sessions
        ]
        self.state.window_count = len(self._browser_sessions)
        self.active_windows_value.setText(str(self.state.window_count))

    def _terminate_browser_sessions(self, log_reason: str | None = None) -> None:
        for session in self._browser_sessions:
            process = session.process
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=3)
                except Exception:
                    try:
                        process.kill()
                    except Exception:
                        pass
            if self.state.username:
                try:
                    record_browser_session(
                        self.state.username,
                        session.session_id,
                        session.title,
                        "Google Chrome",
                        session.mode,
                        "Closed",
                        None,
                        self.state.launch_preset or "Default",
                        {
                            "browser_mode": self.state.browser_mode,
                            "profile_dir": str(session.profile_dir) if session.profile_dir else "",
                        },
                    )
                except Exception:
                    pass
            self._cleanup_browser_profile_dir(session.profile_dir)
            if log_reason:
                self._log_action(f"{log_reason}: {session.title}")
        self._browser_sessions.clear()
        self._sync_session_state_from_handles()
        self._refresh_sessions()
        self._browser_watch_timer.stop()

    def _handle_launch(self) -> None:
        title = "Confirm Launch"
        prompt = (
            f"Launch {self.window_spin.value()} browser window(s) using {self.state.browser_mode} mode "
            f"and the {self.launch_preset_label.text()} preset?"
        )
        confirm = ConfirmDialog(self.window(), title, prompt, scale=self._scale)
        if confirm.exec() != QDialog.Accepted:
            self.notify("Launch cancelled")
            return
        target = max(1, self.window_spin.value())
        self._terminate_browser_sessions()
        self._log_action(f"Preparing {target} browser window(s)")
        self.notify(f"Launching {target} browser window(s)")
        self._show_launch_loader(
            "Launching browser windows",
            "Applying browser mode and launch preset.",
        )
        QTimer.singleShot(900, lambda t=target: self._complete_launch(t))

    def _handle_pause(self) -> None:
        if not self._browser_sessions:
            self.notify("No browser windows are currently open")
            return
        for session in self._browser_sessions:
            session.status = "Paused"
        self._sync_session_state_from_handles()
        self._refresh_sessions()
        self._browser_watch_timer.start()
        if self.state.username:
            for session in self._browser_sessions:
                try:
                    record_browser_session(
                        self.state.username,
                        session.session_id,
                        session.title,
                        "Google Chrome",
                        session.mode,
                        session.status,
                        session.process.pid if session.process is not None else None,
                        self.state.launch_preset or "Default",
                        {
                            "browser_mode": self.state.browser_mode,
                            "profile_dir": str(session.profile_dir) if session.profile_dir else "",
                        },
                    )
                except Exception:
                    pass
        self._log_action("Paused active browser sessions")
        self.notify("Sessions paused")

    def _handle_stop(self) -> None:
        self._handle_pause()

    def _handle_reset(self) -> None:
        self._terminate_browser_sessions()
        self.state.window_count = 1
        self.state.browser_mode = "Incognito"
        self.state.body_mode = "Normal Message"
        self.state.launch_preset = "Default"
        self.state.ai_provider = "ChatGPT"
        self.state.ai_model = ""
        self.state.ai_connected = False
        self._available_ai_models = []
        self.window_spin.setValue(1)
        self.ai_provider_combo.blockSignals(True)
        self.ai_provider_combo.setCurrentText("ChatGPT")
        self.ai_provider_combo.blockSignals(False)
        self.ai_api_key_input.clear()
        self._refresh_controls()
        self._log_action("Reset workspace to defaults")
        self.notify("Workspace reset to defaults")

    def _close_session(self, session_id: str) -> None:
        session = next((item for item in self._browser_sessions if item.session_id == session_id), None)
        if session is None:
            return
        process = session.process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        self._browser_sessions = [item for item in self._browser_sessions if item.session_id != session_id]
        self._sync_session_state_from_handles()
        self._refresh_sessions()
        if self.state.username:
            try:
                record_browser_session(
                    self.state.username,
                    session.session_id,
                    session.title,
                    "Google Chrome",
                    session.mode,
                    "Closed",
                    None,
                    self.state.launch_preset or "Default",
                    {
                        "browser_mode": self.state.browser_mode,
                        "profile_dir": str(session.profile_dir) if session.profile_dir else "",
                    },
                )
            except Exception:
                pass
        self._cleanup_browser_profile_dir(session.profile_dir)
        self._log_action(f"Closed browser window {session.title}")
        self.notify(f"Closed {session.title}")

    def _start_blast(self) -> None:
        self._handle_launch()

    def _show_launch_loader(self, title: str, subtitle: str) -> None:
        self.window().show_launch_loader(title, subtitle)

    def _current_body_widget(self) -> BodyDraftEditor | None:
        widget = self.body_tabs.currentWidget()
        if isinstance(widget, BodyDraftEditor):
            return widget
        return None

    def _sync_active_body_widget_refs(self) -> None:
        widget = self._current_body_widget()
        if widget is None:
            return
        self.body_editor = widget.plain_editor
        self.html_message_editor = widget.html_editor
        self.message_stack = widget.stack
        self.state.body_mode = widget.mode_text()
        self.normal_message_button = widget.plain_button
        self.html_message_button = widget.html_button
        self.body_mode_group = widget._plain_group

    def _update_body_tab_controls(self) -> None:
        limit_reached = self.body_tabs.count() >= MAX_BODY_TABS
        self.body_add_button.setEnabled(not limit_reached)
        self.body_add_button.setToolTip("Maximum of 50 bodies reached" if limit_reached else "Add a new body")

    def _set_subject_item_data(self, item: QListWidgetItem, record_id: int | None, title: str, subject: str) -> None:
        item.setData(Qt.UserRole, record_id)
        item.setData(Qt.UserRole + 1, title)
        item.setData(Qt.UserRole + 2, subject)
        item.setText(title or subject or "Untitled Subject")

    def _selected_subject_item(self) -> QListWidgetItem | None:
        return self.subject_drafts_list.currentItem()

    def _clear_subject_selection(self) -> None:
        self.subject_drafts_list.blockSignals(True)
        try:
            self.subject_drafts_list.clearSelection()
        finally:
            self.subject_drafts_list.blockSignals(False)

    def _subject_item_subject(self, item: QListWidgetItem | None) -> str:
        if item is None:
            return ""
        return str(item.data(Qt.UserRole + 2) or "")

    def _subject_item_title(self, item: QListWidgetItem | None) -> str:
        if item is None:
            return ""
        return str(item.data(Qt.UserRole + 1) or item.text() or "")

    def _open_subject_manager(self) -> None:
        if not self.state.logged_in or not self.state.auth_token:
            self.notify("Sign in first to manage subjects")
            return

        dialog = SubjectDraftsDialog(self, self.state.auth_token, scale=self._scale)
        if dialog.exec() == QDialog.Accepted:
            subject = dialog.selected_subject()
            if subject:
                self.subject_input.blockSignals(True)
                try:
                    self.subject_input.setText(subject)
                finally:
                    self.subject_input.blockSignals(False)
                self.state.subject_text = subject
                self._schedule_subject_body_save()
            self.load_user_workspace()

    def _on_subject_selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if self._workspace_loading:
            return
        if current is None:
            return
        subject = self._subject_item_subject(current)
        if subject:
            self.subject_input.blockSignals(True)
            try:
                self.subject_input.setText(subject)
            finally:
                self.subject_input.blockSignals(False)
            self.state.subject_text = subject

    def _new_subject_draft(self) -> None:
        self._clear_subject_selection()
        self.subject_input.clear()
        self.state.subject_text = ""
        self._schedule_subject_body_save()

    def _subject_draft_rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for index in range(self.subject_drafts_list.count()):
            item = self.subject_drafts_list.item(index)
            rows.append(
                {
                    "id": item.data(Qt.UserRole),
                    "title": self._subject_item_title(item),
                    "subject": self._subject_item_subject(item),
                    "item": item,
                }
            )
        return rows

    def _save_subject_draft(self) -> None:
        if self._workspace_loading or not self.state.logged_in or not self.state.username:
            return

        subject = self.subject_input.text().strip()
        if not subject:
            self.notify("Enter a subject first")
            return

        self._show_subject_body_loader("Saving subject.")
        try:
            current_item = self._selected_subject_item()
            title = subject[:64]
            details = {"kind": "subject"}
            if current_item is not None and current_item.data(Qt.UserRole):
                record_id = int(current_item.data(Qt.UserRole))
                api_update_content(
                    self.state.auth_token,
                    record_id,
                    "subject",
                    title,
                    subject=subject,
                    details=details,
                )
                self._set_subject_item_data(current_item, record_id, title, subject)
            else:
                payload = api_save_content(
                    self.state.auth_token,
                    "subject",
                    title,
                    subject=subject,
                    details=details,
                )
                record = payload.get("content") or {}
                if isinstance(record, dict):
                    record_id = int(record.get("id") or 0)
                else:
                    record_id = 0
                new_item = QListWidgetItem()
                self._set_subject_item_data(new_item, record_id or None, title, subject)
                self.subject_drafts_list.addItem(new_item)
                self.subject_drafts_list.setCurrentItem(new_item)
            self.state.subject_text = subject
            self.subject_count_label.setText(f"{self.subject_drafts_list.count()} subjects")
            self._log_action(f"Saved subject: {title}")
            self.notify("Subject saved")
        except Exception as exc:
            self._log_action(f"Failed to save subject: {exc}")
            self.notify("Unable to save subject")
        finally:
            self._hide_subject_body_loader()

    def _delete_subject_draft(self) -> None:
        item = self._selected_subject_item()
        if item is None:
            return
        record_id = item.data(Qt.UserRole)
        title = self._subject_item_title(item)
        try:
            if record_id:
                api_delete_content(self.state.auth_token, int(record_id))
        except Exception as exc:
            self._log_action(f"Failed to delete subject: {exc}")
            self.notify("Unable to remove subject")
            return
        row = self.subject_drafts_list.row(item)
        self.subject_drafts_list.takeItem(row)
        self.subject_input.clear()
        self.state.subject_text = ""
        self.subject_count_label.setText(f"{self.subject_drafts_list.count()} subjects")
        self._log_action(f"Removed subject: {title or 'Untitled'}")
        self.notify("Subject removed")

    def _create_body_draft_tab(self, record: dict[str, object] | None = None) -> BodyDraftEditor:
        widget = BodyDraftEditor(scale=self._scale)
        if record:
            mode = "HTML Message" if str(record.get("body_html") or "") else "Normal Message"
            title = str(record.get("title") or "Body")
            subject = str(record.get("subject") or "")
            body_text = str(record.get("body_text") or "")
            body_html = str(record.get("body_html") or "")
            details = self._decode_setting_value(record.get("details_json"))
            if isinstance(details, dict) and details.get("body_mode"):
                mode = str(details.get("body_mode"))
            widget.draft_id = int(record.get("id") or 0) or None
            widget.set_content(title, mode, body_text, body_html or body_text)
        else:
            title = f"Body {self.body_tabs.count() + 1}"
            widget.set_content(title, "Normal Message", "Hello {{first_name}},\n\nThis is a body message.", "<div></div>")

        widget.titleChanged.connect(lambda title_text, w=widget: self._rename_body_tab(w, title_text))
        widget.contentChanged.connect(self._schedule_subject_body_save)
        widget.modeChanged.connect(lambda mode, w=widget: self._on_body_mode_changed(w, mode))
        widget.previewRequested.connect(lambda w=widget: self._preview_body_editor_html(w))
        return widget

    def _body_tab_label(self, widget: BodyDraftEditor, index: int) -> str:
        title = widget.title_text()
        if title:
            base = title
        else:
            base = f"Body {index + 1}"
        mode_label = "HTML" if widget.mode_text() == "HTML Message" else "Text"
        return f"{base} [{mode_label}]"

    def _refresh_body_tab_labels(self) -> None:
        for index in range(self.body_tabs.count()):
            widget = self.body_tabs.widget(index)
            if isinstance(widget, BodyDraftEditor):
                self.body_tabs.setTabText(index, self._body_tab_label(widget, index))

    def _rename_body_tab(self, widget: BodyDraftEditor, title: str) -> None:
        index = self.body_tabs.indexOf(widget)
        if index < 0:
            return
        self.body_tabs.setTabText(index, self._body_tab_label(widget, index))

    def _on_body_mode_changed(self, widget: BodyDraftEditor, mode: str) -> None:
        if widget is self._current_body_widget():
            self.state.body_mode = mode
            self.normal_message_button = widget.plain_button
            self.html_message_button = widget.html_button
        self._refresh_body_tab_labels()
        self._schedule_subject_body_save()

    def _add_body_draft_tab(self, record: dict[str, object] | None = None, select: bool = True) -> BodyDraftEditor | None:
        if self.body_tabs.count() >= MAX_BODY_TABS:
            self._update_body_tab_controls()
            self.notify("Maximum of 50 bodies reached")
            return None
        widget = self._create_body_draft_tab(record)
        tab_number = self.body_tabs.count() + 1
        tab_label = f"Body {tab_number} [{'HTML' if widget.mode_text() == 'HTML Message' else 'Text'}]"
        index = self.body_tabs.addTab(widget, tab_label)
        self._refresh_body_tab_labels()
        self._update_body_tab_controls()
        if select:
            self.body_tabs.setCurrentIndex(index)
        return widget

    def _new_body_draft_tab(self) -> None:
        self._add_body_draft_tab(select=True)

    def _remove_body_draft_tab(self, index: int) -> None:
        widget = self.body_tabs.widget(index)
        if not isinstance(widget, BodyDraftEditor):
            return
        if widget.draft_id:
            try:
                api_delete_content(self.state.auth_token, int(widget.draft_id))
            except Exception as exc:
                self._log_action(f"Failed to delete body: {exc}")
                self.notify("Unable to remove body")
                return
        self.body_tabs.removeTab(index)
        if self.body_tabs.count() == 0:
            self._add_body_draft_tab(select=True)
        else:
            self._refresh_body_tab_labels()
        self._update_body_tab_controls()
        self._sync_active_body_widget_refs()
        self._log_action("Removed body tab")

    def _on_body_tab_changed(self, _index: int) -> None:
        self._sync_active_body_widget_refs()
        self._schedule_subject_body_save()

    def _complete_launch(self, target: int) -> None:
        self.window().hide_launch_loader()
        if target <= 0:
            return
        launched: list[BrowserSessionHandle] = []
        try:
            for index in range(1, target + 1):
                launched.append(self._launch_browser_process(index))
        except Exception as exc:
            self._terminate_browser_sessions()
            self._log_action(f"Browser launch failed: {exc}")
            self.notify("Unable to launch Google Chrome")
            return

        self._browser_sessions = launched
        self._sync_session_state_from_handles()
        self._refresh_sessions()
        self._browser_watch_timer.start()
        if self.state.username:
            for session in self._browser_sessions:
                try:
                    record_browser_session(
                        self.state.username,
                        session.session_id,
                        session.title,
                        "Google Chrome",
                        session.mode,
                        session.status,
                        session.process.pid if session.process is not None else None,
                        self.state.launch_preset or "Default",
                        {
                            "browser_mode": self.state.browser_mode,
                            "profile_dir": str(session.profile_dir) if session.profile_dir else "",
                        },
                    )
                except Exception:
                    pass
        self._log_action(f"Started {len(launched)} browser window(s)")
        self.notify(f"Launch started for {len(launched)} browser window(s)")

    def _clear_subject_body(self) -> None:
        self._subject_body_save_timer.stop()
        self.subject_input.clear()
        self.state.subject_text = ""
        current = self._current_body_widget()
        if current is None:
            current = self._add_body_draft_tab(select=True)
        current.set_content("Body 1", "Normal Message", "", "")
        self.state.body_mode = "Normal Message"
        self.state.plain_body_text = ""
        self.state.html_message_text = ""
        self.state.html_template_text = ""
        self._log_action("Cleared subject and body")
        self._schedule_subject_body_save()

    def _save_current_body_draft(self) -> None:
        if self._workspace_loading or not self.state.logged_in or not self.state.username:
            return
        self._show_subject_body_loader("Saving body.")
        try:
            self._persist_subject_body_state()
            current = self._current_body_widget()
            title = current.title_text() if current is not None else "Body"
            self._log_action(f"Saved body: {title or 'Body'}")
            self.notify("Body saved")
        except Exception as exc:
            self._log_action(f"Failed to save body: {exc}")
            self.notify("Unable to save body")
        finally:
            self._hide_subject_body_loader()

    def _show_subject_body_loader(self, subtitle: str) -> None:
        self.window().show_launch_loader("Please wait", subtitle)
        QApplication.processEvents()

    def _hide_subject_body_loader(self) -> None:
        self.window().hide_launch_loader()

    def _schedule_subject_body_save(self) -> None:
        if self._workspace_loading or not self.state.logged_in or not self.state.username:
            return
        self._subject_body_save_timer.start()

    def _read_text_template_file(self, path: Path) -> str:
        return path.read_text(encoding="utf-8-sig").strip()

    def _load_subject_from_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load subject template",
            "",
            "Text files (*.txt *.csv);;All files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        self._show_subject_body_loader(f"Loading subject template from {path.name}.")
        try:
            raw_text = self._read_text_template_file(path)
            subjects = [line.strip() for line in raw_text.splitlines() if line.strip()]
            if not subjects:
                subjects = [path.stem.replace("_", " ").strip() or "Subject"]

            self._workspace_loading = True
            self.subject_drafts_list.blockSignals(True)
            try:
                for subject in subjects:
                    payload = api_save_content(
                        self.state.auth_token,
                        "subject",
                        subject[:64] or "Subject",
                        subject=subject,
                        details={"kind": "subject", "source_file": path.name},
                    )
                    record = payload.get("content") or {}
                    item = QListWidgetItem()
                    record_id = int(record.get("id") or 0) if isinstance(record, dict) else None
                    self._set_subject_item_data(item, record_id, subject[:64] or "Subject", subject)
                    self.subject_drafts_list.addItem(item)
                self.subject_drafts_list.setCurrentRow(self.subject_drafts_list.count() - 1)
            finally:
                self.subject_drafts_list.blockSignals(False)
            current = self.subject_drafts_list.currentItem()
            if current is not None:
                self.subject_input.setText(self._subject_item_subject(current))
                self.state.subject_text = self.subject_input.text().strip()
            self.subject_count_label.setText(f"{self.subject_drafts_list.count()} subjects")
            self._log_action(f"Loaded {len(subjects)} subject(s) from {path.name}")
            self.notify(f"Loaded {len(subjects)} subject(s)")
        except Exception as exc:
            self.notify(f"Unable to load subject file: {exc}")
            self._log_action(f"Failed to load subject template from {path.name}: {exc}")
        finally:
            self._workspace_loading = False
            self._hide_subject_body_loader()
        self._schedule_subject_body_save()

    def _load_body_from_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load body template",
            "",
            "Text/HTML files (*.txt *.html *.htm);;All files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        self._show_subject_body_loader(f"Loading body template from {path.name}.")
        try:
            body = self._read_text_template_file(path)
            is_html = path.suffix.lower() in {".html", ".htm"} or "<html" in body.lower()
            title = path.stem.replace("_", " ").strip() or "Body"
            payload = api_save_content(
                self.state.auth_token,
                "body",
                title[:64],
                body_text="" if is_html else body,
                body_html=body if is_html else "",
                details={"kind": "body", "body_mode": "HTML Body" if is_html else "Plain Text", "source_file": path.name},
            )
            record = payload.get("content") or {}
            self._workspace_loading = True
            body_widget = self._add_body_draft_tab(record if isinstance(record, dict) else None, select=True)
            if isinstance(record, dict) and record.get("id"):
                body_widget.draft_id = int(record.get("id"))
            if is_html:
                body_widget.set_content(title, "HTML Message", "", body)
            else:
                body_widget.set_content(title, "Normal Message", body, "")
            self._sync_active_body_widget_refs()
            self._log_action(f"Loaded body from {path.name}")
            self.notify(f"Loaded body from {path.name}")
        except Exception as exc:
            self.notify(f"Unable to load body file: {exc}")
            self._log_action(f"Failed to load body template from {path.name}: {exc}")
        finally:
            self._workspace_loading = False
            self._hide_subject_body_loader()
        self._schedule_subject_body_save()

    def _upload_body_files(self) -> None:
        if not self.state.logged_in or not self.state.auth_token:
            self.notify("Sign in first to upload bodies")
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Upload bodies",
            "",
            "CSV or HTML files (*.csv *.html *.htm);;CSV files (*.csv);;HTML files (*.html *.htm);;All files (*)",
        )
        if not file_paths:
            return

        imported = 0
        self._show_subject_body_loader("Uploading body files.")
        self._workspace_loading = True
        try:
            for file_name in file_paths:
                if self.body_tabs.count() >= MAX_BODY_TABS:
                    self.notify("Maximum of 50 bodies reached")
                    break

                path = Path(file_name)
                suffix = path.suffix.lower()
                if suffix == ".csv":
                    imported += self._import_csv_body_file(path)
                elif suffix in {".html", ".htm"}:
                    imported += self._import_html_body_file(path)
                else:
                    self._log_action(f"Skipped unsupported body file: {path.name}")
        except Exception as exc:
            self._log_action(f"Failed to upload body files: {exc}")
            self.notify(f"Unable to upload bodies: {exc}")
        finally:
            self._workspace_loading = False
            self._hide_subject_body_loader()

        if self.body_tabs.count() == 0:
            self._add_body_draft_tab(select=True)
        else:
            self._refresh_body_tab_labels()
            self._update_body_tab_controls()
            self._sync_active_body_widget_refs()

        if imported > 0:
            self._log_action(f"Uploaded {imported} body(s)")
            self.notify(f"Uploaded {imported} body(s)")
        self._schedule_subject_body_save()

    def _import_csv_body_file(self, path: Path) -> int:
        imported = 0
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            rows = [row for row in reader if any(str(cell).strip() for cell in row)]

        for index, row in enumerate(rows, start=1):
            if self.body_tabs.count() >= MAX_BODY_TABS:
                break
            cells = [str(cell).strip() for cell in row if str(cell).strip()]
            if not cells:
                continue
            body_text = cells[0]
            title = f"{path.stem.replace('_', ' ').strip() or 'Body'} {index}" if len(rows) > 1 else path.stem.replace("_", " ").strip() or "Body"
            self._create_and_store_body_tab(
                title=title,
                mode="Normal Message",
                plain_text=body_text,
                html_text="",
                source_name=path.name,
            )
            imported += 1
        return imported

    def _import_html_body_file(self, path: Path) -> int:
        body = self._read_text_template_file(path)
        if not body.strip():
            return 0
        title = path.stem.replace("_", " ").strip() or "HTML Body"
        self._create_and_store_body_tab(
            title=title,
            mode="HTML Message",
            plain_text="",
            html_text=body,
            source_name=path.name,
        )
        return 1

    def _create_and_store_body_tab(
        self,
        *,
        title: str,
        mode: str,
        plain_text: str,
        html_text: str,
        source_name: str = "",
    ) -> BodyDraftEditor | None:
        if self.body_tabs.count() >= MAX_BODY_TABS:
            return None

        details = {"kind": "body", "body_mode": "HTML Body" if mode == "HTML Message" else "Plain Text"}
        if source_name:
            details["source_file"] = source_name
        payload = api_save_content(
            self.state.auth_token,
            "body",
            title[:64] or "Body",
            body_text=plain_text,
            body_html=html_text if mode == "HTML Message" else "",
            details=details,
        )
        record = payload.get("content") or {}
        widget = self._add_body_draft_tab(record if isinstance(record, dict) else None, select=False)
        if widget is None:
            return None
        widget.set_content(title, mode, plain_text, html_text if mode == "HTML Message" else "")
        if isinstance(record, dict) and record.get("id"):
            widget.draft_id = int(record.get("id"))
        self._refresh_body_tab_labels()
        self._update_body_tab_controls()
        return widget

    def _persist_subject_body_state(self) -> None:
        if self._workspace_loading or not self.state.logged_in or not self.state.username:
            return

        subject = self.subject_input.text().strip()
        current_subject = self._selected_subject_item()
        current_body = self._current_body_widget()
        if current_body is None:
            current_body = self._add_body_draft_tab(select=True)
        body_payload = current_body.payload()
        body_mode = body_payload["mode"]
        plain_body = body_payload["plain_text"]
        html_body = body_payload["html_text"]
        body_title = body_payload["title"] or "Body"

        self.state.subject_text = subject
        self.state.plain_body_text = plain_body
        self.state.html_message_text = html_body
        self.state.body_mode = body_mode
        self.state.html_template_text = self.html_editor.toPlainText()

        try:
            if subject:
                subject_title = subject[:64] or "Subject"
                if current_subject is not None and current_subject.data(Qt.UserRole):
                    subject_id = int(current_subject.data(Qt.UserRole))
                    api_update_content(
                        self.state.auth_token,
                        subject_id,
                        "subject",
                        subject_title,
                        subject=subject,
                        details={"kind": "subject"},
                    )
                    self._set_subject_item_data(current_subject, subject_id, subject_title, subject)
                else:
                    payload = api_save_content(
                        self.state.auth_token,
                        "subject",
                        subject_title,
                        subject=subject,
                        details={"kind": "subject"},
                    )
                    record = payload.get("content") or {}
                    subject_id = int(record.get("id") or 0) if isinstance(record, dict) else None
                    item = QListWidgetItem()
                    self._set_subject_item_data(item, subject_id, subject_title, subject)
                    self.subject_drafts_list.addItem(item)
                    self.subject_drafts_list.setCurrentItem(item)

            if current_body.draft_id:
                api_update_content(
                    self.state.auth_token,
                    int(current_body.draft_id),
                    "body",
                    body_title[:64] or "Body",
                    body_text=plain_body,
                    body_html=html_body if body_mode == "HTML Body" else "",
                    details={"kind": "body", "body_mode": body_mode},
                )
            else:
                payload = api_save_content(
                    self.state.auth_token,
                    "body",
                    body_title[:64] or "Body",
                    body_text=plain_body,
                    body_html=html_body if body_mode == "HTML Body" else "",
                    details={"kind": "body", "body_mode": body_mode},
                )
                record = payload.get("content") or {}
                if isinstance(record, dict) and record.get("id"):
                    current_body.draft_id = int(record.get("id"))
                    self._rename_body_tab(current_body, body_title[:64] or "Body")

            upsert_setting(self.state.username, "subject_text", subject, user_id=None)
            upsert_setting(self.state.username, "plain_body_text", plain_body, user_id=None)
            upsert_setting(self.state.username, "html_message_text", html_body, user_id=None)
            upsert_setting(self.state.username, "html_template_text", self.state.html_template_text, user_id=None)
            upsert_setting(self.state.username, "body_mode", body_mode, user_id=None)
            upsert_setting(self.state.username, "subject_body_last_saved", QDateTime.currentDateTime().toString(Qt.ISODate), user_id=None)
        except Exception as exc:
            self._log_action(f"Failed to save subject/body state: {exc}")

    def _save_subject_body_draft(self) -> None:
        if not self.state.logged_in or not self.state.username:
            self.notify("Sign in first to save changes")
            return

        self._show_subject_body_loader("Saving subject and body.")
        try:
            self._persist_subject_body_state()
            title = self.subject_input.text().strip() or "Untitled Subject"
            self._log_action(f"Saved subject and body: {title}")
            self.notify("Subject and body saved")
        except Exception as exc:
            self._log_action(f"Failed to save subject and body: {exc}")
            self.notify("Unable to save subject and body")
        finally:
            self._hide_subject_body_loader()

    def _decode_setting_value(self, raw_value) -> object:
        if raw_value is None:
            return None
        if isinstance(raw_value, str):
            try:
                return json.loads(raw_value)
            except Exception:
                return raw_value
        return raw_value

    def _sync_subject_body_widgets(self) -> None:
        self._workspace_loading = True
        try:
            if self.body_tabs.count() == 0:
                self._add_body_draft_tab(select=True)
            self._sync_active_body_widget_refs()
            self.subject_count_label.setText(f"{self.subject_drafts_list.count()} subjects")
            self._update_body_tab_controls()
        finally:
            self._workspace_loading = False

    def load_user_workspace(self) -> None:
        if not self.state.logged_in or not self.state.auth_token:
            return

        self._workspace_loading = True
        try:
            settings_payload = api_get_settings(self.state.auth_token)
            content_payload = api_get_content(self.state.auth_token)
        except Exception:
            self._workspace_loading = False
            return

        try:
            settings_rows = settings_payload.get("settings") or []
            settings_map: dict[str, object] = {}
            for row in settings_rows:
                key = str(row.get("setting_key") or "")
                if not key:
                    continue
                settings_map[key] = self._decode_setting_value(row.get("setting_value_json"))

            self.state.body_mode = str(settings_map.get("body_mode") or self.state.body_mode or "Normal Message")
            self.state.subject_text = str(settings_map.get("subject_text") or self.state.subject_text or "")
            self.state.plain_body_text = str(settings_map.get("plain_body_text") or self.state.plain_body_text or "")
            self.state.html_message_text = str(settings_map.get("html_message_text") or self.state.html_message_text or "")
            self.state.html_template_text = str(settings_map.get("html_template_text") or self.state.html_template_text or "")

            content_rows = content_payload.get("content") or []
            subject_rows: list[dict[str, object]] = []
            body_rows: list[dict[str, object]] = []
            legacy_rows: list[dict[str, object]] = []
            for row in content_rows:
                if not isinstance(row, dict):
                    continue
                details = self._decode_setting_value(row.get("details_json"))
                content_type = str(row.get("content_type") or "")
                kind = ""
                if isinstance(details, dict):
                    kind = str(details.get("kind") or "")
                if content_type in {"subject", "subject-draft"} or kind in {"subject", "subject-draft"}:
                    subject_rows.append(row)
                elif content_type in {"body", "body-draft"} or kind in {"body", "body-draft"}:
                    body_rows.append(row)
                else:
                    legacy_rows.append(row)

            self.subject_drafts_list.blockSignals(True)
            try:
                self.subject_drafts_list.clear()
                for row in reversed(subject_rows):
                    item = QListWidgetItem()
                    record_id = int(row.get("id") or 0) or None
                    title = str(row.get("title") or row.get("subject") or "Subject")
                    subject = str(row.get("subject") or row.get("title") or "")
                    self._set_subject_item_data(item, record_id, title, subject)
                    self.subject_drafts_list.addItem(item)
                if self.subject_drafts_list.count() > 0:
                    self.subject_drafts_list.setCurrentRow(self.subject_drafts_list.count() - 1)
            finally:
                self.subject_drafts_list.blockSignals(False)

            while self.body_tabs.count() > 0:
                self.body_tabs.removeTab(0)

            body_row = body_rows[0] if body_rows else (legacy_rows[0] if legacy_rows else None)
            if body_row is not None:
                self._add_body_draft_tab(body_row, select=True)
            if self.body_tabs.count() == 0:
                self._add_body_draft_tab(select=True)
            else:
                self.body_tabs.setCurrentIndex(0)
            self._refresh_body_tab_labels()
            self._update_body_tab_controls()

            current_subject = self.subject_drafts_list.currentItem()
            if current_subject is not None:
                subject = self._subject_item_subject(current_subject)
                self.subject_input.blockSignals(True)
                try:
                    self.subject_input.setText(subject)
                finally:
                    self.subject_input.blockSignals(False)
                self.state.subject_text = subject
            elif self.state.subject_text:
                self.subject_input.blockSignals(True)
                try:
                    self.subject_input.setText(self.state.subject_text)
                finally:
                    self.subject_input.blockSignals(False)

            self._sync_active_body_widget_refs()
            active_body = self._current_body_widget()
            if active_body is not None:
                payload = active_body.payload()
                self.state.body_mode = payload["mode"]
                self.state.plain_body_text = payload["plain_text"]
                self.state.html_message_text = payload["html_text"]
                self.state.subject_text = self.subject_input.text().strip() or self.state.subject_text
            self.subject_count_label.setText(f"{self.subject_drafts_list.count()} subjects")
        finally:
            self._workspace_loading = False
            self._sync_subject_body_widgets()

    def _clear_pending_emails(self) -> None:
        self.pending_emails_editor.clear()
        self.state.pending_recipients = []
        self.data_summary_labels["total"].setText("0")
        self.data_summary_labels["valid"].setText("0")
        self.data_summary_labels["invalid"].setText("0")
        self.data_summary_labels["duplicates"].setText("0")
        self._log_action("Cleared pending email list")

    def _show_email_loader(self, subtitle: str) -> None:
        self.window().show_launch_loader("Please wait", subtitle)
        QApplication.processEvents()

    def _hide_email_loader(self) -> None:
        self.window().hide_launch_loader()

    def _extract_email_candidates(self, text: str) -> list[str]:
        pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        candidates: list[str] = []
        for match in pattern.finditer(text or ""):
            email = match.group(0).strip().strip("<>[]{}()\"'.,;:")
            if email:
                candidates.append(email.lower())
        return candidates

    def _load_pending_emails_from_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load recipient file",
            "",
            "Data files (*.csv *.xlsx *.xls *.txt);;CSV files (*.csv);;Excel files (*.xlsx *.xls);;Text files (*.txt);;All files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        self._show_email_loader(f"Loading recipient data from {path.name}.")
        try:
            emails = self._read_email_file(path)
        except Exception as exc:
            self.notify(f"Unable to load file: {exc}")
            self._log_action(f"Failed to load pending emails from {path.name}: {exc}")
            return
        finally:
            self._hide_email_loader()

        self.pending_emails_editor.blockSignals(True)
        try:
            self.pending_emails_editor.setPlainText("\n".join(emails))
        finally:
            self.pending_emails_editor.blockSignals(False)
        self.state.pending_recipients = emails[:]
        self._log_action(f"Loaded pending emails from {path.name}")
        self.notify(f"Loaded {len(emails)} email(s)")
        self._prompt_validate_pending_emails()

    def _read_email_file(self, path: Path) -> list[str]:
        suffix = path.suffix.lower()
        rows: list[str] = []
        if suffix in {".xlsx", ".xls"}:
            try:
                import pandas as pd
            except Exception as exc:
                raise RuntimeError("Excel support requires pandas and openpyxl.") from exc
            frame = pd.read_excel(path, header=None, dtype=str)
            for value in frame.fillna("").astype(str).to_numpy().ravel().tolist():
                rows.extend(self._extract_email_candidates(value))
        else:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                if suffix == ".csv":
                    reader = csv.reader(handle)
                    for row in reader:
                        for cell in row:
                            rows.extend(self._extract_email_candidates(cell))
                else:
                    rows.extend(self._extract_email_candidates(handle.read()))

        deduped: list[str] = []
        seen: set[str] = set()
        for email in rows:
            if email not in seen:
                seen.add(email)
                deduped.append(email)
        return deduped

    def _prompt_validate_pending_emails(self) -> None:
        reply = QMessageBox.question(
            self,
            "Validate Emails",
            "Do you want to validate the customer email list now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._validate_pending_emails(confirm=False)
        else:
            self._log_action("Skipped email validation by user choice")

    def _validate_pending_emails(self, confirm: bool = True) -> None:
        if confirm:
            reply = QMessageBox.question(
                self,
                "Validate Emails",
                "Do you want to validate the customer email list now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                self._log_action("Skipped email validation by user choice")
                return

        self._show_email_loader("Validating customer email addresses.")
        try:
            source_text = self.pending_emails_editor.toPlainText()
            candidates = self._extract_email_candidates(source_text)
            gmail_only = self.standard_email_radio.isChecked()

            accepted: list[str] = []
            rejected: list[str] = []
            seen: set[str] = set()
            duplicates = 0

            for email in candidates:
                domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
                allowed = (domain == "gmail.com") if gmail_only else bool(domain)
                if not allowed:
                    rejected.append(email)
                    continue
                if email in seen:
                    duplicates += 1
                    continue
                seen.add(email)
                accepted.append(email)

            self.state.pending_recipients = accepted[:]
            self.pending_emails_editor.blockSignals(True)
            try:
                self.pending_emails_editor.setPlainText("\n".join(accepted))
            finally:
                self.pending_emails_editor.blockSignals(False)
            self.data_summary_labels["total"].setText(str(len(candidates)))
            self.data_summary_labels["valid"].setText(str(len(accepted)))
            self.data_summary_labels["invalid"].setText(str(len(rejected)))
            self.data_summary_labels["duplicates"].setText(str(duplicates))

            mode_label = "gmail.com only" if gmail_only else "mixed domains"
            self._log_action(
                f"Validated {len(candidates)} email candidate(s) in {mode_label}: "
                f"{len(accepted)} valid, {len(rejected)} invalid, {duplicates} duplicates"
            )
            self.notify(f"{len(accepted)} valid email(s) ready")
        finally:
            self._hide_email_loader()

    def eventFilter(self, obj, event):
        if obj is self.pending_emails_editor and event.type() == QEvent.KeyPress:
            if event.matches(QKeySequence.Paste):
                result = super().eventFilter(obj, event)
                QTimer.singleShot(0, self._prompt_validate_pending_emails)
                return result
        return super().eventFilter(obj, event)

    def _refresh_sessions(self) -> None:
        self.session_list.clear()
        self._sync_session_state_from_handles()
        for index, item in enumerate(self._browser_sessions, start=1):
            row_widget = self._session_row(item, index)
            list_item = QListWidgetItem()
            list_item.setSizeHint(row_widget.sizeHint())
            self.session_list.addItem(list_item)
            self.session_list.setItemWidget(list_item, row_widget)

    def _refresh_activity(self) -> None:
        if not self.state.activity_log:
            self.activity_log_view.setPlainText("[--:--:--] No activity yet.")
            self.send_log_view.setPlainText("[--:--:--] No send events yet.")
            return

        lines = "\n".join(self.state.activity_log[-30:][::-1])
        self.activity_log_view.setPlainText(lines)
        self.send_log_view.setPlainText(lines)

    def _refresh_controls(self) -> None:
        self.incognito_button.setChecked(self.state.browser_mode == "Incognito")
        self.normal_button.setChecked(self.state.browser_mode == "Normal")
        self.normal_message_button.setChecked(self.state.body_mode == "Normal Message")
        self.html_message_button.setChecked(self.state.body_mode == "HTML Message")
        current_body = self._current_body_widget()
        if current_body is not None:
            current_body.set_mode(self.state.body_mode)
        self.active_windows_value.setText(str(len(self._browser_sessions)))
        self.launch_preset_label.setText(self.state.launch_preset or "None")
        self.progress_bar.setValue(0)
        self.ai_provider_combo.blockSignals(True)
        self.ai_provider_combo.setCurrentText(self.state.ai_provider)
        self.ai_provider_combo.blockSignals(False)
        self._refresh_ai_models()
        self._sync_ai_connection_ui()

    def _log_action(self, message: str) -> None:
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.state.activity_log.append(f"[{timestamp}] {message}")
        if self.state.logged_in and self.state.username:
            try:
                record_activity(
                    self.state.username,
                    message,
                    category="ui",
                    user_id=None,
                )
            except Exception:
                pass
        self._refresh_activity()
        if callable(self.notify):
            self.notify(message)

    def _session_row(self, session: BrowserSessionHandle, index: int) -> QWidget:
        row = QFrame()
        row.setObjectName("sessionRow")
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(_scaled_int(8, self._scale), _scaled_int(7, self._scale), _scaled_int(8, self._scale), _scaled_int(7, self._scale))
        row_layout.setSpacing(_scaled_int(4, self._scale))
        row.setMinimumHeight(_scaled_int(52, self._scale))

        dot = QLabel("●")
        dot.setObjectName("sessionDot")
        label = QLabel(session.title)
        label.setObjectName("sessionTitleSmall")
        state = QLabel(f"{session.mode} - {session.status}")
        state.setObjectName("sessionState")
        label.setMinimumWidth(_scaled_int(72, self._scale))
        state.setMinimumWidth(_scaled_int(80, self._scale))
        state.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        close_button = QPushButton("✕")
        close_button.setObjectName("dangerButton")
        close_button.setFixedWidth(_scaled_int(28, self._scale))
        close_button.clicked.connect(lambda _, sid=session.session_id: self._close_session(sid))
        close_button.setToolTip("Close this browser window")

        top_row = QHBoxLayout()
        top_row.setSpacing(_scaled_int(6, self._scale))
        top_row.addWidget(dot)
        top_row.addWidget(label)
        top_row.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(_scaled_int(6, self._scale))
        bottom_row.addWidget(state)
        bottom_row.addStretch()
        bottom_row.addWidget(close_button)

        row_layout.addLayout(top_row)
        row_layout.addLayout(bottom_row)
        return row

    def refresh(self) -> None:
        self.window_spin.setValue(self.state.window_count)
        self._refresh_controls()
        self._sync_subject_body_widgets()
        self._refresh_sessions()
        self._refresh_activity()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        self._toasts = []
        self._pending_launch_target = 0
        self._scale = _compute_layout_scale(QApplication.primaryScreen())
        self._text_scale = _compute_text_scale(QApplication.primaryScreen())
        self._centered_once = False
        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.resize(_scaled_int(1120, self._scale), _scaled_int(760, self._scale))
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(self, self.close, scale=self._scale)
        self.title_bar.set_logout_handler(self.handle_logout)
        self.title_bar.sync_window_state()
        self.launch_loader = LaunchLoaderDialog(self, scale=self._scale)

        self.stack = QStackedWidget()
        self.login_page = LoginPage(self.handle_login, scale=self._scale)
        self.dashboard_page = DashboardPage(self.state, self.handle_logout, self.show_toast, scale=self._scale)
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.dashboard_page)
        root.addWidget(self.title_bar)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(container)
        self._apply_styles()
        self.show_login()

    def show_toast(self, message: str, kind: str = "info") -> None:
        toast = Toast(self, message, kind, scale=self._scale)
        self._toasts.append(toast)
        toast.destroyed.connect(lambda: self._remove_toast(toast))
        toast.adjustSize()
        toast.move(
            max(12, self.width() - toast.width() - 16),
            max(12, self.title_bar.height() + 12),
        )
        toast.show()
        toast.raise_()

    def _remove_toast(self, toast: QWidget) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)

    def show_launch_loader(self, title: str, subtitle: str) -> None:
        self.launch_loader.set_message(title, subtitle)
        self.launch_loader.show()
        self.launch_loader.raise_()
        self.launch_loader.activateWindow()

    def hide_launch_loader(self) -> None:
        if self.launch_loader.isVisible():
            self.launch_loader.close()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self.title_bar.sync_window_state()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._centered_once:
            self._centered_once = True
            QTimer.singleShot(0, self._center_window_on_screen)

    def _center_window_on_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return

        geometry = screen.availableGeometry()
        x = geometry.x() + (geometry.width() - self.width()) // 2
        y = geometry.y() + (geometry.height() - self.height()) // 2
        self.move(x, y)

    def _apply_styles(self) -> None:
        self.setFont(QFont("Segoe UI", _scaled_int(10, self._text_scale)))
        style = """
            QMainWindow {
                background: #1e1e1e;
            }
            QWidget {
                color: #d4d4d4;
                font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
                font-size: 8pt;
            }
            QWidget#tabPage {
                background: #1e1e1e;
            }
            QScrollArea,
            QAbstractScrollArea,
            QScrollArea > QWidget,
            QScrollArea > QWidget > QWidget {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4b4b4b;
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5d5d5d;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                background: #1e1e1e;
                height: 10px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #4b4b4b;
                min-width: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #5d5d5d;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: transparent;
                border: none;
            }
            QFrame#heroPanel,
            QFrame#loginCard,
            QFrame#topBar,
            QFrame#sidebar,
            QFrame#panelCard,
            QFrame#contentArea {
                background: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 8px;
            }
            QFrame#sidebar {
                border-radius: 0px;
                border-left: none;
                border-top: none;
                border-bottom: none;
            }
            QFrame#contentArea {
                border-radius: 0px;
                border-right: none;
                border-top: none;
                border-bottom: none;
            }
            QFrame#panelCard {
                border-radius: 6px;
                background: #252526;
            }
            QFrame#loginShell {
                background: #252526;
                border: 1px solid #333333;
                border-radius: 10px;
            }
            QFrame#topBar {
                background: #1f1f1f;
                border-radius: 0px;
                border-left: none;
                border-right: none;
                border-top: none;
                border-bottom: 1px solid #333333;
            }
            QFrame#heroPanel {
                background: #252526;
            }
            QFrame#loginCard {
                background: #252526;
            }
            QFrame#toast {
                background: #202020;
                border: 1px solid #3a3d41;
                border-radius: 6px;
            }
            QFrame#loaderCard {
                background: #252526;
                border: 1px solid #333333;
                border-radius: 12px;
            }
            QDialog#launchLoader {
                background: rgba(0, 0, 0, 0.32);
            }
            QFrame#toast[kind="info"] {
                border-left: 3px solid #007acc;
            }
            QFrame#toast[kind="success"] {
                border-left: 3px solid #6a9955;
            }
            QFrame#toast[kind="warning"] {
                border-left: 3px solid #d7ba7d;
            }
            QFrame#toast[kind="error"] {
                border-left: 3px solid #f48771;
            }
            QFrame#toast[kind="info"] QLabel#toastIcon {
                color: #9cdcfe;
            }
            QFrame#toast[kind="success"] QLabel#toastIcon {
                color: #89d185;
            }
            QFrame#toast[kind="warning"] QLabel#toastIcon {
                color: #d7ba7d;
            }
            QFrame#toast[kind="error"] QLabel#toastIcon {
                color: #f48771;
            }
            QFrame#toast[kind="info"] QLabel#toastText {
                color: #d4d4d4;
            }
            QFrame#toast[kind="success"] QLabel#toastText {
                color: #89d185;
            }
            QFrame#toast[kind="warning"] QLabel#toastText {
                color: #d7ba7d;
            }
            QFrame#toast[kind="error"] QLabel#toastText {
                color: #f48771;
            }
            QLabel#heroBadge {
                color: #569cd6;
                font-size: 8pt;
                font-weight: 700;
                letter-spacing: 0.6px;
            }
            QLabel#loginAppName {
                color: #ffffff;
                font-size: 14pt;
                font-weight: 800;
            }
            QLabel#loginKicker {
                color: #569cd6;
                font-size: 8pt;
                font-weight: 700;
            }
            QLabel#heroTitle {
                color: #ffffff;
                font-size: 18pt;
                font-weight: 800;
            }
            QLabel#heroSubtitle,
            QLabel#heroPoints,
            QLabel#heroFooter,
            QLabel#loginSubtitle,
            QLabel#loginHint,
            QLabel#sectionSubtitle,
            QLabel#sectionHint,
            QLabel#placeholderText,
            QLabel#brandSubtitle {
                color: #94a3b8;
            }
            QLabel#loginTitle {
                color: #ffffff;
                font-size: 16pt;
                font-weight: 800;
            }
            QLabel#loaderTitle {
                color: #ffffff;
                font-size: 12pt;
                font-weight: 800;
            }
            QLabel#loaderSubtitle,
            QLabel#loaderStatus {
                color: #9e9e9e;
            }
            QLabel#loginError {
                color: #fda4af;
                min-height: 18px;
            }
            QLabel#brandTitle {
                color: #ffffff;
                font-size: 10pt;
                font-weight: 800;
            }
            QLabel#versionBadge {
                background: #007acc;
                color: white;
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 7pt;
                font-weight: 700;
            }
            QLabel#statusBadge {
                background: #1e4620;
                color: #89d185;
                border: 1px solid #2d5e34;
                border-radius: 4px;
                padding: 3px 7px;
                font-weight: 700;
            }
            QLabel#sectionTitle {
                color: #ffffff;
                font-size: 10pt;
                font-weight: 800;
            }
            QLabel#fieldLabel {
                color: #c8c8c8;
                min-width: 100px;
            }
            QLabel#windowPill {
                background: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4b4b4b;
                border-radius: 4px;
                padding: 3px 8px;
                font-weight: 700;
                max-width: 110px;
            }
            QLabel#toastIcon {
                color: #9cdcfe;
                font-weight: 900;
            }
            QLabel#toastText {
                color: #d4d4d4;
            }
            QLineEdit,
            QTextEdit,
            QSpinBox,
            QComboBox,
            QTableWidget {
                background: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 5px 8px;
            }
            QLineEdit:focus,
            QTextEdit:focus,
            QSpinBox:focus,
            QComboBox:focus {
                border: 1px solid #007acc;
            }
            QSpinBox {
                min-height: 18px;
            }
            QTableWidget {
                gridline-color: #333333;
                selection-background-color: #094771;
            }
            QHeaderView::section {
                background: #2d2d30;
                color: #d4d4d4;
                border: none;
                padding: 6px 8px;
                font-weight: 700;
            }
            QListWidget {
                background: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 3px;
                color: #d4d4d4;
            }
            QListWidget::item {
                padding: 5px 7px;
                margin: 1px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: #094771;
            }
            QTabWidget::pane {
                border: none;
                background: transparent;
            }
            QTabBar::tab {
                background: #2d2d30;
                color: #d4d4d4;
                padding: 7px 10px;
                margin-right: 6px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 96px;
            }
            QTabBar::tab:selected {
                background: #007acc;
                color: white;
            }
            QPushButton {
                border: none;
                border-radius: 4px;
                padding: 6px 10px;
                font-weight: 700;
            }
            QPushButton#macTrafficLightButton {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            QPushButton#macTrafficLightButton:pressed {
                transform: none;
            }
            QPushButton#primaryButton,
            QPushButton#blastButton {
                background: #0e639c;
                color: white;
            }
            QPushButton#secondaryButton {
                background: #3c3c3c;
                color: #d4d4d4;
            }
            QPushButton#warningButton {
                background: #4d3d1f;
                color: #d7ba7d;
            }
            QPushButton#dangerButton {
                background: #5a1d1d;
                color: #f48771;
            }
            QPushButton#closeButton {
                background: #5a1d1d;
                color: #ffffff;
                border: 1px solid #733838;
                border-radius: 4px;
                padding: 0px;
                font-weight: 900;
            }
            QPushButton#closeButton:hover {
                background: #c43c3c;
                color: white;
            }
            QPushButton#windowControlButton {
                background: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #4b4b4b;
                border-radius: 4px;
                padding: 0px;
                font-weight: 800;
            }
            QPushButton#windowControlButton:hover {
                background: #505050;
                color: white;
            }
            QPushButton:checked {
                background: #007acc;
                color: white;
            }
            QPushButton:pressed {
                transform: translateY(1px);
            }
            QProgressBar {
                background: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                text-align: center;
                color: #d4d4d4;
                height: 20px;
            }
            QProgressBar::chunk {
                background: #007acc;
                border-radius: 4px;
            }
            QLabel#miniStatLabel {
                color: #9e9e9e;
                font-size: 8pt;
                text-transform: uppercase;
            }
            QLabel#countValue {
                color: #ffffff;
                font-size: 13pt;
                font-weight: 800;
            }
            QFrame#miniStat {
                background: #252526;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QFrame#sessionRow {
                background: #252526;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QLabel#sessionDot {
                color: #569cd6;
                font-size: 8pt;
            }
            QLabel#sessionTitleSmall {
                color: #ffffff;
                font-weight: 700;
                font-size: 8.5pt;
            }
            QLabel#sessionState {
                color: #9e9e9e;
                font-size: 7.5pt;
            }
            QPushButton#sessionAction {
                background: #0e639c;
                color: white;
                padding: 2px 6px;
                border-radius: 4px;
                min-height: 18px;
                font-size: 7.5pt;
            }
            QTextEdit#activityList,
            QTextEdit#bodyEditor,
            QTextEdit#htmlEditor {
                background: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                color: #d4d4d4;
                font-family: Consolas, "Cascadia Code", "Courier New", monospace;
            }
            QFrame#panelCard QWidget QLabel#sectionHint {
                color: #9e9e9e;
            }
            QFrame#dialogCard {
                background: #252526;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QFrame#confirmCard {
                background: #252526;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QDialog#outputDialog {
                background: #1e1e1e;
            }
            QDialog#previewDialog {
                background: rgba(18, 18, 18, 0.96);
            }
            QDialog#confirmDialog {
                background: rgba(0, 0, 0, 0.28);
            }
            QLabel#confirmTitle {
                color: #ffffff;
                font-size: 11pt;
                font-weight: 800;
            }
            QLabel#confirmText {
                color: #d4d4d4;
            }
            QDialog#outputDialog QLabel,
            QDialog#outputDialog QRadioButton {
                color: #d4d4d4;
            }
            QDialog#outputDialog QDialogButtonBox {
                spacing: 8px;
            }
            QFrame#previewCard {
                background: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 8px;
            }
            QDialog#previewDialog QPushButton#secondaryButton {
                background: #2d2d30;
                color: #d4d4d4;
                padding: 5px 10px;
                min-width: 54px;
            }
            QDialog#previewDialog QPushButton#secondaryButton:hover {
                background: #3e3e42;
                color: white;
            }
            QLabel#previewMeta {
                color: #9e9e9e;
            }
            QTextBrowser#previewBrowser {
                background: #111827;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 12px;
                font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif;
                font-size: 9pt;
            }
            QTextEdit#sourceEditor {
                background: #0f172a;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
                font-family: Consolas, "Cascadia Code", "Courier New", monospace;
                font-size: 8.5pt;
            }
            QTextBrowser#previewBrowser QScrollBar:vertical,
            QTextBrowser#previewBrowser QScrollBar:horizontal {
                background: #111827;
            }
            """
        import re

        def scale_font(match) -> str:
            value = float(match.group(1))
            return f"font-size: {value * self._text_scale:.1f}pt;"

        style = re.sub(r"font-size:\s*([0-9]+(?:\.[0-9]+)?)pt;", scale_font, style)
        style = style.replace("min-width: 96px;", f"min-width: {_scaled_int(96, self._scale)}px;")
        style = style.replace("width: 10px;", f"width: {_scaled_int(10, self._scale)}px;")
        style = style.replace("height: 10px;", f"height: {_scaled_int(10, self._scale)}px;")
        self.setStyleSheet(style)

    def show_login(self) -> None:
        self.hide_launch_loader()
        self.title_bar.set_state("", False)
        self.stack.setCurrentWidget(self.login_page)

    def show_dashboard(self) -> None:
        self.hide_launch_loader()
        self.title_bar.set_state(self.state.username, self.state.logged_in)
        self.dashboard_page.refresh()
        self.stack.setCurrentWidget(self.dashboard_page)

    def handle_login(self, username: str, auth_token: str = "") -> None:
        self.state.username = username
        self.state.logged_in = True
        self.state.auth_token = auth_token
        self.title_bar.set_state(self.state.username, self.state.logged_in)
        self.dashboard_page.load_user_workspace()
        self.show_dashboard()
        self.dashboard_page._log_action("User authenticated")
        self.show_toast("Signed in successfully", "success")

    def handle_logout(self) -> None:
        if self.state.logged_in and self.state.username:
            self.dashboard_page._log_action("User signed out")
        self.hide_launch_loader()
        self.dashboard_page._terminate_browser_sessions()
        self.state = AppState()
        self.dashboard_page.state = self.state
        self.dashboard_page.refresh()
        self.login_page.username_input.setText(DEFAULT_USERNAME)
        self.login_page.password_input.setText(DEFAULT_PASSWORD)
        self.login_page.error_label.setText("")
        self.show_login()
        self.show_toast("Logged out", "warning")


def main() -> int:
    try:
        ensure_api_server()
    except Exception as exc:
        print(f"Local login API failed to start: {exc}")

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

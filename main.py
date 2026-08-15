import sys
import html
import csv
import json
import os
import re
import subprocess
import shutil
import ssl
import sqlite3
import urllib.error
import urllib.request
from math import ceil, sqrt
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
from typing import Callable

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
    QAbstractItemView,
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
    QHeaderView,
)


APP_TITLE = "EzyMailer"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
IS_MAC = sys.platform == "darwin"
MAX_BODY_TABS = 50
MAX_ATTACHMENT_TABS = 50
MAX_SUBJECTS = 100
LOCAL_CACHE_DIR = (
    Path.home() / "Library" / "Application Support" / APP_TITLE
    if IS_MAC
    else Path.home() / ".ezymailer"
)
LEGACY_LOCAL_CACHE_DIR = Path.home() / ".ezymailer"
LEGACY_LOCAL_CACHE_DB = LEGACY_LOCAL_CACHE_DIR / "local_drafts.sqlite3"
LOCAL_CACHE_DB = LOCAL_CACHE_DIR / "local_drafts.sqlite3"
LOCAL_ATTACHMENT_STATE_KEY = "attachment_content_state"
LOCAL_SUBJECT_STATE_KEY = "subject_content_state"
LOCAL_BODY_STATE_KEY = "body_content_state"
LOCAL_SETTINGS_STATE_KEY = "sending_settings_state"
ROLE_LOCAL_ONLY = Qt.UserRole + 10
ROLE_LOCAL_DRAFT_ID = Qt.UserRole + 11


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


def _is_subject_content_row(row: dict[str, object]) -> bool:
    if not isinstance(row, dict):
        return False
    if bool(row.get("local_only")) and str(row.get("content_type") or "") == "subject":
        return True
    content_type = str(row.get("content_type") or "")
    details = row.get("details_json")
    kind = ""
    if isinstance(details, str):
        try:
            parsed = json.loads(details)
            if isinstance(parsed, dict):
                kind = str(parsed.get("kind") or "")
        except Exception:
            kind = ""
    elif isinstance(details, dict):
        kind = str(details.get("kind") or "")
    return content_type in {"subject", "subject-draft"} or kind in {"subject", "subject-draft"}


def _subject_rows_from_content(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    subject_rows: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not _is_subject_content_row(row):
            continue
        subject = str(row.get("subject") or "").strip()
        if not subject:
            continue
        subject_rows.append(row)
    return subject_rows


def _subject_count_text(count: int) -> str:
    return f"{count}/{MAX_SUBJECTS} subjects"


def _ensure_local_cache_db() -> None:
    LOCAL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(LOCAL_CACHE_DIR, 0o700)
    except Exception:
        pass
    if not LOCAL_CACHE_DB.exists() and LEGACY_LOCAL_CACHE_DB.exists():
        try:
            shutil.copy2(LEGACY_LOCAL_CACHE_DB, LOCAL_CACHE_DB)
        except Exception:
            pass
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS draft_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT NOT NULL,
                title TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                body_text TEXT NOT NULL DEFAULT '',
                body_html TEXT NOT NULL DEFAULT '',
                details_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS attachment_state (
                state_key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()
    finally:
        connection.close()
    try:
        os.chmod(LOCAL_CACHE_DB, 0o600)
    except Exception:
        pass


def _save_local_draft(
    content_type: str,
    title: str,
    subject: str = "",
    body_text: str = "",
    body_html: str = "",
    details: dict[str, object] | None = None,
) -> int:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO draft_content (content_type, title, subject, body_text, body_html, details_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                content_type,
                title,
                subject,
                body_text,
                body_html,
                json.dumps(details or {}, ensure_ascii=False),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid or 0)
    finally:
        connection.close()


def _update_local_draft(
    draft_id: int,
    content_type: str,
    title: str,
    subject: str = "",
    body_text: str = "",
    body_html: str = "",
    details: dict[str, object] | None = None,
) -> None:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    try:
        connection.execute(
            """
            UPDATE draft_content
            SET content_type = ?,
                title = ?,
                subject = ?,
                body_text = ?,
                body_html = ?,
                details_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                content_type,
                title,
                subject,
                body_text,
                body_html,
                json.dumps(details or {}, ensure_ascii=False),
                draft_id,
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _delete_local_draft(draft_id: int) -> None:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    try:
        connection.execute("DELETE FROM draft_content WHERE id = ?", (draft_id,))
        connection.commit()
    finally:
        connection.close()


def _delete_local_drafts(content_type: str | None = None) -> int:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    try:
        cursor = connection.cursor()
        if content_type:
            cursor.execute("DELETE FROM draft_content WHERE content_type = ?", (content_type,))
        else:
            cursor.execute("DELETE FROM draft_content")
        connection.commit()
        return int(cursor.rowcount or 0)
    finally:
        connection.close()


def _list_local_drafts(content_type: str | None = None) -> list[dict[str, object]]:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.cursor()
        if content_type:
            cursor.execute(
                """
                SELECT id, content_type, title, subject, body_text, body_html, details_json, created_at, updated_at
                FROM draft_content
                WHERE content_type = ?
                ORDER BY id ASC
                """,
                (content_type,),
            )
        else:
            cursor.execute(
                """
                SELECT id, content_type, title, subject, body_text, body_html, details_json, created_at, updated_at
                FROM draft_content
                ORDER BY id ASC
                """
            )
        rows = cursor.fetchall() or []
        payload: list[dict[str, object]] = []
        for row in rows:
            payload.append(
                {
                    "id": int(row["id"]),
                    "content_type": str(row["content_type"]),
                    "title": str(row["title"]),
                    "subject": str(row["subject"]),
                    "body_text": str(row["body_text"]),
                    "body_html": str(row["body_html"]),
                    "details_json": row["details_json"],
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"]),
                    "local_only": True,
                }
            )
        return payload
    finally:
        connection.close()


def _upsert_attachment_state(payload: dict[str, object]) -> None:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    try:
        connection.execute(
            """
            INSERT INTO attachment_state (state_key, payload_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(state_key) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (LOCAL_ATTACHMENT_STATE_KEY, json.dumps(payload, ensure_ascii=False)),
        )
        connection.commit()
    finally:
        connection.close()


def _load_attachment_state() -> dict[str, object]:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    connection.row_factory = sqlite3.Row
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT payload_json
            FROM attachment_state
            WHERE state_key = ?
            """,
            (LOCAL_ATTACHMENT_STATE_KEY,),
        )
        row = cursor.fetchone()
        if not row:
            return {}
        raw_payload = row["payload_json"]
        if not raw_payload:
            return {}
        try:
            payload = json.loads(str(raw_payload))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}
    finally:
        connection.close()


def _delete_attachment_state() -> None:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    try:
        connection.execute(
            "DELETE FROM attachment_state WHERE state_key = ?",
            (LOCAL_ATTACHMENT_STATE_KEY,),
        )
        connection.commit()
    finally:
        connection.close()


def _upsert_ui_state(state_key: str, payload: dict[str, object]) -> None:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ui_state (
                state_key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO ui_state (state_key, payload_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(state_key) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (state_key, json.dumps(payload, ensure_ascii=False)),
        )
        connection.commit()
    finally:
        connection.close()


def _load_ui_state(state_key: str) -> dict[str, object]:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ui_state (
                state_key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT payload_json
            FROM ui_state
            WHERE state_key = ?
            """,
            (state_key,),
        )
        row = cursor.fetchone()
        if not row:
            return {}
        raw_payload = str(row["payload_json"] or "")
        if not raw_payload:
            return {}
        try:
            payload = json.loads(raw_payload)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}
    finally:
        connection.close()


def _delete_ui_state(state_key: str) -> None:
    _ensure_local_cache_db()
    connection = sqlite3.connect(LOCAL_CACHE_DB)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ui_state (
                state_key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute("DELETE FROM ui_state WHERE state_key = ?", (state_key,))
        connection.commit()
    finally:
        connection.close()


def _is_local_draft_item(item: QTableWidgetItem | QListWidgetItem | None) -> bool:
    if item is None:
        return False
    return bool(item.data(ROLE_LOCAL_ONLY))


def _local_draft_id_from_item(item: QTableWidgetItem | QListWidgetItem | None) -> int | None:
    if item is None:
        return None
    value = item.data(ROLE_LOCAL_DRAFT_ID)
    return int(value) if value else None


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
    ai_api_key: str = ""
    ai_model: str = ""
    ai_connected: bool = False
    sender_limit: int = 500
    delay_from: float = 0.5
    delay_to: float = 1.0
    retry_count: int = 3
    retry_enabled: bool = True
    delay_type: str = "Random range"
    email_send_order: str = "Sequential"
    window_send_mode: str = "Parallel"
    ai_available_models: list[str] = field(default_factory=list)


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
        self.local_draft_id: int | None = None
        self.local_only = False
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

    def set_content(self, title: str, mode: str, plain_text: str, html_text: str, *, local_only: bool = False) -> None:
        self.blockSignals(True)
        self.title_input.blockSignals(True)
        self.plain_editor.blockSignals(True)
        self.html_editor.blockSignals(True)
        try:
            self.local_only = local_only
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


class AttachmentDraftEditor(QWidget):
    contentChanged = Signal()
    titleChanged = Signal(str)
    previewRequested = Signal()

    def __init__(self, scale: float = 1.0):
        super().__init__()
        self._scale = scale
        self.draft_id: int | None = None
        self.local_draft_id: int | None = None
        self.local_only = False
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
        self.title_input.setToolTip("Name this content tab")
        self.preview_button = QPushButton("Preview")
        self.preview_button.setObjectName("secondaryButton")
        self.preview_button.setVisible(False)
        self.preview_button.clicked.connect(self.previewRequested.emit)
        title_row.addWidget(title_label)
        title_row.addWidget(self.title_input, 1)
        title_row.addWidget(self.preview_button)
        layout.addLayout(title_row)

        self.html_editor = QTextEdit()
        self.html_editor.setObjectName("bodyEditor")
        self.html_editor.setPlaceholderText("<!-- Paste HTML content here -->")
        self.html_editor.setToolTip("Compose the HTML attachment content")
        self.html_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.html_editor, 1)

        self.title_input.textChanged.connect(lambda _text: self.titleChanged.emit(self.title_text()))
        self.title_input.textChanged.connect(self.contentChanged.emit)
        self.html_editor.textChanged.connect(self.contentChanged.emit)
        self.html_editor.textChanged.connect(self._sync_preview_button_state)
        self._sync_preview_button_state()

    def title_text(self) -> str:
        return self.title_input.text().strip()

    def set_content(self, title: str, html_text: str, *, local_only: bool = False) -> None:
        self.blockSignals(True)
        self.title_input.blockSignals(True)
        self.html_editor.blockSignals(True)
        try:
            self.local_only = local_only
            self.title_input.setText(title)
            self.html_editor.setPlainText(html_text)
            self._sync_preview_button_state()
        finally:
            self.title_input.blockSignals(False)
            self.html_editor.blockSignals(False)
            self.blockSignals(False)

    def payload(self) -> dict[str, str]:
        return {
            "title": self.title_text(),
            "html_text": self.html_editor.toPlainText(),
        }

    def _sync_preview_button_state(self) -> None:
        self.preview_button.setVisible(bool(self.html_editor.toPlainText().strip()))

class SubjectDraftsDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        auth_token: str,
        scale: float = 1.0,
        on_changed=None,
    ):
        super().__init__(parent)
        self._scale = scale
        self._auth_token = auth_token
        self._on_changed = on_changed
        self._loading_subjects = False
        self.setWindowTitle("Subjects")
        self.setModal(True)
        self.setObjectName("confirmDialog")
        self.setMinimumSize(_scaled_int(900, self._scale), _scaled_int(660, self._scale))
        self._build_ui()
        self.resize(_scaled_int(1060, self._scale), _scaled_int(760, self._scale))
        self._load_subjects()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale))
        layout.setSpacing(_scaled_int(10, self._scale))

        header = QLabel("Manage Subjects")
        header.setObjectName("sectionTitle")
        subtitle = QLabel("Click any subject to edit inline. Use the cross button to remove a row.")
        subtitle.setObjectName("sectionSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(header)
        layout.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("dialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            _scaled_int(12, self._scale),
            _scaled_int(12, self._scale),
            _scaled_int(12, self._scale),
            _scaled_int(12, self._scale),
        )
        card_layout.setSpacing(_scaled_int(8, self._scale))

        toolbar = QHBoxLayout()
        toolbar.setSpacing(_scaled_int(8, self._scale))
        self.new_button = QPushButton("New")
        self.import_button = QPushButton("Import CSV")
        self.remove_all_button = QPushButton("Remove All")
        toolbar.addWidget(self.new_button)
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.remove_all_button)
        toolbar.addStretch()
        card_layout.addLayout(toolbar)

        self.subject_table = QTableWidget(0, 2)
        self.subject_table.setObjectName("subjectTable")
        self.subject_table.setHorizontalHeaderLabels(["Subject", ""])
        self.subject_table.verticalHeader().setVisible(False)
        self.subject_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.subject_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.subject_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.subject_table.itemChanged.connect(self._on_item_changed)
        self.subject_table.cellClicked.connect(self._on_cell_clicked)
        self.subject_table.horizontalHeader().setStretchLastSection(False)
        self.subject_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.subject_table.setColumnWidth(1, _scaled_int(44, self._scale))
        card_layout.addWidget(self.subject_table, 1)

        self.count_label = QLabel(_subject_count_text(0))
        self.count_label.setObjectName("sectionSubtitle")
        card_layout.addWidget(self.count_label)
        layout.addWidget(card, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Done")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.new_button.clicked.connect(self._new_subject)
        self.import_button.clicked.connect(self._import_subjects_from_csv)
        self.remove_all_button.clicked.connect(self._delete_all_subjects)

    def selected_subject(self) -> str:
        current_item = self.subject_table.currentItem()
        if current_item is None:
            return ""
        return self._table_item_subject(current_item).strip()

    def _table_item_record_id(self, item: QTableWidgetItem | None) -> int | None:
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return int(value) if value else None

    def _table_item_subject(self, item: QTableWidgetItem | None) -> str:
        if item is None:
            return ""
        return str(item.data(Qt.UserRole + 2) or "")

    def _set_item_data(
        self,
        item: QTableWidgetItem,
        record_id: int | None,
        title: str,
        subject: str,
        *,
        local_only: bool = False,
        local_draft_id: int | None = None,
    ) -> None:
        item.setData(Qt.UserRole, record_id)
        item.setData(Qt.UserRole + 1, title)
        item.setData(Qt.UserRole + 2, subject)
        item.setData(ROLE_LOCAL_ONLY, local_only)
        item.setData(ROLE_LOCAL_DRAFT_ID, local_draft_id)
        item.setText(subject or title or "Untitled Subject")
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)

    def _set_row_remove_button(self, row: int) -> None:
        button = QPushButton("×")
        button.setObjectName("dangerButton")
        button.setToolTip("Remove subject")
        button.setFixedSize(_scaled_int(28, self._scale), _scaled_int(28, self._scale))
        button.clicked.connect(lambda _checked=False, r=row: self._delete_subject_row(r))
        container = QWidget()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setAlignment(Qt.AlignCenter)
        row_layout.addWidget(button)
        self.subject_table.setCellWidget(row, 1, container)

    def _refresh_remove_buttons(self) -> None:
        for row in range(self.subject_table.rowCount()):
            self._set_row_remove_button(row)

    def _selected_subject_row(self) -> int:
        item = self.subject_table.currentItem()
        if item is None:
            return -1
        return self.subject_table.row(item)

    def _update_count_label(self) -> None:
        self.count_label.setText(_subject_count_text(self.subject_table.rowCount()))

    def _notify_parent_subjects_changed(self) -> None:
        if callable(self._on_changed):
            try:
                self._on_changed()
            except Exception:
                pass
            return
        parent = self.parentWidget()
        if parent is not None and hasattr(parent, "_load_subjects"):
            try:
                parent._load_subjects()
            except Exception:
                pass

    def _commit_active_subject_row(self) -> None:
        row = self._selected_subject_row()
        if row < 0:
            return
        item = self.subject_table.item(row, 0)
        if item is None:
            return
        subject = item.text().strip()
        if not subject:
            return
        self._save_subject_row(row, subject)

    def _delete_subject_row(self, row: int) -> None:
        if row < 0 or row >= self.subject_table.rowCount():
            return
        self.subject_table.removeRow(row)
        self._refresh_remove_buttons()
        if self.subject_table.rowCount() > 0:
            self.subject_table.setCurrentCell(min(row, self.subject_table.rowCount() - 1), 0)
        self._update_count_label()
        self._save_subject_state()
        self._notify_parent_subjects_changed()

    def _new_subject(self) -> None:
        self._commit_active_subject_row()
        if self.subject_table.rowCount() >= MAX_SUBJECTS:
            self._update_count_label()
            return
        self._loading_subjects = True
        self.subject_table.blockSignals(True)
        try:
            row = self.subject_table.rowCount()
            self.subject_table.insertRow(row)
            item = QTableWidgetItem()
            self._set_item_data(item, None, "Subject", "")
            self.subject_table.setItem(row, 0, item)
            self._set_row_remove_button(row)
            self.subject_table.setCurrentCell(row, 0)
        finally:
            self.subject_table.blockSignals(False)
            self._loading_subjects = False
        self._update_count_label()
        item = self.subject_table.item(self.subject_table.currentRow(), 0)
        if item is not None:
            self.subject_table.editItem(item)

    def _delete_all_subjects(self) -> None:
        if self.subject_table.rowCount() == 0:
            return
        reply = QMessageBox.question(
            self,
            "Remove All Subjects",
            "Remove every subject from the list?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            _delete_ui_state(LOCAL_SUBJECT_STATE_KEY)
        except Exception:
            return
        self.subject_table.blockSignals(True)
        try:
            self.subject_table.setRowCount(0)
        finally:
            self.subject_table.blockSignals(False)
        self._update_count_label()
        self._notify_parent_subjects_changed()

    def _import_subjects_from_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Subjects CSV",
            "",
            "CSV files (*.csv);;All files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        imported_subjects: list[str] = []
        try:
            if path.suffix.lower() != ".csv":
                raise ValueError("Please choose a CSV file.")
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    for value in row:
                        subject = str(value or "").strip()
                        if subject:
                            imported_subjects.append(subject)
            if len(imported_subjects) > 100:
                raise ValueError("CSV can contain at most 100 subjects.")
            if self.subject_table.rowCount() + len(imported_subjects) > MAX_SUBJECTS:
                raise ValueError("Total subjects cannot exceed 100.")
            for subject in imported_subjects:
                if len(subject) > 300:
                    raise ValueError("Each subject must be 300 characters or less.")
        except Exception:
            self.count_label.setText("Unable to import CSV")
            return

        if not imported_subjects:
            self.count_label.setText("No subjects found in CSV")
            return

        if self.subject_table.rowCount() >= MAX_SUBJECTS:
            self.count_label.setText(_subject_count_text(self.subject_table.rowCount()))
            return

        added = 0
        self._loading_subjects = True
        self.subject_table.blockSignals(True)
        try:
            current_rows = self._subject_rows()
            if self.subject_table.rowCount() + len(imported_subjects) > MAX_SUBJECTS:
                raise ValueError("Total subjects cannot exceed 100.")
            if len(current_rows) + len(imported_subjects) > MAX_SUBJECTS:
                raise ValueError("Total subjects cannot exceed 100.")
            for subject in imported_subjects:
                if len(subject) > 300:
                    raise ValueError("Each subject must be 300 characters or less.")
            rows = current_rows[:]
            for subject in imported_subjects:
                rows.append({"title": subject[:64] or "Subject", "subject": subject})
            self._apply_subject_rows(rows)
            added = len(imported_subjects)
        finally:
            self.subject_table.blockSignals(False)
            self._loading_subjects = False
        self._refresh_remove_buttons()
        self._update_count_label()
        self._notify_parent_subjects_changed()

    def _load_subjects(self) -> None:
        filtered_rows = self._subject_rows()
        selected_index = int(_load_ui_state(LOCAL_SUBJECT_STATE_KEY).get("selected_index") or -1)
        if not filtered_rows:
            filtered_rows = []
        self._loading_subjects = True
        self.subject_table.blockSignals(True)
        try:
            self._apply_subject_rows(filtered_rows, selected_index=selected_index)
        finally:
            self.subject_table.blockSignals(False)
            self._loading_subjects = False

        self._update_count_label()

    def _subject_rows(self) -> list[dict[str, object]]:
        payload = _load_ui_state(LOCAL_SUBJECT_STATE_KEY)
        rows = payload.get("subjects") or []
        result: list[dict[str, object]] = []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                subject = str(row.get("subject") or row.get("title") or "").strip()
                if not subject:
                    continue
                result.append(
                    {
                        "title": str(row.get("title") or subject[:64] or "Subject"),
                        "subject": subject,
                    }
                )
        return result

    def _apply_subject_rows(self, rows: list[dict[str, object]], *, selected_index: int = -1) -> None:
        self.subject_table.setRowCount(0)
        for row in rows:
            row_index = self.subject_table.rowCount()
            self.subject_table.insertRow(row_index)
            item = QTableWidgetItem()
            title = str(row.get("title") or row.get("subject") or "Subject")
            subject = str(row.get("subject") or row.get("title") or "")
            self._set_item_data(item, None, title, subject, local_only=True, local_draft_id=None)
            self.subject_table.setItem(row_index, 0, item)
            self._set_row_remove_button(row_index)
        if self.subject_table.rowCount() > 0:
            if 0 <= selected_index < self.subject_table.rowCount():
                self.subject_table.setCurrentCell(selected_index, 0)
            else:
                self.subject_table.setCurrentCell(self.subject_table.rowCount() - 1, 0)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading_subjects:
            return
        if item is None:
            return
        row = self.subject_table.row(item)
        if row < 0 or self.subject_table.column(item) != 0:
            return
        self._save_subject_row(row, item.text().strip())

    def _on_cell_clicked(self, row: int, column: int) -> None:
        if self._loading_subjects or row < 0 or column != 0:
            return
        item = self.subject_table.item(row, 0)
        if item is None:
            return
        self.subject_table.editItem(item)

    def _save_subject_row(self, row: int, subject_text: str | None = None) -> None:
        if self._loading_subjects or row < 0 or row >= self.subject_table.rowCount():
            return
        item = self.subject_table.item(row, 0)
        if item is None:
            return
        subject = (subject_text if subject_text is not None else item.text()).strip()
        if not subject:
            return
        if len(subject) > 300:
            self.count_label.setText("Subject must be 300 characters or less")
            return
        if not self._table_item_record_id(item) and self.subject_table.rowCount() >= MAX_SUBJECTS:
            self.count_label.setText(_subject_count_text(self.subject_table.rowCount()))
            return
        title = subject[:64] or "Subject"
        try:
            self.subject_table.blockSignals(True)
            try:
                self._set_item_data(item, None, title, subject, local_only=True, local_draft_id=None)
            finally:
                self.subject_table.blockSignals(False)
            self._update_count_label()
            self._save_subject_state()
        except Exception:
            return

        self._notify_parent_subjects_changed()

    def _save_subject_state(self) -> None:
        rows: list[dict[str, object]] = []
        for row in range(self.subject_table.rowCount()):
            item = self.subject_table.item(row, 0)
            if item is None:
                continue
            subject = item.text().strip()
            if not subject:
                continue
            rows.append({"title": subject[:64] or "Subject", "subject": subject})
        _upsert_ui_state(
            LOCAL_SUBJECT_STATE_KEY,
            {
                "subjects": rows,
                "selected_index": self.subject_table.currentRow(),
            },
        )


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


class FileFormatDialog(QDialog):
    def __init__(self, parent=None, scale: float = 1.0, selected_format: str = "PDF document"):
        super().__init__(parent)
        self._scale = scale
        self._selected_format = selected_format
        self.setWindowTitle("Choose File Format")
        self.setModal(True)
        self.setObjectName("outputDialog")
        self._buttons: list[QCheckBox] = []
        self._random_checkbox: QCheckBox | None = None
        self.auto_name: QRadioButton | None = None
        self.custom_name: QRadioButton | None = None
        self.custom_name_input: QLineEdit | None = None
        self.file_extension_label: QLabel | None = None
        self._build_ui()
        self._apply_initial_selection()
        self._wire_exclusive_selection()
        self._sync_file_name_controls()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(_scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale), _scaled_int(14, self._scale))
        layout.setSpacing(_scaled_int(10, self._scale))

        card = QFrame()
        card.setObjectName("dialogCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale))
        card_layout.setSpacing(_scaled_int(8, self._scale))

        title = QLabel("FILE FORMAT")
        title.setObjectName("sectionTitle")
        card_layout.addWidget(title)

        self._random_checkbox = QCheckBox("Random format")
        self._random_checkbox.setToolTip("Choose a random format from the selected file types")
        self._random_checkbox.toggled.connect(self._handle_random_toggled)
        card_layout.addWidget(self._random_checkbox)

        for label in [
            "PDF document",
            "Excel spreadsheet (XLSX)",
            "Excel template (XLTX)",
            "PowerPoint presentation (PPTX)",
            "PowerPoint slideshow (PPSX)",
            "Word document (DOCX)",
        ]:
            button = QCheckBox(label)
            if label == self._selected_format:
                button.setChecked(True)
            button.toggled.connect(self._handle_format_toggled)
            self._buttons.append(button)
            card_layout.addWidget(button)

        layout.addWidget(card)

        file_card = QFrame()
        file_card.setObjectName("dialogCard")
        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(_scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale), _scaled_int(12, self._scale))
        file_layout.setSpacing(_scaled_int(8, self._scale))

        file_title = QLabel("FILE NAME")
        file_title.setObjectName("sectionTitle")
        file_layout.addWidget(file_title)

        self.auto_name = QRadioButton("Auto-generate a unique name")
        self.custom_name = QRadioButton("Use a custom name")
        self.auto_name.setChecked(True)
        self.auto_name.toggled.connect(self._sync_file_name_controls)
        self.custom_name.toggled.connect(self._sync_file_name_controls)
        file_layout.addWidget(self.auto_name)

        custom_row = QHBoxLayout()
        custom_row.setContentsMargins(0, 0, 0, 0)
        custom_row.setSpacing(_scaled_int(8, self._scale))
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText("Enter file name")
        self.file_extension_label = QLabel(self._format_extension())
        custom_row.addWidget(self.custom_name)
        custom_row.addWidget(self.custom_name_input, 1)
        custom_row.addWidget(self.file_extension_label)
        file_layout.addLayout(custom_row)
        layout.addWidget(file_card)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _apply_initial_selection(self) -> None:
        if self._random_checkbox is None:
            return
        current = (self._selected_format or "").strip()
        if not current:
            return
        if current == "Random format":
            self._random_checkbox.setChecked(True)
            return
        current_values = {part.strip() for part in current.split(",") if part.strip()}
        for button in self._buttons:
            if button.text() in current_values:
                button.setChecked(True)

    def _wire_exclusive_selection(self) -> None:
        # Keep the random option mutually exclusive with specific file formats.
        if self._random_checkbox is not None:
            self._random_checkbox.setTristate(False)
        for button in self._buttons:
            button.setTristate(False)

    def _handle_random_toggled(self, checked: bool) -> None:
        if not checked:
            return
        for button in self._buttons:
            if button.isChecked():
                button.blockSignals(True)
                try:
                    button.setChecked(False)
                finally:
                    button.blockSignals(False)
        self._sync_file_name_controls()

    def _handle_format_toggled(self, checked: bool) -> None:
        if not checked or self._random_checkbox is None:
            return
        if self._random_checkbox.isChecked():
            self._random_checkbox.blockSignals(True)
            try:
                self._random_checkbox.setChecked(False)
            finally:
                self._random_checkbox.blockSignals(False)
        self._sync_file_name_controls()

    def selected_format(self) -> str:
        if self._random_checkbox is not None and self._random_checkbox.isChecked():
            return "Random format"
        selected = [button.text() for button in self._buttons if button.isChecked()]
        if selected:
            if len(selected) == 1:
                return selected[0]
            return ", ".join(selected)
        return self._selected_format

    def _format_extension(self) -> str:
        selected = [button.text() for button in self._buttons if button.isChecked()]
        if len(selected) != 1:
            return ".out"
        mapping = {
            "PDF document": ".pdf",
            "Excel spreadsheet (XLSX)": ".xlsx",
            "Excel template (XLTX)": ".xltx",
            "PowerPoint presentation (PPTX)": ".pptx",
            "PowerPoint slideshow (PPSX)": ".ppsx",
            "Word document (DOCX)": ".docx",
        }
        return mapping.get(selected[0], ".out")

    def _sync_file_name_controls(self) -> None:
        auto_checked = bool(self.auto_name and self.auto_name.isChecked())
        if self.custom_name_input is not None:
            self.custom_name_input.setEnabled(not auto_checked)
        if self.file_extension_label is not None:
            self.file_extension_label.setText(self._format_extension())


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
        self.subject_import_button = QPushButton("Import CSV")
        self.subject_count_label = QLabel(_subject_count_text(0))
        self.body_tabs = QTabWidget()
        self.body_add_button = QPushButton("+")
        self.body_upload_button = QPushButton("Upload")
        self.body_refresh_button = QPushButton("Reset Body")
        self.attach_tabs = QTabWidget()
        self.attach_add_button = QPushButton("+")
        self.attach_upload_button = QPushButton("Upload")
        self.attach_reset_button = QPushButton("Reset Content")
        self.attach_convert_checkbox = QCheckBox("Convert")
        self.attach_choose_format_button = QPushButton("Choose Format")
        self.attach_format_value = "PDF document"
        self.attach_format_label = QLabel(self._attachment_format_summary(self.attach_format_value))
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
        self.sender_limit = QSpinBox()
        self.delay_from = QDoubleSpinBox()
        self.delay_to = QDoubleSpinBox()
        self.retry_count = QSpinBox()
        self.retry_enable_checkbox = QCheckBox("Enable")
        self.ai_provider_combo = QComboBox()
        self.ai_api_key_input = QLineEdit()
        self.ai_connect_button = QPushButton("Connect")
        self.ai_status_label = QLabel("Not connected")
        self.ai_model_combo = QComboBox()
        self.delay_fixed_radio = QRadioButton("Fixed")
        self.delay_random_radio = QRadioButton("Random range")
        self.delay_human_radio = QRadioButton("Human-like pattern")
        self.send_seq_radio = QRadioButton("Sequential")
        self.send_rand_radio = QRadioButton("Random shuffle")
        self.window_parallel_radio = QRadioButton("Parallel (all windows at once)")
        self.window_sequential_radio = QRadioButton("Sequential (one window at a time)")
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
        self._attachment_save_timer = QTimer(self)
        self._attachment_save_timer.setSingleShot(True)
        self._attachment_save_timer.setInterval(700)
        self._attachment_save_timer.timeout.connect(self._persist_attachment_state)
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(700)
        self._settings_save_timer.timeout.connect(self._persist_sending_settings_state)
        self._subject_manager_dialog: SubjectDraftsDialog | None = None
        self._workspace_loading = False
        self._active_attachment_widget: AttachmentDraftEditor | None = None
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
        self.tabs.addTab(self._build_html_content_tab(), "Attach Content")
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
        self.subject_input.setMaxLength(300)
        self.subject_toggle_button.setObjectName("secondaryButton")
        self.subject_toggle_button.setToolTip("Open the subject manager modal")
        self.subject_toggle_button.setVisible(False)
        self.subject_toggle_button.clicked.connect(self._open_subject_manager)
        subject_row.addWidget(subject_label)
        subject_row.addWidget(self.subject_input, 1)
        subject_row.addWidget(self.subject_toggle_button)
        subject_box.addLayout(subject_row)

        subject_toolbar = QHBoxLayout()
        self.subject_new_button.setObjectName("secondaryButton")
        self.subject_new_button.clicked.connect(self._new_subject_draft)
        self.subject_new_button.setToolTip("Start a new subject")
        subject_toolbar.addWidget(self.subject_new_button)
        self.subject_import_button.setObjectName("secondaryButton")
        self.subject_import_button.clicked.connect(self._load_subject_from_file)
        self.subject_import_button.setToolTip("Import subject rows from a CSV file")
        subject_toolbar.addWidget(self.subject_import_button)
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
        self.body_refresh_button.setToolTip("Reset the body workspace to a single active body tab")
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

        content_card, content_layout = self._card("", None)
        content_header = QHBoxLayout()
        content_header.setContentsMargins(0, 0, 0, 0)
        content_header.setSpacing(_scaled_int(8, self._scale))
        content_label = QLabel("ATTACHMENT CONTENT")
        content_label.setObjectName("sectionTitle")
        content_header.addWidget(content_label)
        content_header.addStretch()
        self.attach_add_button.setObjectName("secondaryButton")
        self.attach_add_button.setFixedWidth(_scaled_int(34, self._scale))
        self.attach_add_button.setToolTip("Add a new HTML attachment tab")
        self.attach_add_button.clicked.connect(self._new_attachment_draft_tab)
        self.attach_upload_button.setObjectName("secondaryButton")
        self.attach_upload_button.clicked.connect(self._upload_attachment_files)
        self.attach_upload_button.setToolTip("Upload HTML files and create tabs")
        self.attach_reset_button.setObjectName("secondaryButton")
        self.attach_reset_button.clicked.connect(self._reset_attachment_tabs)
        self.attach_reset_button.setToolTip("Reset attachments to a single blank tab")
        content_header.addWidget(self.attach_add_button)
        content_header.addWidget(self.attach_upload_button)
        content_header.addWidget(self.attach_reset_button)
        content_layout.addLayout(content_header)

        self.attach_tabs.setTabsClosable(True)
        self.attach_tabs.setMovable(True)
        self.attach_tabs.setDocumentMode(True)
        self.attach_tabs.setUsesScrollButtons(True)
        self.attach_tabs.tabCloseRequested.connect(self._remove_attachment_draft_tab)
        self.attach_tabs.currentChanged.connect(self._on_attachment_tab_changed)
        self.attach_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(self.attach_tabs, 1)

        export_card, export_layout = self._card("ATTACHMENT FORMAT OPTIONS", "Choose the attachment file format and preview behavior for the active HTML content.")
        export_form = QFormLayout()
        export_form.setLabelAlignment(Qt.AlignLeft)

        self.attach_convert_checkbox.setChecked(True)
        self.attach_convert_checkbox.setToolTip("Enable file conversion options")
        self.attach_convert_checkbox.toggled.connect(self._sync_attachment_convert_controls)
        convert_row = QHBoxLayout()
        convert_row.setContentsMargins(0, 0, 0, 0)
        convert_row.setSpacing(_scaled_int(10, self._scale))
        convert_label = QLabel("Convert")
        convert_label.setObjectName("fieldLabel")
        convert_row.addWidget(convert_label)
        convert_row.addWidget(self.attach_convert_checkbox)
        convert_row.addStretch()
        export_form.addRow(self._wrap_layout(convert_row))

        self.attach_format_label.setObjectName("sectionSubtitle")
        self.attach_choose_format_button.setObjectName("secondaryButton")
        self.attach_choose_format_button.clicked.connect(self._choose_attachment_file_format)
        self.attach_choose_format_button.setToolTip("Open a modal to choose one or more export file formats")
        format_row = QHBoxLayout()
        format_row.setContentsMargins(0, 0, 0, 0)
        format_row.setSpacing(_scaled_int(8, self._scale))
        format_row.addWidget(self.attach_choose_format_button)
        format_row.addWidget(self.attach_format_label)
        format_row.addStretch()
        self.attach_format_row_widget = self._wrap_layout(format_row)
        export_form.addRow("File format", self.attach_format_row_widget)
        self.attach_format_row_label = export_form.labelForField(self.attach_format_row_widget)

        export_layout.addLayout(export_form)
        self._sync_attachment_convert_controls(self.attach_convert_checkbox.isChecked())

        layout.addWidget(content_card, 1)
        layout.addWidget(export_card)
        if self.attach_tabs.count() == 0:
            self._add_attachment_draft_tab(select=True)
        self._sync_active_attachment_widget_refs()
        self._update_attachment_tab_controls()
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
        self.delay_fixed_radio.setToolTip("Use the same delay for every send")
        self.delay_random_radio.setToolTip("Use a random delay within the range")
        self.delay_human_radio.setToolTip("Use a human-like delay pattern")
        self.delay_type_group = QButtonGroup(self)
        self.delay_type_group.setExclusive(True)
        for button in (self.delay_fixed_radio, self.delay_random_radio, self.delay_human_radio):
            self.delay_type_group.addButton(button)
            delay_type_row.addWidget(button)
        delay_type_row.addStretch()
        send_layout.addWidget(self._labeled_value_row("Delay type", self._wrap_layout(delay_type_row)))

        retry_row = QHBoxLayout()
        self.retry_enable_checkbox.setChecked(True)
        self.retry_enable_checkbox.setToolTip("Enable retry handling for failed sends")
        retry_row.addWidget(self.retry_enable_checkbox)
        retry_row.addWidget(self.retry_count)
        retry_row.addWidget(QLabel("retries"))
        retry_row.addStretch()
        send_layout.addWidget(self._labeled_value_row("Retry failed sends", self._wrap_layout(retry_row)))

        order_row = QHBoxLayout()
        self.send_seq_radio.setToolTip("Send in list order")
        self.send_rand_radio.setToolTip("Shuffle the send order")
        self.send_order_group = QButtonGroup(self)
        self.send_order_group.setExclusive(True)
        for button in (self.send_seq_radio, self.send_rand_radio):
            self.send_order_group.addButton(button)
            order_row.addWidget(button)
        order_row.addStretch()
        send_layout.addWidget(self._labeled_value_row("Email send order", self._wrap_layout(order_row)))

        window_mode_row = QHBoxLayout()
        self.window_parallel_radio.setToolTip("Launch and send in parallel")
        self.window_sequential_radio.setToolTip("Rotate through windows one at a time")
        self.window_mode_group = QButtonGroup(self)
        self.window_mode_group.setExclusive(True)
        for button in (self.window_parallel_radio, self.window_sequential_radio):
            self.window_mode_group.addButton(button)
            window_mode_row.addWidget(button)
        window_mode_row.addStretch()
        send_layout.addWidget(self._labeled_value_row("Window send mode", self._wrap_layout(window_mode_row)))

        layout.addWidget(send_card)

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
        save_button.clicked.connect(lambda: self._save_sending_settings())
        save_button.setToolTip("Save the current sending settings")
        layout.addWidget(save_button, alignment=Qt.AlignLeft)
        layout.addStretch()

        self.sender_limit.valueChanged.connect(lambda _value: self._schedule_sending_settings_save())
        self.delay_from.valueChanged.connect(lambda _value: self._schedule_sending_settings_save())
        self.delay_to.valueChanged.connect(lambda _value: self._schedule_sending_settings_save())
        self.retry_count.valueChanged.connect(lambda _value: self._schedule_sending_settings_save())
        self.retry_enable_checkbox.toggled.connect(lambda _value: self._schedule_sending_settings_save())
        self.delay_type_group.buttonToggled.connect(lambda *_args: self._schedule_sending_settings_save())
        self.send_order_group.buttonToggled.connect(lambda *_args: self._schedule_sending_settings_save())
        self.window_mode_group.buttonToggled.connect(lambda *_args: self._schedule_sending_settings_save())
        self.ai_provider_combo.currentTextChanged.connect(lambda _value: self._schedule_sending_settings_save())
        self.ai_api_key_input.textEdited.connect(lambda _value: self._on_ai_api_key_changed())
        self.ai_model_combo.currentTextChanged.connect(lambda _value: self._schedule_sending_settings_save())

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

    def _current_sending_settings_payload(self) -> dict[str, object]:
        delay_type = "Random range"
        if self.delay_fixed_radio.isChecked():
            delay_type = "Fixed"
        elif self.delay_human_radio.isChecked():
            delay_type = "Human-like pattern"

        email_send_order = "Sequential"
        if self.send_rand_radio.isChecked():
            email_send_order = "Random shuffle"

        window_send_mode = "Parallel"
        if self.window_sequential_radio.isChecked():
            window_send_mode = "Sequential"

        return {
            "sender_limit": int(self.sender_limit.value()),
            "delay_from": float(self.delay_from.value()),
            "delay_to": float(self.delay_to.value()),
            "retry_count": int(self.retry_count.value()),
            "retry_enabled": bool(self.retry_enable_checkbox.isChecked()),
            "delay_type": delay_type,
            "email_send_order": email_send_order,
            "window_send_mode": window_send_mode,
            "ai_provider": self.ai_provider_combo.currentText().strip() or "ChatGPT",
            "ai_api_key": self.ai_api_key_input.text(),
            "ai_model": self.ai_model_combo.currentText().strip(),
            "ai_connected": bool(self.state.ai_connected),
            "available_models": list(self._available_ai_models),
        }

    def _apply_sending_settings_payload(self, payload: dict[str, object]) -> None:
        def _as_int(value: object, default: int) -> int:
            try:
                return int(float(value))
            except Exception:
                return default

        def _as_float(value: object, default: float) -> float:
            try:
                return float(value)
            except Exception:
                return default

        def _as_bool(value: object, default: bool) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"1", "true", "yes", "on"}:
                    return True
                if lowered in {"0", "false", "no", "off"}:
                    return False
            return default

        def _block(widget: QWidget, value: Callable[[], None]) -> None:
            widget.blockSignals(True)
            try:
                value()
            finally:
                widget.blockSignals(False)

        sender_limit = _as_int(payload.get("sender_limit"), 500)
        delay_from = _as_float(payload.get("delay_from"), 0.5)
        delay_to = _as_float(payload.get("delay_to"), 1.0)
        retry_count = _as_int(payload.get("retry_count"), 3)
        retry_enabled = _as_bool(payload.get("retry_enabled"), True)
        delay_type = str(payload.get("delay_type") or "Random range")
        email_send_order = str(payload.get("email_send_order") or "Sequential")
        window_send_mode = str(payload.get("window_send_mode") or "Parallel")
        ai_provider = str(payload.get("ai_provider") or "ChatGPT")
        ai_api_key = str(payload.get("ai_api_key") or "")
        ai_model = str(payload.get("ai_model") or "")
        ai_connected = _as_bool(payload.get("ai_connected"), False)
        available_models_raw = payload.get("available_models")
        available_models = available_models_raw if isinstance(available_models_raw, list) else []

        _block(self.sender_limit, lambda: self.sender_limit.setValue(sender_limit))
        _block(self.delay_from, lambda: self.delay_from.setValue(delay_from))
        _block(self.delay_to, lambda: self.delay_to.setValue(delay_to))
        _block(self.retry_count, lambda: self.retry_count.setValue(retry_count))
        _block(self.retry_enable_checkbox, lambda: self.retry_enable_checkbox.setChecked(retry_enabled))

        _block(self.delay_fixed_radio, lambda: self.delay_fixed_radio.setChecked(delay_type == "Fixed"))
        _block(self.delay_random_radio, lambda: self.delay_random_radio.setChecked(delay_type == "Random range"))
        _block(self.delay_human_radio, lambda: self.delay_human_radio.setChecked(delay_type == "Human-like pattern"))
        if not any((self.delay_fixed_radio.isChecked(), self.delay_random_radio.isChecked(), self.delay_human_radio.isChecked())):
            self.delay_random_radio.setChecked(True)

        _block(self.send_seq_radio, lambda: self.send_seq_radio.setChecked(email_send_order != "Random shuffle"))
        _block(self.send_rand_radio, lambda: self.send_rand_radio.setChecked(email_send_order == "Random shuffle"))

        _block(self.window_parallel_radio, lambda: self.window_parallel_radio.setChecked(window_send_mode != "Sequential"))
        _block(self.window_sequential_radio, lambda: self.window_sequential_radio.setChecked(window_send_mode == "Sequential"))

        _block(self.ai_provider_combo, lambda: self.ai_provider_combo.setCurrentText(ai_provider))
        _block(self.ai_api_key_input, lambda: self.ai_api_key_input.setText(ai_api_key))

        self.state.sender_limit = sender_limit
        self.state.delay_from = delay_from
        self.state.delay_to = delay_to
        self.state.retry_count = retry_count
        self.state.retry_enabled = retry_enabled
        self.state.delay_type = delay_type
        self.state.email_send_order = email_send_order
        self.state.window_send_mode = window_send_mode
        self.state.ai_provider = ai_provider
        self.state.ai_api_key = ai_api_key
        self.state.ai_model = ai_model
        self.state.ai_connected = ai_connected
        self._available_ai_models = [str(item) for item in available_models if str(item).strip()]
        self.state.ai_available_models = list(self._available_ai_models)

        self._refresh_ai_models()
        self._sync_ai_connection_ui()

    def _load_sending_settings_state(self, mysql_settings_map: dict[str, object] | None = None) -> None:
        local_payload = _load_ui_state(LOCAL_SETTINGS_STATE_KEY)
        payload: dict[str, object] = {}
        if isinstance(mysql_settings_map, dict):
            payload.update(mysql_settings_map)
        if isinstance(local_payload, dict):
            payload.update(local_payload)
        self._apply_sending_settings_payload(payload)

    def _schedule_sending_settings_save(self) -> None:
        if self._workspace_loading:
            return
        self._settings_save_timer.start()

    def _persist_sending_settings_state(self) -> None:
        if self._workspace_loading:
            return
        payload = self._current_sending_settings_payload()
        _upsert_ui_state(LOCAL_SETTINGS_STATE_KEY, payload)
        self.state.sender_limit = int(payload["sender_limit"])
        self.state.delay_from = float(payload["delay_from"])
        self.state.delay_to = float(payload["delay_to"])
        self.state.retry_count = int(payload["retry_count"])
        self.state.retry_enabled = bool(payload["retry_enabled"])
        self.state.delay_type = str(payload["delay_type"])
        self.state.email_send_order = str(payload["email_send_order"])
        self.state.window_send_mode = str(payload["window_send_mode"])
        self.state.ai_provider = str(payload["ai_provider"])
        self.state.ai_api_key = str(payload["ai_api_key"])
        self.state.ai_model = str(payload["ai_model"])
        self.state.ai_connected = bool(payload["ai_connected"])
        self.state.ai_available_models = [str(item) for item in payload.get("available_models") or []]
        self._available_ai_models = list(self.state.ai_available_models)
        if self.state.logged_in and self.state.username:
            try:
                for key, value in payload.items():
                    upsert_setting(self.state.username, str(key), value)
            except Exception:
                pass

    def _save_sending_settings(self) -> None:
        self._persist_sending_settings_state()
        self._log_action("Saved sending settings")
        self.notify("Settings saved")

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
        self._schedule_sending_settings_save()

    def _on_ai_api_key_changed(self) -> None:
        api_key = self.ai_api_key_input.text()
        self.state.ai_api_key = api_key
        self.state.ai_connected = False
        self.state.ai_model = ""
        self._available_ai_models = []
        self._refresh_ai_models()
        self._sync_ai_connection_ui()
        self._schedule_sending_settings_save()

    def _connect_ai_provider(self) -> None:
        provider = self.ai_provider_combo.currentText() or "ChatGPT"
        api_key = self.ai_api_key_input.text().strip()
        self.state.ai_api_key = api_key
        if not api_key:
            self.state.ai_connected = False
            self.state.ai_model = ""
            self._available_ai_models = []
            self._refresh_ai_models()
            self._sync_ai_connection_ui()
            self.notify("Enter an API key to connect")
            self._persist_sending_settings_state()
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
            self._persist_sending_settings_state()
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
        self._persist_sending_settings_state()
        self.notify(f"{provider} connected")

    def _on_ai_model_changed(self) -> None:
        if not self.ai_model_combo.isEnabled():
            return
        self.state.ai_model = self.ai_model_combo.currentText().strip()
        if self.state.ai_model:
            self._log_action(f"AI model selected: {self.state.ai_model}")
            self._schedule_sending_settings_save()

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

    def _choose_attachment_file_format(self) -> None:
        dialog = FileFormatDialog(self.window(), scale=self._scale, selected_format=getattr(self, "attach_format_value", "PDF document") or "PDF document")
        if dialog.exec() == QDialog.Accepted:
            selected = dialog.selected_format()
            self.attach_format_value = selected
            self.attach_format_label.setText(self._attachment_format_summary(selected))
            self._log_action(f"Selected attachment format: {selected}")
            self.notify(f"Format set to {selected}")

    def _sync_attachment_convert_controls(self, checked: bool) -> None:
        row_widget = getattr(self, "attach_format_row_widget", None)
        row_label = getattr(self, "attach_format_row_label", None)
        if row_widget is not None:
            row_widget.setVisible(checked)
        if row_label is not None:
            row_label.setVisible(checked)
        self.attach_choose_format_button.setEnabled(checked)
        self.attach_format_label.setEnabled(checked)

    def _attachment_format_summary(self, selected: str) -> str:
        summary_map = {
            "PDF document": "PDF",
            "Excel spreadsheet (XLSX)": "XLSX",
            "Excel template (XLTX)": "XLTX",
            "PowerPoint presentation (PPTX)": "PPTX",
            "PowerPoint slideshow (PPSX)": "PPSX",
            "Word document (DOCX)": "DOCX",
        }
        selected = (selected or "").strip()
        if not selected:
            return "PDF"
        if selected == "Random format":
            return "Random"
        parts = [part.strip() for part in selected.split(",") if part.strip()]
        short_parts = [summary_map.get(part, part) for part in parts]
        return ", ".join(short_parts)

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
        current_widget = self._current_attachment_widget()
        html_content = ""
        if current_widget is not None:
            html_content = current_widget.html_editor.toPlainText().strip()
        elif hasattr(self, "html_editor") and isinstance(self.html_editor, QTextEdit):
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
        self.state.ai_api_key = ""
        self.state.ai_model = ""
        self.state.ai_connected = False
        self.state.ai_available_models = []
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

    def _update_attachment_tab_controls(self) -> None:
        limit_reached = self.attach_tabs.count() >= MAX_ATTACHMENT_TABS
        self.attach_add_button.setEnabled(not limit_reached)
        self.attach_add_button.setToolTip("Maximum of 50 content tabs reached" if limit_reached else "Add a new HTML content tab")

    def _set_subject_item_data(
        self,
        item: QListWidgetItem,
        record_id: int | None,
        title: str,
        subject: str,
        *,
        local_only: bool = False,
        local_draft_id: int | None = None,
    ) -> None:
        item.setData(Qt.UserRole, record_id)
        item.setData(Qt.UserRole + 1, title)
        item.setData(Qt.UserRole + 2, subject)
        item.setData(ROLE_LOCAL_ONLY, local_only)
        item.setData(ROLE_LOCAL_DRAFT_ID, local_draft_id)
        item.setText(title or subject or "Untitled Subject")

    def _selected_subject_item(self) -> QListWidgetItem | None:
        return self.subject_drafts_list.currentItem()

    def _clear_subject_selection(self) -> None:
        self.subject_drafts_list.blockSignals(True)
        try:
            self.subject_drafts_list.clearSelection()
        finally:
            self.subject_drafts_list.blockSignals(False)

    def _update_subject_toggle_visibility(self) -> None:
        self.subject_toggle_button.setVisible(self.subject_drafts_list.count() > 0)

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

        if self._subject_manager_dialog is not None:
            if self._subject_manager_dialog.isVisible():
                try:
                    self._subject_manager_dialog.raise_()
                    self._subject_manager_dialog.activateWindow()
                except Exception:
                    pass
                return
            try:
                self._subject_manager_dialog.deleteLater()
            except Exception:
                pass
            self._subject_manager_dialog = None

        try:
            dialog = SubjectDraftsDialog(self, self.state.auth_token, scale=self._scale, on_changed=self._load_subjects)
            self._subject_manager_dialog = dialog
            dialog.setAttribute(Qt.WA_DeleteOnClose, True)
            dialog.finished.connect(lambda _result, d=dialog: self._on_subject_manager_finished(d))
            dialog.setWindowModality(Qt.ApplicationModal)
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            QTimer.singleShot(0, dialog.raise_)
            QTimer.singleShot(0, dialog.activateWindow)
        except Exception as exc:
            self._subject_manager_dialog = None
            self._log_action(f"Failed to open subject manager: {exc}")
            self.notify("Unable to open subject manager")

    def _on_subject_manager_finished(self, dialog: SubjectDraftsDialog) -> None:
        if self._subject_manager_dialog is dialog:
            self._subject_manager_dialog = None
        subject = dialog.selected_subject()
        if subject:
            self.subject_input.blockSignals(True)
            try:
                self.subject_input.setText(subject)
            except Exception:
                pass
            finally:
                self.subject_input.blockSignals(False)
            self.state.subject_text = subject
            self._schedule_subject_body_save()
        self._load_subjects()

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
        current_text = self.subject_input.text().strip()
        if self.subject_drafts_list.count() >= MAX_SUBJECTS:
            self.notify("Maximum 100 subjects allowed")
            self._update_subject_count_label()
            return
        if current_text:
            self._save_subject_draft(force_new=True)
        self._clear_subject_selection()
        self.subject_input.blockSignals(True)
        try:
            self.subject_input.clear()
        finally:
            self.subject_input.blockSignals(False)
        self.state.subject_text = ""
        self._update_subject_toggle_visibility()
        self._persist_subject_body_state()

    def _subject_draft_rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for index in range(self.subject_drafts_list.count()):
            item = self.subject_drafts_list.item(index)
            rows.append(
                {
                    "title": self._subject_item_title(item),
                    "subject": self._subject_item_subject(item),
                }
            )
        return rows

    def _save_subject_draft(self, *, force_new: bool = False) -> None:
        if self._workspace_loading or not self.state.logged_in or not self.state.username:
            return

        subject = self.subject_input.text().strip()
        if not subject:
            self.notify("Enter a subject first")
            return
        if len(subject) > 300:
            self.notify("Subject must be 300 characters or less")
            return
        current_item = self._selected_subject_item()
        if current_item is None and self.subject_drafts_list.count() >= MAX_SUBJECTS:
            self.notify("Maximum 100 subjects allowed")
            self._update_subject_count_label()
            return

        self._show_subject_body_loader("Saving subject.")
        try:
            title = subject[:64]
            if current_item is not None and not force_new:
                self._set_subject_item_data(
                    current_item,
                    None,
                    title,
                    subject,
                    local_only=True,
                    local_draft_id=None,
                )
            else:
                new_item = QListWidgetItem()
                self._set_subject_item_data(
                    new_item,
                    None,
                    title,
                    subject,
                    local_only=True,
                    local_draft_id=None,
                )
                self.subject_drafts_list.addItem(new_item)
                self.subject_drafts_list.setCurrentItem(new_item)
            self.state.subject_text = subject
            self._update_subject_count_label()
            self._update_subject_toggle_visibility()
            self._persist_subject_body_state()
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
        title = self._subject_item_title(item)
        row = self.subject_drafts_list.row(item)
        self.subject_drafts_list.takeItem(row)
        self.subject_input.clear()
        self.state.subject_text = ""
        self._update_subject_count_label()
        self._update_subject_toggle_visibility()
        self._persist_subject_body_state()
        self._log_action(f"Removed subject: {title or 'Untitled'}")
        self.notify("Subject removed")

    def _create_body_draft_tab(self, record: dict[str, object] | None = None) -> BodyDraftEditor:
        widget = BodyDraftEditor(scale=self._scale)
        if record:
            mode = str(record.get("mode") or "Normal Message")
            title = str(record.get("title") or self._body_record_title(record, self.body_tabs.count()))
            body_text = str(record.get("plain_text") or record.get("body_text") or "")
            body_html = str(record.get("html_text") or record.get("body_html") or "")
            widget.set_content(title, mode, body_text, body_html or body_text, local_only=True)
        else:
            title = self._next_body_title()
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

    def _body_record_title(self, record: dict[str, object], index: int) -> str:
        details = self._decode_setting_value(record.get("details_json"))
        title = str(record.get("title") or "").strip()
        source_file = ""
        if isinstance(details, dict):
            source_file = str(details.get("source_file") or "").strip()
        title_normalized = title.lower()
        if source_file or not title or self._looks_like_auto_body_title(title_normalized):
            return f"Body {index + 1}"
        return title

    def _looks_like_auto_body_title(self, title_normalized: str) -> bool:
        if not title_normalized:
            return True
        if title_normalized.startswith("body "):
            return False
        if "inv" in title_normalized:
            return True
        if "copy" in title_normalized and any(ch.isdigit() for ch in title_normalized):
            return True
        if title_normalized.startswith("text body") or title_normalized.startswith("html body"):
            return True
        return False

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
        self.body_tabs.removeTab(index)
        if self.body_tabs.count() == 0:
            self._add_body_draft_tab(select=True)
        else:
            self._refresh_body_tab_labels()
        self._update_body_tab_controls()
        self._sync_active_body_widget_refs()
        self._persist_subject_body_state()
        self._log_action("Removed body tab")

    def _on_body_tab_changed(self, _index: int) -> None:
        self._sync_active_body_widget_refs()
        self._schedule_subject_body_save()

    def _current_attachment_widget(self) -> AttachmentDraftEditor | None:
        widget = self.attach_tabs.currentWidget()
        return widget if isinstance(widget, AttachmentDraftEditor) else None

    def _sync_active_attachment_widget_refs(self) -> None:
        if self.attach_tabs.count() == 0:
            self._add_attachment_draft_tab(select=True)
        widget = self._current_attachment_widget()
        self._active_attachment_widget = widget
        if widget is not None:
            self.html_editor = widget.html_editor
            self.state.html_template_text = widget.html_editor.toPlainText()
        self._update_attachment_tab_controls()

    def _attachment_tab_label(self, widget: AttachmentDraftEditor, index: int) -> str:
        title = widget.title_text() or f"Content {index + 1}"
        return f"{title} [HTML]"

    def _refresh_attachment_tab_labels(self) -> None:
        for index in range(self.attach_tabs.count()):
            widget = self.attach_tabs.widget(index)
            if isinstance(widget, AttachmentDraftEditor):
                self.attach_tabs.setTabText(index, self._attachment_tab_label(widget, index))

    def _rename_attachment_tab(self, widget: AttachmentDraftEditor, title: str) -> None:
        index = self.attach_tabs.indexOf(widget)
        if index < 0:
            return
        self.attach_tabs.setTabText(index, self._attachment_tab_label(widget, index))

    def _next_attachment_title(self) -> str:
        return f"Content {self.attach_tabs.count() + 1}"

    def _looks_like_auto_attachment_title(self, title_normalized: str) -> bool:
        if not title_normalized:
            return True
        if title_normalized.startswith("content "):
            return True
        if title_normalized.startswith("html content"):
            return True
        if "copy" in title_normalized and any(ch.isdigit() for ch in title_normalized):
            return True
        return False

    def _attachment_record_title(self, record: dict[str, object], index: int) -> str:
        details = self._decode_setting_value(record.get("details_json"))
        title = str(record.get("title") or "").strip()
        source_file = ""
        if isinstance(details, dict):
            source_file = str(details.get("source_file") or "").strip()
        title_normalized = title.lower()
        if source_file or not title or self._looks_like_auto_attachment_title(title_normalized):
            return f"Content {index + 1}"
        return title

    def _create_attachment_draft_tab(self, record: dict[str, object] | None = None) -> AttachmentDraftEditor:
        widget = AttachmentDraftEditor(scale=self._scale)
        if record:
            title = self._attachment_record_title(record, self.attach_tabs.count())
            html_text = str(record.get("html_text") or record.get("body_html") or record.get("body_text") or "")
            widget.set_content(title, html_text, local_only=True)
        else:
            title = self._next_attachment_title()
            widget.set_content(title, "")

        widget.titleChanged.connect(lambda title_text, w=widget: self._rename_attachment_tab(w, title_text))
        widget.titleChanged.connect(lambda _title, self=self: self._persist_attachment_state())
        widget.contentChanged.connect(self._persist_attachment_state)
        widget.previewRequested.connect(lambda w=widget: self._preview_attachment_editor_html(w))
        return widget

    def _add_attachment_draft_tab(self, record: dict[str, object] | None = None, select: bool = True) -> AttachmentDraftEditor | None:
        if self.attach_tabs.count() >= MAX_ATTACHMENT_TABS:
            self._update_attachment_tab_controls()
            self.notify("Maximum of 50 content tabs reached")
            return None
        widget = self._create_attachment_draft_tab(record)
        tab_number = self.attach_tabs.count() + 1
        index = self.attach_tabs.addTab(widget, f"Content {tab_number} [HTML]")
        self._refresh_attachment_tab_labels()
        self._update_attachment_tab_controls()
        if select:
            self.attach_tabs.setCurrentIndex(index)
        return widget

    def _new_attachment_draft_tab(self) -> None:
        self._add_attachment_draft_tab(select=True)

    def _remove_attachment_draft_tab(self, index: int) -> None:
        widget = self.attach_tabs.widget(index)
        if not isinstance(widget, AttachmentDraftEditor):
            return
        self.attach_tabs.removeTab(index)
        if self.attach_tabs.count() == 0:
            self._add_attachment_draft_tab(select=True)
        else:
            self._refresh_attachment_tab_labels()
        self._update_attachment_tab_controls()
        self._sync_active_attachment_widget_refs()
        self._persist_attachment_state()
        self._log_action("Removed attachment tab")

    def _on_attachment_tab_changed(self, _index: int) -> None:
        self._sync_active_attachment_widget_refs()
        self._persist_attachment_state()

    def _reset_attachment_tabs(self) -> None:
        self._show_subject_body_loader("Resetting attachment tabs.")
        try:
            _delete_attachment_state()
            _delete_local_drafts("attachment")
            self.attach_tabs.blockSignals(True)
            try:
                for index in reversed(range(self.attach_tabs.count())):
                    self.attach_tabs.removeTab(index)
            finally:
                self.attach_tabs.blockSignals(False)
            self._add_attachment_draft_tab(select=True)
            self._refresh_attachment_tab_labels()
            self._update_attachment_tab_controls()
            self._sync_active_attachment_widget_refs()
            self._log_action("Reset attachment tabs")
            self.notify("Content tabs reset")
        except Exception as exc:
            self._log_action(f"Failed to reset attachment tabs: {exc}")
            self.notify("Unable to reset content tabs")
        finally:
            self._hide_subject_body_loader()

    def _import_html_attachment_file(self, path: Path) -> int:
        html_text = self._read_text_template_file(path)
        if not html_text.strip():
            return 0
        title = self._next_attachment_title()
        self._create_and_store_attachment_tab(title=title, html_text=html_text, source_name=path.name)
        return 1

    def _create_and_store_attachment_tab(self, *, title: str, html_text: str, source_name: str = "") -> AttachmentDraftEditor | None:
        if self.attach_tabs.count() >= MAX_ATTACHMENT_TABS:
            return None
        record = {
            "title": title[:64] or "Content",
            "html_text": html_text,
        }
        widget = self._add_attachment_draft_tab(record, select=False)
        if widget is None:
            return None
        self._refresh_attachment_tab_labels()
        self._update_attachment_tab_controls()
        self._persist_attachment_state()
        return widget

    def _upload_attachment_files(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Upload attachment content",
            "",
            "HTML files (*.html *.htm);;All files (*)",
        )
        if not file_paths:
            return

        imported = 0
        self._show_subject_body_loader("Uploading attachment files.")
        self._workspace_loading = True
        try:
            for file_name in file_paths:
                if self.attach_tabs.count() >= MAX_ATTACHMENT_TABS:
                    self.notify("Maximum of 50 content tabs reached")
                    break
                path = Path(file_name)
                if path.suffix.lower() in {".html", ".htm"}:
                    imported += self._import_html_attachment_file(path)
                else:
                    self._log_action(f"Skipped unsupported content file: {path.name}")
        except Exception as exc:
            self._log_action(f"Failed to upload attachment files: {exc}")
            self.notify(f"Unable to upload content: {exc}")
        finally:
            self._workspace_loading = False
            self._hide_subject_body_loader()

        if self.attach_tabs.count() == 0:
            self._add_attachment_draft_tab(select=True)
        else:
            self._refresh_attachment_tab_labels()
            self._update_attachment_tab_controls()
            self._sync_active_attachment_widget_refs()

        if imported > 0:
            self._log_action(f"Uploaded {imported} attachment content(s)")
            self.notify(f"Uploaded {imported} content(s)")
        self._persist_attachment_state()

    def _load_attachment_tabs_from_local(self) -> None:
        state_payload = _load_attachment_state()
        _delete_local_drafts("attachment")
        tab_rows = state_payload.get("tabs") if isinstance(state_payload, dict) else []
        if not isinstance(tab_rows, list):
            tab_rows = []
        selected_index = int(state_payload.get("selected_index") or 0) if isinstance(state_payload, dict) else 0
        self.attach_tabs.blockSignals(True)
        try:
            for index in reversed(range(self.attach_tabs.count())):
                self.attach_tabs.removeTab(index)
            for row in tab_rows:
                if isinstance(row, dict):
                    self._add_attachment_draft_tab(row, select=False)
            if self.attach_tabs.count() == 0:
                self._add_attachment_draft_tab(select=True)
            else:
                self.attach_tabs.setCurrentIndex(min(max(selected_index, 0), self.attach_tabs.count() - 1))
            convert_enabled = bool(state_payload.get("convert_enabled", True)) if isinstance(state_payload, dict) else True
            format_value = str(state_payload.get("format_value") or self.attach_format_value or "PDF document") if isinstance(state_payload, dict) else self.attach_format_value
            self.attach_convert_checkbox.blockSignals(True)
            try:
                self.attach_convert_checkbox.setChecked(convert_enabled)
            finally:
                self.attach_convert_checkbox.blockSignals(False)
            self.attach_format_value = format_value or "PDF document"
            self.attach_format_label.setText(self._attachment_format_summary(self.attach_format_value))
        finally:
            self.attach_tabs.blockSignals(False)
        self._refresh_attachment_tab_labels()
        self._update_attachment_tab_controls()
        self._sync_active_attachment_widget_refs()

    def _schedule_attachment_save(self) -> None:
        if self._workspace_loading:
            return
        self._attachment_save_timer.start()

    def _persist_attachment_state(self) -> None:
        if self._workspace_loading:
            return
        try:
            if self.attach_tabs.count() == 0:
                self._add_attachment_draft_tab(select=True)
            tabs_payload: list[dict[str, object]] = []
            for index in range(self.attach_tabs.count()):
                widget = self.attach_tabs.widget(index)
                if not isinstance(widget, AttachmentDraftEditor):
                    continue
                payload = widget.payload()
                title = payload["title"] or f"Content {index + 1}"
                html_text = payload["html_text"]
                tabs_payload.append(
                    {
                        "title": title[:64] or "Content",
                        "html_text": html_text,
                        "kind": "attachment",
                    }
                )
                widget.local_only = True
                self.attach_tabs.setTabText(index, self._attachment_tab_label(widget, index))
            active_widget = self._current_attachment_widget()
            if active_widget is not None:
                self.state.html_template_text = active_widget.html_editor.toPlainText()
            _delete_local_drafts("attachment")
            _upsert_attachment_state(
                {
                    "tabs": tabs_payload,
                    "selected_index": self.attach_tabs.currentIndex(),
                    "convert_enabled": self.attach_convert_checkbox.isChecked(),
                    "format_value": self.attach_format_value,
                }
            )
        except Exception as exc:
            self._log_action(f"Failed to save attachment content: {exc}")

    def _preview_attachment_editor_html(self, widget: AttachmentDraftEditor | None) -> None:
        if widget is None:
            self.notify("No attachment content available")
            return
        html_content = widget.html_editor.toPlainText().strip()
        if not html_content:
            self.notify("Add HTML content first")
            return
        title = widget.title_text() or "HTML Content Preview"
        dialog = self._build_preview_dialog(title, html_content, "Previewing the selected HTML attachment content.")
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._log_action(f"Opened attachment preview: {title}")
        self.notify("Content preview opened")

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
            "CSV files (*.csv);;All files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        self._show_subject_body_loader(f"Loading subject template from {path.name}.")
        try:
            if path.suffix.lower() != ".csv":
                raise ValueError("Please choose a CSV file.")
            raw_text = self._read_text_template_file(path)
            subjects = []
            for row in csv.reader(raw_text.splitlines()):
                for value in row:
                    subject = str(value or "").strip()
                    if subject:
                        subjects.append(subject)
            if len(subjects) > 100:
                raise ValueError("CSV can contain at most 100 subjects.")
            if self.subject_drafts_list.count() + len(subjects) > MAX_SUBJECTS:
                raise ValueError("Total subjects cannot exceed 100.")
            for subject in subjects:
                if len(subject) > 300:
                    raise ValueError("Each subject must be 300 characters or less.")
            if not subjects:
                subjects = [path.stem.replace("_", " ").strip() or "Subject"]

            self._workspace_loading = True
            self.subject_drafts_list.blockSignals(True)
            try:
                for subject in subjects:
                    item = QListWidgetItem()
                    self._set_subject_item_data(
                        item,
                        None,
                        subject[:64] or "Subject",
                        subject,
                        local_only=True,
                        local_draft_id=None,
                    )
                    self.subject_drafts_list.addItem(item)
                self.subject_drafts_list.setCurrentRow(self.subject_drafts_list.count() - 1)
            finally:
                self.subject_drafts_list.blockSignals(False)
            current = self.subject_drafts_list.currentItem()
            if current is not None:
                self.subject_input.setText(self._subject_item_subject(current))
                self.state.subject_text = self.subject_input.text().strip()
            self._update_subject_count_label()
            self._update_subject_toggle_visibility()
            self._persist_subject_body_state()
            self._log_action(f"Loaded {len(subjects)} subject(s) from {path.name}")
            self.notify(f"Loaded {len(subjects)} subject(s)")
        except Exception as exc:
            self.notify(f"Unable to load subject file: {exc}")
            self._log_action(f"Failed to load subject template from {path.name}: {exc}")
        finally:
            self._workspace_loading = False
            self._hide_subject_body_loader()

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
            title = self._next_body_title()
            self._workspace_loading = True
            body_widget = self._create_and_store_body_tab(
                title=title,
                mode="HTML Message" if is_html else "Normal Message",
                plain_text="" if is_html else body,
                html_text=body if is_html else "",
                source_name=path.name,
            )
            if body_widget is None:
                return
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

    def _next_body_title(self) -> str:
        return f"Body {self.body_tabs.count() + 1}"

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
            title = self._next_body_title()
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
        title = self._next_body_title()
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
        record = {
            "title": title[:64] or "Body",
            "mode": mode,
            "plain_text": plain_text,
            "html_text": html_text if mode == "HTML Message" else "",
        }
        widget = self._add_body_draft_tab(record, select=False)
        if widget is None:
            return None
        self._refresh_body_tab_labels()
        self._update_body_tab_controls()
        self._persist_subject_body_state()
        return widget

    def _persist_subject_body_state(self) -> None:
        if self._workspace_loading or not self.state.logged_in or not self.state.username:
            return

        subject = self.subject_input.text().strip()
        current_subject = self._selected_subject_item()
        current_body = self._current_body_widget()
        current_attachment = self._current_attachment_widget()
        if current_body is None:
            current_body = self._add_body_draft_tab(select=True)
        body_payload = current_body.payload() if current_body is not None else {"mode": "Normal Message", "plain_text": "", "html_text": "", "title": "Body"}
        body_mode = str(body_payload["mode"])
        plain_body = str(body_payload["plain_text"])
        html_body = str(body_payload["html_text"])
        body_title = str(body_payload["title"] or "Body")
        attachment_html = current_attachment.html_editor.toPlainText() if current_attachment is not None else ""

        self.state.subject_text = subject
        self.state.plain_body_text = plain_body
        self.state.html_message_text = html_body
        self.state.body_mode = body_mode
        self.state.html_template_text = attachment_html

        try:
            subject_rows = []
            for index in range(self.subject_drafts_list.count()):
                item = self.subject_drafts_list.item(index)
                if item is None:
                    continue
                row_subject = self._subject_item_subject(item).strip() or item.text().strip()
                if row_subject:
                    subject_rows.append({"title": row_subject[:64] or "Subject", "subject": row_subject})
            if subject:
                if current_subject is not None:
                    current_index = self.subject_drafts_list.row(current_subject)
                    if current_index >= 0 and current_index < len(subject_rows):
                        subject_rows[current_index] = {"title": subject[:64] or "Subject", "subject": subject}
                    else:
                        subject_rows.append({"title": subject[:64] or "Subject", "subject": subject})
                else:
                    subject_rows.append({"title": subject[:64] or "Subject", "subject": subject})
            _upsert_ui_state(
                LOCAL_SUBJECT_STATE_KEY,
                {
                    "subjects": subject_rows,
                    "selected_index": max(self.subject_drafts_list.currentRow(), 0) if self.subject_drafts_list.count() > 0 else -1,
                },
            )

            body_rows = []
            for index in range(self.body_tabs.count()):
                widget = self.body_tabs.widget(index)
                if not isinstance(widget, BodyDraftEditor):
                    continue
                payload = widget.payload()
                mode = payload["mode"]
                title = payload["title"] or f"Body {index + 1}"
                plain = payload["plain_text"]
                html_text = payload["html_text"]
                body_rows.append(
                    {
                        "title": title[:64] or "Body",
                        "mode": mode,
                        "plain_text": plain,
                        "html_text": html_text if mode == "HTML Message" else "",
                    }
                )
            _upsert_ui_state(
                LOCAL_BODY_STATE_KEY,
                {
                    "tabs": body_rows,
                    "selected_index": self.body_tabs.currentIndex(),
                },
            )

            self._rename_body_tab(current_body, body_title)
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

    def _update_subject_count_label(self) -> None:
        self.subject_count_label.setText(_subject_count_text(self.subject_drafts_list.count()))

    def _load_subjects(self) -> None:
        self._workspace_loading = True
        try:
            payload = _load_ui_state(LOCAL_SUBJECT_STATE_KEY)
            subject_rows = payload.get("subjects") or []
            if not isinstance(subject_rows, list):
                subject_rows = []

            self.subject_drafts_list.blockSignals(True)
            try:
                self.subject_drafts_list.clear()
                for row in reversed(subject_rows):
                    if not isinstance(row, dict):
                        continue
                    item = QListWidgetItem()
                    title = str(row.get("title") or row.get("subject") or "Subject")
                    subject = str(row.get("subject") or row.get("title") or "")
                    self._set_subject_item_data(
                        item,
                        None,
                        title,
                        subject,
                        local_only=True,
                        local_draft_id=None,
                    )
                    self.subject_drafts_list.addItem(item)
                if self.subject_drafts_list.count() > 0:
                    self.subject_drafts_list.setCurrentRow(self.subject_drafts_list.count() - 1)
            finally:
                self.subject_drafts_list.blockSignals(False)

            current_subject = self.subject_drafts_list.currentItem()
            if current_subject is not None:
                subject = self._subject_item_subject(current_subject)
                self.subject_input.blockSignals(True)
                try:
                    self.subject_input.setText(subject)
                finally:
                    self.subject_input.blockSignals(False)
                self.state.subject_text = subject

            self._update_subject_count_label()
            self._update_subject_toggle_visibility()
        finally:
            self._workspace_loading = False

    def _sync_subject_body_widgets(self) -> None:
        self._workspace_loading = True
        try:
            if self.body_tabs.count() == 0:
                self._load_body_tabs_from_state()
            self._sync_active_body_widget_refs()
            self._update_body_tab_controls()
            self._sync_active_attachment_widget_refs()
        finally:
            self._workspace_loading = False

    def _load_body_tabs_from_state(self) -> None:
        payload = _load_ui_state(LOCAL_BODY_STATE_KEY)
        tab_rows = payload.get("tabs") or []
        if not isinstance(tab_rows, list):
            tab_rows = []
        selected_index = int(payload.get("selected_index") or -1)

        self.body_tabs.blockSignals(True)
        try:
            for index in reversed(range(self.body_tabs.count())):
                self.body_tabs.removeTab(index)
            for row in tab_rows:
                if not isinstance(row, dict):
                    continue
                self._add_body_draft_tab(
                    {
                        "title": str(row.get("title") or row.get("label") or "Body"),
                        "mode": str(row.get("mode") or "Normal Message"),
                        "plain_text": str(row.get("plain_text") or ""),
                        "html_text": str(row.get("html_text") or ""),
                    },
                    select=False,
                )
            if self.body_tabs.count() == 0:
                self._add_body_draft_tab(select=True)
            elif 0 <= selected_index < self.body_tabs.count():
                self.body_tabs.setCurrentIndex(selected_index)
            else:
                self.body_tabs.setCurrentIndex(self.body_tabs.count() - 1)
        finally:
            self.body_tabs.blockSignals(False)
        self._refresh_body_tab_labels()
        self._update_body_tab_controls()
        self._sync_active_body_widget_refs()

    def load_user_workspace(self) -> None:
        if not self.state.logged_in or not self.state.auth_token:
            return

        self._workspace_loading = True
        try:
            settings_payload = api_get_settings(self.state.auth_token)
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
            self._load_sending_settings_state(settings_map)
            self._load_subjects()
            self._load_body_tabs_from_state()
            self._load_attachment_tabs_from_local()
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
        self.sender_limit.blockSignals(True)
        self.sender_limit.setValue(int(getattr(self.state, "sender_limit", 500)))
        self.sender_limit.blockSignals(False)
        self.delay_from.blockSignals(True)
        self.delay_from.setValue(float(getattr(self.state, "delay_from", 0.5)))
        self.delay_from.blockSignals(False)
        self.delay_to.blockSignals(True)
        self.delay_to.setValue(float(getattr(self.state, "delay_to", 1.0)))
        self.delay_to.blockSignals(False)
        self.retry_count.blockSignals(True)
        self.retry_count.setValue(int(getattr(self.state, "retry_count", 3)))
        self.retry_count.blockSignals(False)
        self.retry_enable_checkbox.blockSignals(True)
        self.retry_enable_checkbox.setChecked(bool(getattr(self.state, "retry_enabled", True)))
        self.retry_enable_checkbox.blockSignals(False)
        self.delay_fixed_radio.blockSignals(True)
        self.delay_random_radio.blockSignals(True)
        self.delay_human_radio.blockSignals(True)
        delay_type = getattr(self.state, "delay_type", "Random range")
        self.delay_fixed_radio.setChecked(delay_type == "Fixed")
        self.delay_random_radio.setChecked(delay_type != "Fixed" and delay_type != "Human-like pattern")
        self.delay_human_radio.setChecked(delay_type == "Human-like pattern")
        self.delay_fixed_radio.blockSignals(False)
        self.delay_random_radio.blockSignals(False)
        self.delay_human_radio.blockSignals(False)
        self.send_seq_radio.blockSignals(True)
        self.send_rand_radio.blockSignals(True)
        self.send_seq_radio.setChecked(getattr(self.state, "email_send_order", "Sequential") != "Random shuffle")
        self.send_rand_radio.setChecked(getattr(self.state, "email_send_order", "Sequential") == "Random shuffle")
        self.send_seq_radio.blockSignals(False)
        self.send_rand_radio.blockSignals(False)
        self.window_parallel_radio.blockSignals(True)
        self.window_sequential_radio.blockSignals(True)
        self.window_parallel_radio.setChecked(getattr(self.state, "window_send_mode", "Parallel") != "Sequential")
        self.window_sequential_radio.setChecked(getattr(self.state, "window_send_mode", "Parallel") == "Sequential")
        self.window_parallel_radio.blockSignals(False)
        self.window_sequential_radio.blockSignals(False)
        current_body = self._current_body_widget()
        if current_body is not None:
            current_body.set_mode(self.state.body_mode)
        self.active_windows_value.setText(str(len(self._browser_sessions)))
        self.launch_preset_label.setText(self.state.launch_preset or "None")
        self.progress_bar.setValue(0)
        self.ai_provider_combo.blockSignals(True)
        self.ai_provider_combo.setCurrentText(self.state.ai_provider)
        self.ai_provider_combo.blockSignals(False)
        self.ai_api_key_input.blockSignals(True)
        self.ai_api_key_input.setText(getattr(self.state, "ai_api_key", ""))
        self.ai_api_key_input.blockSignals(False)
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
        try:
            self.dashboard_page._persist_sending_settings_state()
        except Exception:
            pass
        self.dashboard_page._terminate_browser_sessions()
        self.state = AppState()
        self.dashboard_page.state = self.state
        self.dashboard_page.refresh()
        self.login_page.username_input.setText(DEFAULT_USERNAME)
        self.login_page.password_input.setText(DEFAULT_PASSWORD)
        self.login_page.error_label.setText("")
        self.show_login()
        self.show_toast("Logged out", "warning")

    def closeEvent(self, event) -> None:
        try:
            if hasattr(self, "dashboard_page"):
                self.dashboard_page._persist_subject_body_state()
                self.dashboard_page._persist_attachment_state()
                self.dashboard_page._persist_sending_settings_state()
        except Exception:
            pass
        super().closeEvent(event)


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

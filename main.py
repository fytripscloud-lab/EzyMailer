import sys
import html
from dataclasses import dataclass, field

from PySide6.QtCore import QDateTime, QEasingCurve, Property, QPropertyAnimation, QTimer, Qt, QEvent, QPoint
from PySide6.QtGui import QColor, QFont, QPainter, QPen
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
    QPushButton,
    QProgressBar,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QDoubleSpinBox,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QTextBrowser,
    QWidget,
)


APP_TITLE = "EzyMailer"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "01010202"


@dataclass
class AppState:
    username: str = ""
    logged_in: bool = False
    browser_mode: str = "Incognito"
    window_count: int = 1
    launch_preset: str = "Default"
    active_sessions: list[str] = field(default_factory=lambda: ["Window 1 - Idle"])
    activity_log: list[str] = field(default_factory=list)
    body_mode: str = "Normal Message"


class AnimatedLogoBadge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pulse = 0.0
        self.setFixedSize(40, 40)
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

        painter.setPen(QPen(QColor("#67e8f9"), 1.4))
        painter.drawLine(18, 10, 15, 19)
        painter.drawLine(15, 19, 21, 19)
        painter.drawLine(21, 19, 18, 29)

        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(self.rect(), Qt.AlignCenter, "EZ")


class TitleBar(QWidget):
    def __init__(self, window, on_close):
        super().__init__()
        self._window = window
        self._on_close = on_close
        self._drag_pos = None
        self._is_maximized = False
        self.setObjectName("topBar")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        brand = QHBoxLayout()
        brand.setSpacing(6)
        self.logo = AnimatedLogoBadge()
        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        title = QLabel("EzyMailer")
        title.setObjectName("brandTitle")
        subtitle = QLabel("Modern enterprise workspace for Gmail automation")
        subtitle.setObjectName("brandSubtitle")
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
            badge.setFixedHeight(28)
            badge.setMinimumWidth(64)
            badge.setAlignment(Qt.AlignCenter)
        version_badge.setToolTip("Application version")
        self.status_badge.setToolTip("Current login status")

        self.minimize_button = QPushButton("−")
        self.minimize_button.setObjectName("windowControlButton")
        self.minimize_button.setFixedSize(28, 28)
        self.minimize_button.clicked.connect(self._window.showMinimized)
        self.minimize_button.setToolTip("Minimize window")
        self.maximize_button = QPushButton("▢")
        self.maximize_button.setObjectName("windowControlButton")
        self.maximize_button.setFixedSize(28, 28)
        self.maximize_button.clicked.connect(self._toggle_maximize)
        self.maximize_button.setToolTip("Maximize or restore window")
        self.logout_button = QPushButton("Logout")
        self.logout_button.setObjectName("secondaryButton")
        self.logout_button.setFixedHeight(28)
        self.logout_button.setMinimumWidth(64)
        self.logout_button.setToolTip("Sign out and return to login")

        close_button = QPushButton("✕")
        close_button.setObjectName("closeButton")
        close_button.setFixedSize(28, 28)
        close_button.setText("✕")
        close_button.clicked.connect(self._on_close)
        close_button.setToolTip("Close application")

        layout.addLayout(brand)
        layout.addWidget(spacer)
        layout.addWidget(version_badge)
        layout.addWidget(self.status_badge)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.logout_button)
        layout.addWidget(close_button)

    def set_state(self, username: str, logged_in: bool) -> None:
        self.status_badge.setText("READY" if logged_in else "LOCKED")

    def sync_window_state(self) -> None:
        self._is_maximized = self._window.isMaximized()
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
    def __init__(self, parent: QWidget, message: str, kind: str = "info"):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setProperty("kind", kind)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setFixedWidth(360)
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
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        icon = QLabel("●")
        icon.setObjectName("toastIcon")
        icon.setFixedSize(14, 14)
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pulse = 0.0
        self._blink = False
        self.setFixedSize(104, 104)
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
        painter.drawEllipse(rect.adjusted(4, 4, -4, -4))

        # antenna
        painter.setPen(QPen(QColor("#8bd5ff"), 2))
        painter.drawLine(rect.center().x(), 10, rect.center().x(), 24)
        painter.setBrush(QColor("#f9fafb"))
        painter.drawEllipse(rect.center().x() - 4, 6, 8, 8)

        # head
        head = rect.adjusted(18, 24, -18, -24)
        painter.setBrush(QColor("#2d2d30"))
        painter.setPen(QPen(QColor("#4b4b4b"), 1))
        painter.drawRoundedRect(head, 18, 18)

        # eyes
        eye_y = head.center().y() - 10
        eye_color = QColor("#9cdcfe") if not self._blink else QColor("#3a3d41")
        painter.setBrush(eye_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(head.center().x() - 19, eye_y, 12, 12, 4, 4)
        painter.drawRoundedRect(head.center().x() + 7, eye_y, 12, 12, 4, 4)

        # mouth / badge line
        painter.setBrush(QColor("#0e639c"))
        painter.drawRoundedRect(head.center().x() - 18, head.center().y() + 10, 36, 8, 4, 4)

        # body
        body = rect.adjusted(30, 56, -30, -16)
        painter.setBrush(QColor("#1e1e1e"))
        painter.setPen(QPen(QColor("#3c3c3c"), 1))
        painter.drawRoundedRect(body, 10, 10)
        painter.setPen(QPen(QColor("#6b7280"), 2))
        painter.drawLine(body.left() + 10, body.bottom() - 8, body.right() - 10, body.bottom() - 8)
        painter.drawLine(body.left() + 14, body.bottom() - 4, body.left() + 14, body.bottom() + 4)
        painter.drawLine(body.right() - 14, body.bottom() - 4, body.right() - 14, body.bottom() + 4)


class LaunchLoaderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("launchLoader")
        self._dots = 0
        self._build_ui()

        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(260)
        self._dot_timer.timeout.connect(self._animate_dots)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(0)

        root.addStretch()

        card = QFrame()
        card.setObjectName("loaderCard")
        card.setFixedWidth(360)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(10)
        card_layout.setAlignment(Qt.AlignCenter)

        self.robot = RobotLoaderBadge()
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
    def __init__(self, parent: QWidget, title: str, message: str):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setObjectName("confirmDialog")
        self._build_ui(title, message)

    def _build_ui(self, title: str, message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("confirmCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

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


class OutputOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Output File Options")
        self.setModal(True)
        self.setObjectName("outputDialog")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        layout.addWidget(self._dialog_card("OUTPUT FORMAT", [
            "PDF Document",
            "Excel Spreadsheet (XLSX)",
            "Excel Template (XLTX)",
            "PowerPoint Presentation (PPTX)",
            "PowerPoint Slideshow (PPSX)",
            "Word Document (DOCX)",
        ]))

        file_card = QFrame()
        file_card.setObjectName("dialogCard")
        file_layout = QVBoxLayout(file_card)
        file_layout.setContentsMargins(12, 12, 12, 12)
        file_layout.setSpacing(8)
        title = QLabel("OUTPUT FILENAME")
        title.setObjectName("sectionTitle")
        file_layout.addWidget(title)

        self.auto_name = QRadioButton("Auto-generated (random unique name)")
        self.custom_name = QRadioButton("Custom name:")
        self.auto_name.setChecked(True)
        file_layout.addWidget(self.auto_name)
        custom_row = QHBoxLayout()
        self.custom_name_input = QLineEdit()
        self.custom_name_input.setPlaceholderText("Custom name")
        custom_row.addWidget(self.custom_name)
        custom_row.addWidget(self.custom_name_input, 1)
        custom_row.addWidget(QLabel(".pptx"))
        file_layout.addLayout(custom_row)
        layout.addWidget(file_card)

        image_card = QFrame()
        image_card.setObjectName("dialogCard")
        image_layout = QVBoxLayout(image_card)
        image_layout.setContentsMargins(12, 12, 12, 12)
        image_layout.setSpacing(8)
        image_title = QLabel("IMAGE")
        image_title.setObjectName("sectionTitle")
        image_layout.addWidget(image_title)
        image_layout.addWidget(QLabel("Image format used to capture the page before the document is built."))
        image_layout.addWidget(QLabel("Supported reference formats: PNG, JPG, WEBP"))
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
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        card_layout.addWidget(title_label)
        for option in options:
            card_layout.addWidget(QRadioButton(option))
        return card


class HtmlPreviewDialog(QDialog):
    def __init__(self, parent: QWidget, title: str, html: str, source_label: str = ""):
        super().__init__(parent)
        self.setModal(False)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setObjectName("previewDialog")
        self._source_html = html
        self._source_visible = False
        self._build_ui(title, source_label, html)

    def _build_ui(self, title: str, source_label: str, html: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        card = QFrame()
        card.setObjectName("previewCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(10)

        header_row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        header_row.addWidget(title_label)
        header_row.addStretch()
        reload_button = QPushButton("Reload")
        reload_button.setObjectName("secondaryButton")
        reload_button.setFixedHeight(28)
        reload_button.setToolTip("Reload the preview from the current HTML source")
        reload_button.clicked.connect(self._reload_preview)

        source_button = QPushButton("Source")
        source_button.setObjectName("secondaryButton")
        source_button.setFixedHeight(28)
        source_button.setCheckable(True)
        source_button.setToolTip("Show or hide the raw HTML source")
        source_button.clicked.connect(self._toggle_source_view)
        self.source_button = source_button

        zoom_out_button = QPushButton("A-")
        zoom_out_button.setObjectName("secondaryButton")
        zoom_out_button.setFixedHeight(28)
        zoom_out_button.setToolTip("Zoom out the rendered preview")
        zoom_out_button.clicked.connect(lambda: self._zoom_preview(-1))

        zoom_reset_button = QPushButton("100%")
        zoom_reset_button.setObjectName("secondaryButton")
        zoom_reset_button.setFixedHeight(28)
        zoom_reset_button.setToolTip("Reset the preview zoom level")
        zoom_reset_button.clicked.connect(self._reset_zoom)

        zoom_in_button = QPushButton("A+")
        zoom_in_button.setObjectName("secondaryButton")
        zoom_in_button.setFixedHeight(28)
        zoom_in_button.setToolTip("Zoom in the rendered preview")
        zoom_in_button.clicked.connect(lambda: self._zoom_preview(1))

        for button in (reload_button, source_button, zoom_out_button, zoom_reset_button, zoom_in_button):
            header_row.addWidget(button)

        close_button = QPushButton("Close")
        close_button.setObjectName("secondaryButton")
        close_button.setFixedHeight(28)
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
        self.source_view.setMinimumHeight(180)
        card_layout.addWidget(self.source_view)

        layout.addWidget(card)
        self.resize(920, 680)

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
    def __init__(self, on_login):
        super().__init__()
        self.on_login = on_login
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.error_label = QLabel("")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(0)

        root.addStretch()

        shell = QFrame()
        shell.setObjectName("loginShell")
        shell.setMaximumWidth(480)
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(22, 22, 22, 22)
        shell_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)
        logo = AnimatedLogoBadge()
        logo.setFixedSize(48, 48)

        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        brand = QLabel("EzyMailer")
        brand.setObjectName("loginAppName")
        kicker = QLabel("Gmail automation workspace")
        kicker.setObjectName("loginKicker")
        title_block.addWidget(brand)
        title_block.addWidget(kicker)

        header.addWidget(logo)
        header.addLayout(title_block)
        header.addStretch()

        intro = QLabel("Sign in to continue")
        intro.setObjectName("loginTitle")
        intro.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Temporary local access for the current design milestone.")
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

        login_button = QPushButton("Sign In")
        login_button.setObjectName("primaryButton")
        login_button.setMinimumHeight(38)
        login_button.clicked.connect(lambda: self._attempt_login())
        login_button.setToolTip("Authenticate and open the workspace")

        footer = QLabel("Local credentials: admin / 01010202")
        footer.setObjectName("loginHint")
        footer.setAlignment(Qt.AlignCenter)
        footer.setWordWrap(True)

        shell_layout.addLayout(header)
        shell_layout.addWidget(intro)
        shell_layout.addWidget(subtitle)
        shell_layout.addLayout(form)
        shell_layout.addWidget(self.error_label)
        shell_layout.addWidget(login_button)
        shell_layout.addWidget(footer)

        root.addWidget(shell, alignment=Qt.AlignHCenter)
        root.addStretch()

        self.username_input.returnPressed.connect(self._attempt_login)
        self.password_input.returnPressed.connect(self._attempt_login)

    def _attempt_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if username == DEFAULT_USERNAME and password == DEFAULT_PASSWORD:
            self.error_label.setText("")
            self.on_login(username)
            return

        self.error_label.setText("Invalid username or password.")


class DashboardPage(QWidget):
    def __init__(self, state: AppState, on_logout, notify):
        super().__init__()
        self.state = state
        self.on_logout = on_logout
        self.notify = notify
        self.session_list = QListWidget()
        self.window_spin = QSpinBox()
        self.incognito_button = QPushButton("Incognito")
        self.normal_button = QPushButton("Normal Mode")
        self.normal_message_button = QPushButton("Normal Message")
        self.html_message_button = QPushButton("HTML Message")
        self.data_summary_labels: dict[str, QLabel] = {}
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
        self.window_mode_group = QButtonGroup(self)
        self.delay_type_group = QButtonGroup(self)
        self.send_order_group = QButtonGroup(self)
        self.body_mode_group = QButtonGroup(self)
        self._session_timer = QTimer(self)
        self._session_timer.setSingleShot(False)
        self._session_timer.timeout.connect(self._advance_session_states)
        self._session_stage = 0
        self._session_running = False
        self._row_animations: list[QPropertyAnimation] = []
        self._floating_windows: list[QDialog] = []
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
        sidebar.setMinimumWidth(300)
        sidebar.setMaximumWidth(320)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        launch_card, launch_layout = self._card("Browser Launch Controls")
        self.window_spin.setRange(1, 99)
        self.window_spin.setValue(self.state.window_count)
        self.window_spin.setObjectName("windowSpin")
        self.window_spin.valueChanged.connect(self._window_count_changed)

        launch_row = QHBoxLayout()
        launch_row.setSpacing(8)

        launch_button = QPushButton("Start")
        launch_button.setObjectName("primaryButton")
        launch_button.clicked.connect(lambda: self._handle_launch())
        launch_button.setToolTip("Start the browser session workflow")

        pause_button = QPushButton("Pause")
        pause_button.setObjectName("warningButton")
        pause_button.clicked.connect(lambda: self._handle_pause())
        pause_button.setToolTip("Pause active browser sessions")

        reset_button = QPushButton("Reset")
        reset_button.setObjectName("dangerButton")
        reset_button.clicked.connect(lambda: self._handle_reset())
        reset_button.setToolTip("Reset all launch and session settings")

        launch_layout.addWidget(self._labeled_value_row("Number of Windows", self.window_spin))
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

        mode_card, mode_layout = self._card("Browser Mode", "Choose how sessions should launch.")
        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        self._configure_segmented_button(self.incognito_button, checked=True)
        self._configure_segmented_button(self.normal_button)
        mode_group.addButton(self.incognito_button)
        mode_group.addButton(self.normal_button)
        self.incognito_button.clicked.connect(lambda: self._set_browser_mode("Incognito"))
        self.normal_button.clicked.connect(lambda: self._set_browser_mode("Normal"))
        self.incognito_button.setToolTip("Launch windows in private browsing mode")
        self.normal_button.setToolTip("Launch windows in normal browsing mode")
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.incognito_button)
        mode_row.addWidget(self.normal_button)
        mode_layout.addLayout(mode_row)

        sessions_card, sessions_layout = self._card("Active Sessions", "Current browser windows and their state.")
        self.session_list.setObjectName("sessionList")
        self.session_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sessions_layout.addWidget(self.session_list)

        activity_card, activity_layout = self._card("Activity Log", "Recent automation events.")
        self.activity_log_view.setObjectName("activityList")
        self.activity_log_view.setReadOnly(True)
        self.activity_log_view.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.activity_log_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        activity_layout.addWidget(self.activity_log_view)

        blast_button = QPushButton("Start Blast")
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
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.addTab(self._build_data_tab(), "Data")
        self.tabs.addTab(self._build_subject_body_tab(), "Subject+Body")
        self.tabs.addTab(self._build_html_content_tab(), "Content")
        self.tabs.addTab(self._build_settings_tab(), "Settings")
        self.tabs.addTab(self._build_blaster_tab(), "Blaster")
        self.tabs.addTab(self._build_tags_tab(), "Tags")
        for index, tip in enumerate(
            [
                "Customer database and pending email list",
                "Subject and body composition",
                "HTML content and attachment setup",
                "Sending and runtime settings",
                "Launch and progress controls",
                "Dynamic tag management",
            ]
        ):
            self.tabs.setTabToolTip(index, tip)

        layout.addWidget(self.tabs)
        return content

    def _build_data_tab(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setSpacing(10)

        header = self._section_title("CUSTOMER EMAILS")
        page_layout.addWidget(header)

        self.pending_emails_editor.setPlaceholderText("Paste email addresses here, one per line...")
        self.pending_emails_editor.setObjectName("bodyEditor")
        self.pending_emails_editor.setMinimumHeight(360)
        self.pending_emails_editor.setToolTip("Paste recipient email addresses, one per line")
        page_layout.addWidget(self.pending_emails_editor, 1)

        filter_card, filter_layout = self._card(
            "EMAIL DOMAIN FILTER", "Choose whether to accept only Gmail addresses or all aliases."
        )
        filter_row = QHBoxLayout()
        self.standard_email_radio = QRadioButton("Standard Email (@gmail.com only)")
        self.mix_email_radio = QRadioButton("Mix Email (All Domains & Aliases)")
        self.standard_email_radio.setChecked(True)
        self.standard_email_radio.setToolTip("Accept only Gmail addresses")
        self.mix_email_radio.setToolTip("Allow Gmail and alias domains")
        filter_row.addWidget(self.standard_email_radio)
        filter_row.addWidget(self.mix_email_radio)
        filter_row.addStretch()
        filter_layout.addLayout(filter_row)

        actions_row = QHBoxLayout()
        load_button = QPushButton("Load from File")
        load_button.setObjectName("secondaryButton")
        clear_button = QPushButton("Clear List")
        clear_button.setObjectName("secondaryButton")
        validate_button = QPushButton("Validate & Count")
        validate_button.setObjectName("primaryButton")
        load_button.setToolTip("Load recipient emails from a file")
        clear_button.setToolTip("Clear the current recipient list")
        validate_button.setToolTip("Validate emails and count the results")
        load_button.clicked.connect(lambda: self._log_action("Loaded pending emails from file"))
        clear_button.clicked.connect(lambda: self._clear_pending_emails())
        validate_button.clicked.connect(lambda: self._log_action("Validated email list"))
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
            card_layout.setContentsMargins(10, 8, 10, 8)
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
        page_layout.setSpacing(10)

        window_card, window_layout = self._card("SUBJECT + BODY", "Compose message content for the selected window.")
        window_pill = QLabel("Window 1")
        window_pill.setObjectName("windowPill")
        window_layout.addWidget(window_pill)

        subject_row = QHBoxLayout()
        subject_label = QLabel("Subject")
        subject_label.setObjectName("fieldLabel")
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("Type your subject here")
        self.subject_input.setText("$word3 MIXED $word3")
        self.subject_input.setToolTip("Set the email subject line")
        subject_row.addWidget(subject_label)
        subject_row.addWidget(self.subject_input, 1)
        window_layout.addLayout(subject_row)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_label = QLabel("Message Body")
        mode_label.setObjectName("fieldLabel")
        self._configure_segmented_button(self.normal_message_button, checked=True)
        self._configure_segmented_button(self.html_message_button)
        self.body_mode_group = QButtonGroup(self)
        self.body_mode_group.setExclusive(True)
        self.body_mode_group.addButton(self.normal_message_button)
        self.body_mode_group.addButton(self.html_message_button)
        self.normal_message_button.clicked.connect(lambda: self._set_body_mode("Normal Message"))
        self.html_message_button.clicked.connect(lambda: self._set_body_mode("HTML Message"))
        self.normal_message_button.setToolTip("Write a plain text message")
        self.html_message_button.setToolTip("Write or paste HTML message code")
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.normal_message_button)
        mode_row.addWidget(self.html_message_button)
        mode_row.addStretch()
        window_layout.addLayout(mode_row)

        self.body_editor = QTextEdit()
        self.html_message_editor = QTextEdit()
        self.body_editor.setPlaceholderText("Type your message here...")
        self.body_editor.setObjectName("bodyEditor")
        self.body_editor.setToolTip("Compose the normal text message body")
        self.body_editor.setPlainText(
            "Hello {{first_name}},\n\nThis is a modern design preview for your email automation workspace."
        )
        self.html_message_editor.setObjectName("bodyEditor")
        self.html_message_editor.setPlaceholderText("<!-- Paste HTML message code here -->")
        self.html_message_editor.setToolTip("Paste HTML email code here")
        self.html_message_editor.setPlainText(
            "<div style='font-family: Segoe UI;'>\n  <h2>Hello {{first_name}}</h2>\n  <p>Paste your HTML code here.</p>\n</div>"
        )
        self.message_stack = QStackedWidget()
        self.message_stack.addWidget(self.body_editor)
        self.message_stack.addWidget(self.html_message_editor)
        window_layout.addWidget(self.message_stack, 1)

        footer_row = QHBoxLayout()
        footer_row.setSpacing(8)
        load_subject = QPushButton("Load Subject from File")
        load_subject.setObjectName("secondaryButton")
        load_subject.clicked.connect(lambda: self._log_action("Loaded subject from file"))
        load_body = QPushButton("Load Body from File")
        load_body.setObjectName("secondaryButton")
        load_body.clicked.connect(lambda: self._log_action("Loaded body from file"))
        clear_button = QPushButton("Clear")
        clear_button.setObjectName("secondaryButton")
        clear_button.clicked.connect(lambda: self._clear_subject_body())
        preview_button = QPushButton("Preview")
        preview_button.setObjectName("primaryButton")
        preview_button.clicked.connect(lambda: self._preview_subject_body())
        guide_button = QPushButton("Spintax Guide")
        guide_button.setObjectName("warningButton")
        guide_button.clicked.connect(lambda: self._log_action("Opened spintax guide"))
        load_subject.setToolTip("Load a subject template from file")
        load_body.setToolTip("Load a body template from file")
        clear_button.setToolTip("Clear the subject and body fields")
        preview_button.setToolTip("Preview the current message content")
        guide_button.setToolTip("Open the spintax usage guide")

        for button in (load_subject, load_body, clear_button, preview_button, guide_button):
            footer_row.addWidget(button)
        footer_row.addStretch()
        window_layout.addLayout(footer_row)

        page_layout.addWidget(window_card, 1)
        return self._tab_scroll(page)

    def _build_html_content_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        header = self._section_title("HTML CONTENT EDITOR")
        layout.addWidget(header)

        status_banner = QFrame()
        status_banner.setObjectName("panelCard")
        status_layout = QHBoxLayout(status_banner)
        status_layout.setContentsMargins(12, 10, 12, 10)
        status_label = QLabel("No active windows")
        status_label.setObjectName("placeholderText")
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        layout.addWidget(status_banner)

        self.html_editor.setObjectName("bodyEditor")
        self.html_editor.setPlaceholderText("<!-- Paste your HTML email template here... -->")
        self.html_editor.setToolTip("Paste the HTML email template here")
        self.html_editor.setPlainText(
            "<html>\n  <body style='font-family: Segoe UI; background:#0f172a; color:#e5eefc;'>\n    <h1>Campaign Title</h1>\n    <p>Hello {{first_name}}, welcome to the preview.</p>\n  </body>\n</html>"
        )
        self.html_editor.setMinimumHeight(300)
        layout.addWidget(self.html_editor, 1)

        footer_row = QHBoxLayout()
        preview_html = QPushButton("Preview HTML")
        preview_html.setObjectName("primaryButton")
        convert_check = QCheckBox("Convert to File")
        convert_check.setChecked(True)
        convert_file = QPushButton("Convert to File")
        convert_file.setObjectName("secondaryButton")
        convert_preview = QPushButton("Convert & Preview")
        convert_preview.setObjectName("primaryButton")
        preview_html.setToolTip("Preview the HTML content")
        convert_check.setToolTip("Enable conversion to a file output")
        convert_file.setToolTip("Open the file output options")
        convert_preview.setToolTip("Convert the HTML and preview the output")
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

        attachment_hint = QLabel("PDF, images, and additional files can be attached later in the logic phase.")
        attachment_hint.setObjectName("sectionHint")
        attachment_hint.setWordWrap(True)
        attach_layout.addWidget(attachment_hint)

        layout.addWidget(attach_card)
        return self._tab_scroll(page)

    def _build_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

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
        delay_row.addWidget(QLabel("seconds (random delay range)"))
        delay_holder = QFrame()
        delay_holder.setLayout(delay_row)
        form.addRow(delay_holder)
        send_layout.addLayout(form)

        delay_type_row = QHBoxLayout()
        fixed_radio = QRadioButton("Fixed")
        random_radio = QRadioButton("Random Range")
        human_radio = QRadioButton("Human Pattern")
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
        sequential_window_radio = QRadioButton("Sequential (1 window at a time, rotate)")
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
        startup_checkbox = QCheckBox("Open custom URL in new tab on startup")
        self.custom_url_input.setPlaceholderText("Custom URL")
        startup_checkbox.setToolTip("Open a custom page when each session starts")
        self.custom_url_input.setToolTip("Enter the startup URL to open")
        startup_layout.addWidget(startup_checkbox)
        startup_layout.addWidget(self.custom_url_input)
        layout.addWidget(startup_card)

        save_button = QPushButton("Save Settings")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(lambda: self._log_action("Saved settings"))
        save_button.setToolTip("Save the current sending settings")
        layout.addWidget(save_button, alignment=Qt.AlignLeft)
        layout.addStretch()

        return self._tab_scroll(page)

    def _build_blaster_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

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

        start_button = QPushButton("Start Blast")
        start_button.setObjectName("blastButton")
        start_button.setMinimumHeight(54)
        start_button.clicked.connect(lambda: self._log_action("Start Blast pressed"))
        start_button.setToolTip("Start the email blasting workflow")
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
        layout.setSpacing(10)

        header = self._section_title("DYNAMIC TAGS", "Use these tags in Subject or Body — they generate random values when sending.")
        layout.addWidget(header)

        grid_card, grid_layout = self._card("", None)
        grid_layout.setContentsMargins(6, 6, 6, 6)
        tag_grid = QGridLayout()
        tag_grid.setSpacing(8)
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
        ]
        for index, (title, token, description) in enumerate(samples):
            tag_grid.addWidget(self._tag_card(title, token, description), index // 3, index % 3)
        grid_layout.addLayout(tag_grid)
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

        manual_card, manual_layout = self._card("MANUAL CUSTOM TAGS", "Values entered here will replace $custom1 and $custom2.")
        manual_layout.addWidget(QLabel("For example, you can add your phone number, email address, or anything else."))
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
        row_layout.setSpacing(10)

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
        row_layout.setSpacing(10)

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
        dialog = OutputOptionsDialog(self.window())
        if dialog.exec() == QDialog.Accepted:
            self._log_action("Opened output file options")
            if preview:
                self._log_action("Converted HTML and opened preview")
                self.notify("HTML conversion preview ready")
                self._preview_html_content(title="Converted HTML Preview")
            else:
                self.notify("Output file options confirmed")

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
        dialog = HtmlPreviewDialog(self.window(), title, html_content, source_label)
        self._floating_windows.append(dialog)
        dialog.finished.connect(lambda _result, d=dialog: self._remove_floating_window(d))
        dialog.destroyed.connect(lambda *_args, d=dialog: self._remove_floating_window(d))
        return dialog

    def _remove_floating_window(self, dialog: QDialog) -> None:
        if dialog in self._floating_windows:
            self._floating_windows.remove(dialog)

    def _preview_subject_body(self) -> None:
        subject = self.subject_input.text().strip() or "Subject Preview"
        if self.state.body_mode == "HTML Message":
            html_content = self.html_message_editor.toPlainText().strip()
            source = "Previewing the HTML message body."
            if not html_content:
                html_content = "<html><body style='background:#1e1e1e; color:#d4d4d4; font-family:Segoe UI;'>No HTML content available.</body></html>"
        else:
            body_text = self.body_editor.toPlainText().strip()
            source = "Previewing the plain-text body as rendered HTML."
            if not body_text:
                body_text = "No message body available."
            html_content = self._wrap_text_as_html(body_text, subject)

        dialog = self._build_preview_dialog("Message Preview", html_content, source)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._log_action("Opened message preview")
        self.notify("Message preview opened")

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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

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
        remove_button.setFixedWidth(36)
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
        self._log_action(f"Browser mode set to {mode}")
        self.notify(f"Browser mode changed to {mode}")

    def _set_body_mode(self, mode: str) -> None:
        self.state.body_mode = mode
        self.normal_message_button.setChecked(mode == "Normal Message")
        self.html_message_button.setChecked(mode == "HTML Message")
        self.message_stack.setCurrentIndex(0 if mode == "Normal Message" else 1)
        self._log_action(f"Body mode set to {mode}")
        self.notify(f"Body mode changed to {mode}")

    def _set_launch_preset(self, preset: str | None) -> None:
        self.state.launch_preset = preset or ""
        label = preset if preset else "None"
        self.launch_preset_label.setText(label)
        self._log_action(f"Launch preset set to {label}")
        self.notify(f"Launch preset updated: {label}")

    def _window_count_changed(self, value: int) -> None:
        self.state.window_count = max(1, value)

    def _handle_launch(self) -> None:
        title = "Confirm Launch"
        prompt = (
            f"Start {self.window_spin.value()} window(s) using {self.state.browser_mode} mode "
            f"and {self.launch_preset_label.text()} preset?"
        )
        confirm = ConfirmDialog(self.window(), title, prompt)
        if confirm.exec() != QDialog.Accepted:
            self.notify("Launch cancelled")
            return
        target = max(1, self.window_spin.value())
        self.state.window_count = target
        self._set_active_sessions(target, running=False)
        self._session_stage = 0
        self._session_running = False
        self._log_action(f"Preparing {target} window(s)")
        self.notify(f"Launching {target} window(s)")
        self._show_launch_loader(
            "Launching browser windows",
            "Applying browser mode and launch preset.",
        )
        QTimer.singleShot(1200, lambda t=target: self._complete_launch(t))

    def _handle_pause(self) -> None:
        self._session_timer.stop()
        self._session_running = False
        self.state.active_sessions = [self._replace_session_state(item, "Paused") for item in self.state.active_sessions]
        self._refresh_sessions()
        self._log_action("Paused active sessions")
        self.notify("Sessions paused")

    def _handle_stop(self) -> None:
        if not self.state.active_sessions:
            self.state.active_sessions = ["Window 1 - Paused"]
        else:
            self.state.active_sessions = [self._replace_session_state(item, "Paused") for item in self.state.active_sessions]
        self._session_timer.stop()
        self._session_running = False
        self._refresh_sessions()
        self._log_action("Paused the active session")

    def _handle_reset(self) -> None:
        self._session_timer.stop()
        self._session_running = False
        self._session_stage = 0
        self.state.window_count = 1
        self.state.browser_mode = "Incognito"
        self.state.body_mode = "Normal Message"
        self.state.launch_preset = "Default"
        self.state.active_sessions = ["Window 1 - Idle"]
        self.window_spin.setValue(1)
        self._refresh_sessions()
        self._refresh_controls()
        self._log_action("Reset workspace to defaults")
        self.notify("Workspace reset to defaults")

    def _close_session(self, index: int, session: str) -> None:
        if 0 <= index < len(self.state.active_sessions):
            list_item = self.session_list.item(index)
            row_widget = self.session_list.itemWidget(list_item) if list_item is not None else None
            if row_widget is not None:
                effect = QGraphicsOpacityEffect(row_widget)
                row_widget.setGraphicsEffect(effect)
                animation = QPropertyAnimation(effect, b"opacity", self)
                animation.setDuration(180)
                animation.setStartValue(1.0)
                animation.setEndValue(0.0)

                def finalize_close() -> None:
                    if 0 <= index < len(self.state.active_sessions):
                        self.state.active_sessions.pop(index)
                    self.state.window_count = max(0, len(self.state.active_sessions))
                    if not self.state.active_sessions:
                        self._session_timer.stop()
                        self._session_running = False
                        self.state.window_count = 0
                    self._refresh_sessions()
                    self._refresh_controls()
                    self._log_action(f"Closed browser window {session}")
                    self.notify(f"Closed {session}")

                animation.finished.connect(finalize_close)
                self._row_animations.append(animation)
                animation.finished.connect(lambda: self._row_animations.remove(animation) if animation in self._row_animations else None)
                animation.start()
                return
            self.state.active_sessions.pop(index)
        self.state.window_count = max(0, len(self.state.active_sessions))
        if not self.state.active_sessions:
            self._session_timer.stop()
            self._session_running = False
            self.state.window_count = 0
        self._refresh_sessions()
        self._refresh_controls()
        self._log_action(f"Closed browser window {session}")
        self.notify(f"Closed {session}")

    def _start_blast(self) -> None:
        self._handle_launch()

    def _show_launch_loader(self, title: str, subtitle: str) -> None:
        self.window().show_launch_loader(title, subtitle)

    def _complete_launch(self, target: int) -> None:
        self.window().hide_launch_loader()
        if target <= 0:
            return
        self._session_running = True
        self._session_stage = 0
        self._session_timer.start(700)
        self._log_action(f"Started {target} window(s)")
        self.notify(f"Start initiated for {target} window(s)")

    def _clear_subject_body(self) -> None:
        self.subject_input.clear()
        self.body_editor.clear()
        self._log_action("Cleared subject and body")

    def _clear_pending_emails(self) -> None:
        self.pending_emails_editor.clear()
        self.data_summary_labels["total"].setText("0")
        self.data_summary_labels["valid"].setText("0")
        self.data_summary_labels["invalid"].setText("0")
        self.data_summary_labels["duplicates"].setText("0")
        self._log_action("Cleared pending email list")

    def _set_active_sessions(self, count: int, running: bool) -> None:
        sessions: list[str] = []
        for index in range(1, count + 1):
            state_text = "Navigating" if not running else "Processing"
            sessions.append(f"Window {index} - {state_text}")
        self.state.active_sessions = sessions
        self._refresh_sessions()

    def _replace_session_state(self, session: str, state_text: str) -> str:
        prefix = session.split(" - ", 1)[0] if " - " in session else session
        return f"{prefix} - {state_text}"

    def _advance_session_states(self) -> None:
        if not self._session_running:
            return
        stages = ["Opened", "Processing"]
        if self._session_stage >= len(stages):
            self._session_timer.stop()
            return
        state_text = stages[self._session_stage]
        self.state.active_sessions = [
            self._replace_session_state(item, state_text) for item in self.state.active_sessions
        ]
        self._refresh_sessions()
        self._log_action(f"Session status updated: {state_text}")
        self.notify(f"Sessions {state_text.lower()}")
        self._session_stage += 1
        if self._session_stage >= len(stages):
            self._session_timer.stop()

    def _refresh_sessions(self) -> None:
        self.session_list.clear()
        for index, item in enumerate(self.state.active_sessions, start=1):
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
        self.message_stack.setCurrentIndex(0 if self.state.body_mode == "Normal Message" else 1)
        self.active_windows_value.setText(str(self.state.window_count))
        self.launch_preset_label.setText(self.state.launch_preset or "None")
        self.progress_bar.setValue(0)

    def _log_action(self, message: str) -> None:
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.state.activity_log.append(f"[{timestamp}] {message}")
        self._refresh_activity()
        if callable(self.notify):
            self.notify(message)

    def _session_row(self, session: str, index: int) -> QWidget:
        row = QFrame()
        row.setObjectName("sessionRow")
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(8, 7, 8, 7)
        row_layout.setSpacing(4)
        row.setMinimumHeight(52)

        dot = QLabel("●")
        dot.setObjectName("sessionDot")
        session_name, session_state = self._split_session(session, index)
        label = QLabel(session_name)
        label.setObjectName("sessionTitleSmall")
        state = QLabel(session_state)
        state.setObjectName("sessionState")
        label.setMinimumWidth(72)
        state.setMinimumWidth(80)
        state.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        close_button = QPushButton("✕")
        close_button.setObjectName("dangerButton")
        close_button.setFixedWidth(28)
        close_button.clicked.connect(lambda _, i=index - 1, s=session: self._close_session(i, s))
        close_button.setToolTip("Close this browser window")

        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        top_row.addWidget(dot)
        top_row.addWidget(label)
        top_row.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        bottom_row.addWidget(state)
        bottom_row.addStretch()
        bottom_row.addWidget(close_button)

        row_layout.addLayout(top_row)
        row_layout.addLayout(bottom_row)
        return row

    def _split_session(self, session: str, index: int) -> tuple[str, str]:
        if " - " in session:
            name, state = session.split(" - ", 1)
            return name, state
        return f"Window {index}", "Idle"

    def refresh(self) -> None:
        self.window_spin.setValue(self.state.window_count)
        self._refresh_controls()
        self._refresh_sessions()
        self._refresh_activity()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        self._toasts = []
        self._pending_launch_target = 0
        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.resize(1380, 860)
        self._build_ui()

    def _build_ui(self) -> None:
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = TitleBar(self, self.close)
        self.title_bar.set_logout_handler(self.handle_logout)
        self.title_bar.sync_window_state()
        self.launch_loader = LaunchLoaderDialog(self)

        self.stack = QStackedWidget()
        self.login_page = LoginPage(self.handle_login)
        self.dashboard_page = DashboardPage(self.state, self.handle_logout, self.show_toast)
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.dashboard_page)
        root.addWidget(self.title_bar)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(container)
        self._apply_styles()
        self.show_login()

    def show_toast(self, message: str, kind: str = "info") -> None:
        toast = Toast(self, message, kind)
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

    def _apply_styles(self) -> None:
        self.setFont(QFont("Segoe UI", 9))
        self.setStyleSheet(
            """
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
        )

    def show_login(self) -> None:
        self.hide_launch_loader()
        self.title_bar.set_state("", False)
        self.stack.setCurrentWidget(self.login_page)

    def show_dashboard(self) -> None:
        self.hide_launch_loader()
        self.title_bar.set_state(self.state.username, self.state.logged_in)
        self.dashboard_page.refresh()
        self.stack.setCurrentWidget(self.dashboard_page)

    def handle_login(self, username: str) -> None:
        self.state.username = username
        self.state.logged_in = True
        self.state.activity_log.append("User authenticated")
        self.title_bar.set_state(self.state.username, self.state.logged_in)
        self.show_dashboard()
        self.show_toast("Signed in successfully", "success")

    def handle_logout(self) -> None:
        self.hide_launch_loader()
        self.state = AppState()
        self.dashboard_page.state = self.state
        self.dashboard_page.refresh()
        self.login_page.username_input.setText(DEFAULT_USERNAME)
        self.login_page.password_input.setText(DEFAULT_PASSWORD)
        self.login_page.error_label.setText("")
        self.show_login()
        self.show_toast("Logged out", "warning")


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


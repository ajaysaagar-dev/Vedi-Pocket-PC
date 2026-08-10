"""
Vedi Pocket PC — Apple Glassmorphism PySide6 Desktop Controller
Native Python GUI control panel and multi-process manager for Screen Stream Server,
FastAPI Backend Agent, and Mobile Expo Dev Server.
"""

import sys
import os
import re
import socket
import subprocess
from typing import Optional

from PySide6.QtCore import (
    Qt, QProcess, QTimer, QSize, Signal, Slot,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
)
from PySide6.QtGui import (
    QIcon, QPixmap, QImage, QFont, QColor, QAction, QTextCursor,
    QPainter, QBrush, QPen
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTextEdit, QFrame, QGridLayout,
    QSystemTrayIcon, QMenu, QMessageBox, QGroupBox, QLineEdit,
    QSizePolicy, QFileDialog, QStyle, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect
)
import qrcode
from PIL import Image as PILImage


def get_lan_ip() -> str:
    """Find local Wi-Fi / Ethernet LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_free_port(preferred: int) -> int:
    port = preferred
    while is_port_in_use(port):
        port += 1
    return port


def generate_apple_qr(data: str, size: int = 170) -> QPixmap:
    """Generate an Apple-style crisp white QR code on dark glass background."""
    if not data:
        data = "VediPocketPC"
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#ffffff", back_color="#0a0a0f").convert("RGBA")
        
        im_bytes = img.tobytes("raw", "RGBA")
        qimg = QImage(im_bytes, img.width, img.height, img.width * 4, QImage.Format_RGBA8888).copy()
        pixmap = QPixmap.fromImage(qimg)
        return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception as e:
        print(f"[QR Error] Failed to generate QR: {e}")
        pix = QPixmap(size, size)
        pix.fill(QColor("#0a0a0f"))
        return pix


def kill_process_tree(pid: int):
    """Safely terminate a process and all its child trees on Windows."""
    if not pid:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass


# --- Apple Glassmorphism Pure Black & White QSS Theme ---
APPLE_GLASS_QSS = """
QMainWindow, QWidget#centralWidget {
    background-color: #000000;
    color: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
}

QFrame.glassCard {
    background-color: rgba(22, 22, 26, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
    padding: 16px;
}

QLabel {
    color: #ffffff;
}

QLabel.brandTitle {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
}

QLabel.brandSub {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.55);
    font-weight: 400;
}

QLabel.sectionTitle {
    font-size: 13px;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.45);
    text-transform: uppercase;
    letter-spacing: 1px;
}

QLabel.statusBadge {
    font-size: 11px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 12px;
    letter-spacing: 0.5px;
}

QLabel.statusRunning {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.35);
}

QLabel.statusStopped {
    background-color: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.08);
}

QPushButton {
    font-size: 13px;
    font-weight: 600;
    border-radius: 20px;
    padding: 10px 20px;
    background-color: rgba(255, 255, 255, 0.08);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.15);
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.16);
    border-color: rgba(255, 255, 255, 0.3);
}

QPushButton:pressed {
    background-color: rgba(255, 255, 255, 0.05);
}

QPushButton.primaryPill {
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #ffffff;
    font-weight: 700;
}

QPushButton.primaryPill:hover {
    background-color: rgba(255, 255, 255, 0.88);
    border-color: rgba(255, 255, 255, 0.88);
}

QPushButton.primaryPill:pressed {
    background-color: rgba(255, 255, 255, 0.7);
}

QPushButton.stopPill {
    background-color: rgba(239, 68, 68, 0.16);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.4);
}

QPushButton.stopPill:hover {
    background-color: rgba(239, 68, 68, 0.28);
    border-color: rgba(239, 68, 68, 0.6);
}

QPushButton.accentPill {
    background-color: rgba(255, 255, 255, 0.12);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.25);
}

QPushButton.accentPill:hover {
    background-color: rgba(255, 255, 255, 0.22);
}

QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    background-color: rgba(12, 12, 15, 0.9);
}

QTabBar::tab {
    background-color: transparent;
    color: rgba(255, 255, 255, 0.45);
    font-weight: 600;
    font-size: 12px;
    padding: 8px 18px;
    border-radius: 14px;
    margin-right: 4px;
}

QTabBar::tab:selected {
    background-color: rgba(255, 255, 255, 0.12);
    color: #ffffff;
}

QTextEdit {
    background-color: #050508;
    color: #ffffff;
    font-family: 'SF Mono', 'Consolas', 'Menlo', monospace;
    font-size: 12px;
    border: none;
    border-radius: 10px;
    padding: 12px;
    line-height: 1.5;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 0.2);
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 0.4);
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


def apply_glass_shadow(widget: QWidget, blur: int = 24, alpha: int = 120):
    """Apply an Apple-style subtle ambient drop shadow."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setColor(QColor(0, 0, 0, alpha))
    shadow.setOffset(0, 8)
    widget.setGraphicsEffect(shadow)


class ControllerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vedi Pocket PC")
        self.setMinimumSize(960, 700)
        self.setStyleSheet(APPLE_GLASS_QSS)

        # Base directories
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.server_dir = os.path.join(self.root_dir, "Screen-Stream-Server")
        self.backend_dir = os.path.join(self.root_dir, "Vedi-PocketPC-Backend")
        self.mobile_dir = os.path.join(self.root_dir, "Vedi-PocketPC-Mobile")

        # Network info
        self.lan_ip = get_lan_ip()
        self.stream_port = 8080
        self.backend_port = 8000
        self.expo_port = 8088

        # Pairing State
        self.pairing_pin = ""
        self.expo_url = ""

        # QProcess instances
        self.stream_process: Optional[QProcess] = None
        self.backend_process: Optional[QProcess] = None
        self.expo_process: Optional[QProcess] = None

        self._init_ui()
        self._init_tray()
        self._animate_window_fade_in()

        # Start servers automatically on launch
        QTimer.singleShot(400, self.start_all_servers)

    def _animate_window_fade_in(self):
        """Apple-style smooth window entry animation."""
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(450)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def _animate_qr_update(self, label: QLabel, pixmap: QPixmap):
        """Smooth fade pulse animation when updating QR codes."""
        effect = QGraphicsOpacityEffect(label)
        label.setGraphicsEffect(effect)

        anim_out = QPropertyAnimation(effect, b"opacity")
        anim_out.setDuration(150)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.2)
        anim_out.setEasingCurve(QEasingCurve.OutQuad)

        anim_in = QPropertyAnimation(effect, b"opacity")
        anim_in.setDuration(250)
        anim_in.setStartValue(0.2)
        anim_in.setEndValue(1.0)
        anim_in.setEasingCurve(QEasingCurve.InCubic)

        def swap():
            label.setPixmap(pixmap)
            anim_in.start()

        anim_out.finished.connect(swap)
        anim_out.start()

    def _init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(18)

        # --- Header Glass Card ---
        header_frame = QFrame()
        header_frame.setProperty("class", "glassCard")
        apply_glass_shadow(header_frame)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        brand_title = QLabel("Vedi Pocket PC")
        brand_title.setProperty("class", "brandTitle")

        brand_sub = QLabel("Apple Glassmorphism Controller · LAN Local Engine")
        brand_sub.setProperty("class", "brandSub")

        title_box.addWidget(brand_title)
        title_box.addWidget(brand_sub)

        self.lan_label = QLabel(f"🌐  {self.lan_ip}")
        self.lan_label.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #ffffff; "
            "background: rgba(255,255,255,0.08); padding: 6px 14px; "
            "border-radius: 14px; border: 1px solid rgba(255,255,255,0.12);"
        )

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(self.lan_label)

        main_layout.addWidget(header_frame)

        # --- Middle Split Layout: Controls + QR Displays ---
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(18)

        # Left Column: Service Status & Controls Card
        status_card = QFrame()
        status_card.setProperty("class", "glassCard")
        apply_glass_shadow(status_card)

        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(14)

        services_title = QLabel("System Services")
        services_title.setProperty("class", "sectionTitle")
        status_layout.addWidget(services_title)

        grid = QGridLayout()
        grid.setVerticalSpacing(14)
        grid.setHorizontalSpacing(16)

        # 1. Stream Server Row
        stream_lbl = QLabel("📡 Screen Stream (:8080)")
        stream_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.9);")
        grid.addWidget(stream_lbl, 0, 0)

        self.stream_status_badge = QLabel("OFFLINE")
        self.stream_status_badge.setProperty("class", "statusBadge statusStopped")
        grid.addWidget(self.stream_status_badge, 0, 1, alignment=Qt.AlignRight)

        # 2. Remote Agent Row
        backend_lbl = QLabel("🔧 Remote Agent (:8000)")
        backend_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.9);")
        grid.addWidget(backend_lbl, 1, 0)

        self.backend_status_badge = QLabel("OFFLINE")
        self.backend_status_badge.setProperty("class", "statusBadge statusStopped")
        grid.addWidget(self.backend_status_badge, 1, 1, alignment=Qt.AlignRight)

        # 3. Mobile Expo Server Row
        expo_lbl = QLabel("📱 Mobile Client (:8088)")
        expo_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.9);")
        grid.addWidget(expo_lbl, 2, 0)

        self.expo_status_badge = QLabel("OFFLINE")
        self.expo_status_badge.setProperty("class", "statusBadge statusStopped")
        grid.addWidget(self.expo_status_badge, 2, 1, alignment=Qt.AlignRight)

        status_layout.addLayout(grid)
        status_layout.addSpacing(6)

        # Master Controls Pills
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)

        self.start_btn = QPushButton("Start All Services")
        self.start_btn.setProperty("class", "primaryPill")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_all_servers)

        self.stop_btn = QPushButton("Stop All Services")
        self.stop_btn.setProperty("class", "stopPill")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_all_servers)

        self.restart_btn = QPushButton("Restart All Services")
        self.restart_btn.setProperty("class", "accentPill")
        self.restart_btn.setCursor(Qt.PointingHandCursor)
        self.restart_btn.clicked.connect(self.restart_all_servers)

        self.reload_expo_btn = QPushButton("Reload Mobile App (Clear Cache)")
        self.reload_expo_btn.setCursor(Qt.PointingHandCursor)
        self.reload_expo_btn.clicked.connect(self.reload_expo)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.restart_btn)
        btn_layout.addWidget(self.reload_expo_btn)

        status_layout.addLayout(btn_layout)
        status_layout.addStretch()

        middle_layout.addWidget(status_card, stretch=1)

        # Right Column: Apple Glass QR Code Cards (PC Pairing & Expo Client)
        qr_card = QFrame()
        qr_card.setProperty("class", "glassCard")
        apply_glass_shadow(qr_card)

        qr_layout = QHBoxLayout(qr_card)
        qr_layout.setSpacing(20)

        # PC Pairing QR Column
        pc_qr_box = QVBoxLayout()
        pc_qr_box.setSpacing(10)

        pc_title = QLabel("1. Scan PC Pairing QR")
        pc_title.setProperty("class", "sectionTitle")
        pc_title.setAlignment(Qt.AlignCenter)
        
        self.pc_qr_label = QLabel()
        self.pc_qr_label.setFixedSize(170, 170)
        self.pc_qr_label.setAlignment(Qt.AlignCenter)
        self.pc_qr_label.setStyleSheet(
            "background-color: #0a0a0f; border-radius: 14px; "
            "border: 1px solid rgba(255,255,255,0.12);"
        )
        self.pc_qr_label.setPixmap(generate_apple_qr(f"{self.lan_ip}:8000:0000", 170))

        self.pin_info_label = QLabel("PIN: ----")
        self.pin_info_label.setAlignment(Qt.AlignCenter)
        self.pin_info_label.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #ffffff; "
            "letter-spacing: 2px;"
        )

        pc_qr_box.addWidget(pc_title)
        pc_qr_box.addWidget(self.pc_qr_label, alignment=Qt.AlignCenter)
        pc_qr_box.addWidget(self.pin_info_label)

        # Expo App QR Column
        expo_qr_box = QVBoxLayout()
        expo_qr_box.setSpacing(10)

        expo_title = QLabel("2. Scan Expo Go QR")
        expo_title.setProperty("class", "sectionTitle")
        expo_title.setAlignment(Qt.AlignCenter)

        self.expo_qr_label = QLabel()
        self.expo_qr_label.setFixedSize(170, 170)
        self.expo_qr_label.setAlignment(Qt.AlignCenter)
        self.expo_qr_label.setStyleSheet(
            "background-color: #0a0a0f; border-radius: 14px; "
            "border: 1px solid rgba(255,255,255,0.12);"
        )
        self.expo_qr_label.setPixmap(generate_apple_qr(f"exp://{self.lan_ip}:8088", 170))

        self.expo_info_label = QLabel("Initializing Expo...")
        self.expo_info_label.setAlignment(Qt.AlignCenter)
        self.expo_info_label.setStyleSheet(
            "font-size: 11px; color: rgba(255,255,255,0.45); font-weight: 500;"
        )

        expo_qr_box.addWidget(expo_title)
        expo_qr_box.addWidget(self.expo_qr_label, alignment=Qt.AlignCenter)
        expo_qr_box.addWidget(self.expo_info_label)

        qr_layout.addLayout(pc_qr_box)
        qr_layout.addLayout(expo_qr_box)

        middle_layout.addWidget(qr_card, stretch=2)
        main_layout.addLayout(middle_layout)

        # --- Bottom Logs Glass Card Section ---
        logs_card = QFrame()
        logs_card.setProperty("class", "glassCard")
        apply_glass_shadow(logs_card)

        logs_layout = QVBoxLayout(logs_card)
        logs_layout.setContentsMargins(10, 10, 10, 10)
        logs_layout.setSpacing(8)

        tab_row = QHBoxLayout()
        self.tabs = QTabWidget()

        # Logs Tabs
        self.all_log_edit = QTextEdit()
        self.all_log_edit.setReadOnly(True)

        self.python_log_edit = QTextEdit()
        self.python_log_edit.setReadOnly(True)

        self.expo_log_edit = QTextEdit()
        self.expo_log_edit.setReadOnly(True)

        self.tabs.addTab(self.all_log_edit, "Combined Stream Logs")
        self.tabs.addTab(self.python_log_edit, "Python Backend Logs")
        self.tabs.addTab(self.expo_log_edit, "Expo Mobile Logs")

        clear_btn = QPushButton("Clear Console")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            "font-size: 11px; padding: 4px 12px; border-radius: 10px; "
            "background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.6);"
        )
        clear_btn.clicked.connect(self.clear_logs)

        tab_row.addWidget(self.tabs)
        logs_layout.addLayout(tab_row)
        logs_layout.addWidget(clear_btn, alignment=Qt.AlignRight)

        main_layout.addWidget(logs_card, stretch=1)

    def _init_tray(self):
        """Initialize System Tray icon and context menu."""
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)

        tray_menu = QMenu()
        tray_menu.setStyleSheet(
            "QMenu { background-color: #16161a; color: #ffffff; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; padding: 6px; }"
            "QMenu::item { padding: 6px 16px; border-radius: 4px; font-size: 12px; font-weight: 500; }"
            "QMenu::item:selected { background-color: rgba(255,255,255,0.15); }"
        )

        show_action = QAction("Show Controller", self)
        show_action.triggered.connect(self.show_normal)
        
        start_action = QAction("Start All Services", self)
        start_action.triggered.connect(self.start_all_servers)

        stop_action = QAction("Stop All Services", self)
        stop_action.triggered.connect(self.stop_all_servers)

        restart_action = QAction("Restart All Services", self)
        restart_action.triggered.connect(self.restart_all_servers)

        quit_action = QAction("Quit Vedi Pocket PC", self)
        quit_action.triggered.connect(self.quit_app)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(start_action)
        tray_menu.addAction(stop_action)
        tray_menu.addAction(restart_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def show_normal(self):
        self.show()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def closeEvent(self, event):
        """Minimize to tray when close button is clicked."""
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "Vedi Pocket PC",
                "Controller minimized to system tray.",
                QSystemTrayIcon.Information,
                2000
            )
            event.ignore()
        else:
            self.quit_app()

    def quit_app(self):
        self.stop_all_servers()
        QApplication.quit()

    # --- Log Appenders ---
    def append_log(self, target: str, text: str):
        if not text:
            return
        if target == "python":
            self.python_log_edit.append(text)
        elif target == "expo":
            self.expo_log_edit.append(text)
        
        self.all_log_edit.append(f"[{target.upper()}] {text}")

    def clear_logs(self):
        self.all_log_edit.clear()
        self.python_log_edit.clear()
        self.expo_log_edit.clear()

    # --- Server Process Management ---
    def start_all_servers(self):
        self.start_stream_server()
        self.start_backend_server()
        self.start_expo_server()

    def stop_all_servers(self):
        self.stop_stream_server()
        self.stop_backend_server()
        self.stop_expo_server()

    def restart_all_servers(self):
        self.append_log("python", "Restarting all system services...")
        self.stop_all_servers()
        QTimer.singleShot(800, self.start_all_servers)

    # 1. Screen Stream Server
    def start_stream_server(self):
        if self.stream_process and self.stream_process.state() != QProcess.NotRunning:
            return

        self.stream_port = find_free_port(8080)
        self.append_log("python", f"Starting Screen Stream Server on port {self.stream_port}...")

        self.stream_process = QProcess(self)
        self.stream_process.setWorkingDirectory(self.server_dir)

        env = QProcess.systemEnvironment()
        env.append(f"STREAM_PORT={self.stream_port}")
        env.append(f"STREAM_HOST=0.0.0.0")
        self.stream_process.setEnvironment(env)

        self.stream_process.readyReadStandardOutput.connect(self._on_stream_stdout)
        self.stream_process.readyReadStandardError.connect(self._on_stream_stderr)
        self.stream_process.finished.connect(self._on_stream_finished)

        self.stream_process.start(sys.executable, ["main.py"])

        self.stream_status_badge.setText("ACTIVE")
        self.stream_status_badge.setProperty("class", "statusBadge statusRunning")
        self.stream_status_badge.style().unpolish(self.stream_status_badge)
        self.stream_status_badge.style().polish(self.stream_status_badge)

    def _on_stream_stdout(self):
        if not self.stream_process:
            return
        data = self.stream_process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        self.append_log("python", f"[Stream] {data.strip()}")

    def _on_stream_stderr(self):
        if not self.stream_process:
            return
        data = self.stream_process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.append_log("python", f"[Stream Err] {data.strip()}")

    def _on_stream_finished(self):
        self.append_log("python", "Screen Stream Server process exited.")
        self.stream_status_badge.setText("OFFLINE")
        self.stream_status_badge.setProperty("class", "statusBadge statusStopped")
        self.stream_status_badge.style().unpolish(self.stream_status_badge)
        self.stream_status_badge.style().polish(self.stream_status_badge)
        self.stream_process = None

    def stop_stream_server(self):
        if self.stream_process:
            kill_process_tree(self.stream_process.processId())
            self.stream_process.kill()
            self.stream_process = None

    # 2. FastAPI Backend
    def start_backend_server(self):
        if self.backend_process and self.backend_process.state() != QProcess.NotRunning:
            return

        self.backend_port = find_free_port(8000)
        self.append_log("python", f"Starting Remote Agent Backend on port {self.backend_port}...")

        self.backend_process = QProcess(self)
        self.backend_process.setWorkingDirectory(self.backend_dir)

        env = QProcess.systemEnvironment()
        env.append(f"BACKEND_PORT={self.backend_port}")
        env.append(f"BACKEND_HOST=0.0.0.0")
        self.backend_process.setEnvironment(env)

        self.backend_process.readyReadStandardOutput.connect(self._on_backend_stdout)
        self.backend_process.readyReadStandardError.connect(self._on_backend_stderr)
        self.backend_process.finished.connect(self._on_backend_finished)

        self.backend_process.start(sys.executable, ["main.py"])

        self.backend_status_badge.setText("ACTIVE")
        self.backend_status_badge.setProperty("class", "statusBadge statusRunning")
        self.backend_status_badge.style().unpolish(self.backend_status_badge)
        self.backend_status_badge.style().polish(self.backend_status_badge)

    def _on_backend_stdout(self):
        if not self.backend_process:
            return
        data = self.backend_process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        text = data.strip()
        self.append_log("python", f"[Backend] {text}")

        # Parse pairing PIN
        match = re.search(r"Pairing PIN:\s*(\d{4})", text)
        if match:
            self.pairing_pin = match.group(1)
            self.pin_info_label.setText(f"PIN: {self.pairing_pin}")
            qr_payload = f"{self.lan_ip}:{self.backend_port}:{self.pairing_pin}"
            pix = generate_apple_qr(qr_payload, 170)
            self._animate_qr_update(self.pc_qr_label, pix)
            self.append_log("python", f"Captured PC Pairing PIN: {self.pairing_pin}")

    def _on_backend_stderr(self):
        if not self.backend_process:
            return
        data = self.backend_process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.append_log("python", f"[Backend Err] {data.strip()}")

    def _on_backend_finished(self):
        self.append_log("python", "Remote Agent Backend process exited.")
        self.backend_status_badge.setText("OFFLINE")
        self.backend_status_badge.setProperty("class", "statusBadge statusStopped")
        self.backend_status_badge.style().unpolish(self.backend_status_badge)
        self.backend_status_badge.style().polish(self.backend_status_badge)
        self.backend_process = None

    def stop_backend_server(self):
        if self.backend_process:
            kill_process_tree(self.backend_process.processId())
            self.backend_process.kill()
            self.backend_process = None

    # 3. Mobile Expo Server
    def start_expo_server(self):
        if self.expo_process and self.expo_process.state() != QProcess.NotRunning:
            return

        self.expo_port = find_free_port(8088)
        self.expo_url = f"exp://{self.lan_ip}:{self.expo_port}"
        self.append_log("expo", f"Starting Expo Server on {self.expo_url}...")

        self.expo_process = QProcess(self)
        self.expo_process.setWorkingDirectory(self.mobile_dir)

        npx_cmd = "npx.cmd" if sys.platform == "win32" else "npx"
        expo_args = ["expo", "start", "-c", "--host", "lan", "--port", str(self.expo_port)]

        self.expo_process.readyReadStandardOutput.connect(self._on_expo_stdout)
        self.expo_process.readyReadStandardError.connect(self._on_expo_stderr)
        self.expo_process.finished.connect(self._on_expo_finished)

        self.expo_process.start(npx_cmd, expo_args)

        self.expo_status_badge.setText("ACTIVE")
        self.expo_status_badge.setProperty("class", "statusBadge statusRunning")
        self.expo_status_badge.style().unpolish(self.expo_status_badge)
        self.expo_status_badge.style().polish(self.expo_status_badge)

        pix = generate_apple_qr(self.expo_url, 170)
        self._animate_qr_update(self.expo_qr_label, pix)
        self.expo_info_label.setText(f"exp://{self.lan_ip}:{self.expo_port}")

    def _on_expo_stdout(self):
        if not self.expo_process:
            return
        data = self.expo_process.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        text = data.strip()
        self.append_log("expo", text)

        # Detect exp:// URL
        clean_text = re.sub(r"\x1b\[[0-9;]*m", "", text)
        match = re.search(r"exp://[\w.\-]+(?::\d+)?[^\s]*", clean_text)
        if match:
            self.expo_url = match.group(0)
            pix = generate_apple_qr(self.expo_url, 170)
            self._animate_qr_update(self.expo_qr_label, pix)
            self.expo_info_label.setText(self.expo_url)

    def _on_expo_stderr(self):
        if not self.expo_process:
            return
        data = self.expo_process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.append_log("expo", data.strip())

    def _on_expo_finished(self):
        self.append_log("expo", "Expo Server process exited.")
        self.expo_status_badge.setText("OFFLINE")
        self.expo_status_badge.setProperty("class", "statusBadge statusStopped")
        self.expo_status_badge.style().unpolish(self.expo_status_badge)
        self.expo_status_badge.style().polish(self.expo_status_badge)
        self.expo_process = None

    def stop_expo_server(self):
        if self.expo_process:
            kill_process_tree(self.expo_process.processId())
            self.expo_process.kill()
            self.expo_process = None

    def reload_expo(self):
        if self.expo_process and self.expo_process.state() == QProcess.Running:
            self.append_log("expo", "Sending 'r' key signal to reload connected Expo devices...")
            self.expo_process.write(b"r\n")
        else:
            self.append_log("expo", "Expo process not running, restarting...")
            self.stop_expo_server()
            QTimer.singleShot(500, self.start_expo_server)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    window = ControllerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""
Vedi Pocket PC — PySide6 Desktop Controller
Exact implementation of ref/dark.html and ref/other.html with top-right Theme Switcher (Dark Mode default).
"""

import sys
import os
import re
import socket
import subprocess
from typing import Optional

from PySide6.QtCore import Qt, QProcess, QTimer, QSize, Signal, Slot
from PySide6.QtGui import QIcon, QPixmap, QImage, QFont, QColor, QAction, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTextEdit, QFrame, QGridLayout,
    QSystemTrayIcon, QMenu, QMessageBox, QGroupBox, QLineEdit,
    QSizePolicy, QFileDialog, QStyle, QGraphicsDropShadowEffect
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


def generate_qr_pixmap(data: str, size: int = 180) -> QPixmap:
    """Generate a clean QR code QPixmap."""
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
        img = qr.make_image(fill_color="#000000", back_color="#ffffff").convert("RGBA")
        
        im_bytes = img.tobytes("raw", "RGBA")
        qimg = QImage(im_bytes, img.width, img.height, img.width * 4, QImage.Format_RGBA8888).copy()
        pixmap = QPixmap.fromImage(qimg)
        return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception as e:
        print(f"[QR Error] Failed to generate QR: {e}")
        pix = QPixmap(size, size)
        pix.fill(QColor("#ffffff"))
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


# --- Theme QSS Definitions (ref/dark.html & ref/other.html) ---

DARK_THEME_QSS = """
QMainWindow, QWidget#centralWidget {
    background-color: #131313;
    color: #e5e2e1;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

QFrame.glassPanel {
    background-color: rgba(19, 19, 19, 0.85);
    border: 1px solid #2C2C2E;
    border-radius: 12px;
    padding: 16px;
}

QLabel {
    color: #e5e2e1;
}

QLabel.titleLabel {
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
}

QLabel.subTitleLabel {
    font-size: 13px;
    color: #c4c7c8;
}

QLabel.sectionTitle {
    font-size: 12px;
    font-weight: 600;
    color: #c4c7c8;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QLabel.statusBadgeActive {
    font-size: 10px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 12px;
    background-color: rgba(78, 222, 163, 0.12);
    color: #4edea3;
    border: 1px solid rgba(78, 222, 163, 0.3);
}

QLabel.statusBadgeOffline {
    font-size: 10px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 12px;
    background-color: rgba(255, 180, 171, 0.1);
    color: #ffb4ab;
    border: 1px solid rgba(255, 180, 171, 0.25);
}

QPushButton {
    font-size: 14px;
    font-weight: 500;
    border-radius: 8px;
    padding: 10px 16px;
    background-color: transparent;
    color: #e5e2e1;
    border: 1px solid #444748;
}

QPushButton:hover {
    background-color: #2a2a2a;
}

QPushButton.primaryBtn {
    background-color: #ffffff;
    color: #2f3131;
    border: none;
    font-weight: 600;
}

QPushButton.primaryBtn:hover {
    background-color: #e2e2e2;
}

QPushButton.stopBtn {
    background-color: rgba(147, 0, 10, 0.3);
    color: #ffb4ab;
    border: 1px solid rgba(255, 180, 171, 0.4);
    font-weight: 600;
}

QPushButton.stopBtn:hover {
    background-color: rgba(147, 0, 10, 0.5);
}

QPushButton.themeToggleBtn {
    font-size: 12px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 20px;
    background-color: #2a2a2a;
    color: #e5e2e1;
    border: 1px solid #444748;
}

QPushButton.themeToggleBtn:hover {
    background-color: #353534;
}

QTabWidget::pane {
    border: 1px solid #2C2C2E;
    border-radius: 8px;
    background-color: #000000;
}

QTabBar::tab {
    background-color: transparent;
    color: #c4c7c8;
    font-weight: 500;
    font-size: 12px;
    padding: 6px 16px;
    border-radius: 16px;
    margin: 4px;
}

QTabBar::tab:selected {
    background-color: #353534;
    color: #ffffff;
    border: 1px solid #444748;
}

QTextEdit {
    background-color: #000000;
    color: #4edea3;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 13px;
    border: none;
    border-radius: 6px;
    padding: 12px;
    line-height: 1.5;
}
"""

CYBER_THEME_QSS = """
QMainWindow, QWidget#centralWidget {
    background-color: #0A0C10;
    color: #F3F4F6;
    font-family: 'Inter', 'Segoe UI', sans-serif;
}

QFrame.glassPanel {
    background-color: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(6, 182, 212, 0.35);
    border-radius: 12px;
    padding: 16px;
}

QLabel {
    color: #F3F4F6;
}

QLabel.titleLabel {
    font-size: 24px;
    font-weight: 700;
    color: #06B6D4;
    letter-spacing: -0.5px;
}

QLabel.subTitleLabel {
    font-size: 13px;
    color: #D1D5DB;
}

QLabel.sectionTitle {
    font-size: 12px;
    font-weight: 600;
    color: #06B6D4;
    text-transform: uppercase;
    letter-spacing: 1px;
}

QLabel.statusBadgeActive {
    font-size: 10px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 12px;
    background-color: rgba(6, 182, 212, 0.2);
    color: #06B6D4;
    border: 1px solid rgba(6, 182, 212, 0.4);
}

QLabel.statusBadgeOffline {
    font-size: 10px;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 12px;
    background-color: rgba(244, 63, 94, 0.2);
    color: #F43F5E;
    border: 1px solid rgba(244, 63, 94, 0.4);
}

QPushButton {
    font-size: 14px;
    font-weight: 500;
    border-radius: 8px;
    padding: 10px 16px;
    background-color: rgba(17, 24, 39, 0.6);
    color: #A855F7;
    border: 1px solid rgba(168, 85, 247, 0.4);
}

QPushButton:hover {
    background-color: #1F2937;
}

QPushButton.primaryBtn {
    background-color: #06B6D4;
    color: #0A0C10;
    border: none;
    font-weight: 600;
}

QPushButton.primaryBtn:hover {
    background-color: rgba(6, 182, 212, 0.9);
}

QPushButton.stopBtn {
    background-color: rgba(159, 18, 57, 0.4);
    color: #F43F5E;
    border: 1px solid rgba(244, 63, 94, 0.5);
    font-weight: 600;
}

QPushButton.stopBtn:hover {
    background-color: rgba(159, 18, 57, 0.7);
}

QPushButton.themeToggleBtn {
    font-size: 12px;
    font-weight: 500;
    padding: 6px 14px;
    border-radius: 20px;
    background-color: #1F2937;
    color: #06B6D4;
    border: 1px solid rgba(6, 182, 212, 0.4);
}

QPushButton.themeToggleBtn:hover {
    background-color: #374151;
}

QTabWidget::pane {
    border: 1px solid rgba(6, 182, 212, 0.4);
    border-radius: 8px;
    background-color: #050608;
}

QTabBar::tab {
    background-color: transparent;
    color: #D1D5DB;
    font-weight: 500;
    font-size: 12px;
    padding: 6px 16px;
    border-radius: 16px;
    margin: 4px;
}

QTabBar::tab:selected {
    background-color: rgba(6, 182, 212, 0.2);
    color: #06B6D4;
    border: 1px solid rgba(6, 182, 212, 0.5);
}

QTextEdit {
    background-color: #050608;
    color: #06B6D4;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 13px;
    border: none;
    border-radius: 6px;
    padding: 12px;
    line-height: 1.5;
}
"""


class ControllerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vedi Pocket PC")
        self.setMinimumSize(980, 720)
        self.current_theme = "dark"
        self.setStyleSheet(DARK_THEME_QSS)

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

        # Start servers automatically on launch
        QTimer.singleShot(400, self.start_all_servers)

    def toggle_theme(self):
        if self.current_theme == "dark":
            self.current_theme = "cyber"
            self.setStyleSheet(CYBER_THEME_QSS)
            self.theme_toggle_btn.setText("🎨 Cyber Mode")
        else:
            self.current_theme = "dark"
            self.setStyleSheet(DARK_THEME_QSS)
            self.theme_toggle_btn.setText("🎨 Dark Mode")

    def _init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # --- Top Navigation Header (ref/dark.html) ---
        header_frame = QFrame()
        header_frame.setProperty("class", "glassPanel")
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 16, 20, 16)
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        brand_title = QLabel("Vedi Pocket PC")
        brand_title.setProperty("class", "titleLabel")

        brand_sub = QLabel("pywebview Apple Glassmorphism Desktop Controller")
        brand_sub.setProperty("class", "subTitleLabel")

        title_box.addWidget(brand_title)
        title_box.addWidget(brand_sub)

        # Top Right Pills & Theme Switcher
        top_right_box = QHBoxLayout()
        top_right_box.setSpacing(12)

        self.lan_label = QLabel(f"🌐  {self.lan_ip}")
        self.lan_label.setStyleSheet(
            "font-size: 13px; font-weight: 500; color: #e5e2e1; "
            "background: rgba(255,255,255,0.06); padding: 6px 16px; "
            "border-radius: 20px; border: 1px solid rgba(255,255,255,0.1);"
        )

        self.theme_toggle_btn = QPushButton("🎨 Dark Mode")
        self.theme_toggle_btn.setProperty("class", "themeToggleBtn")
        self.theme_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.theme_toggle_btn.clicked.connect(self.toggle_theme)

        top_right_box.addWidget(self.lan_label)
        top_right_box.addWidget(self.theme_toggle_btn)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addLayout(top_right_box)

        main_layout.addWidget(header_frame)

        # --- Main Content Grid Area (Spans 4 cols / 8 cols) ---
        middle_grid = QGridLayout()
        middle_grid.setSpacing(20)

        # Left Panel: System Services (Spans 4 cols)
        status_card = QFrame()
        status_card.setProperty("class", "glassPanel")

        status_layout = QVBoxLayout(status_card)
        status_layout.setSpacing(14)

        services_title = QLabel("SYSTEM SERVICES")
        services_title.setProperty("class", "sectionTitle")
        status_layout.addWidget(services_title)

        grid = QGridLayout()
        grid.setVerticalSpacing(14)
        grid.setHorizontalSpacing(16)

        # 1. Stream Server Row
        stream_lbl = QLabel("🖥️ Screen Stream (:8080)")
        stream_lbl.setStyleSheet("font-size: 14px; font-weight: 500;")
        grid.addWidget(stream_lbl, 0, 0)

        self.stream_status_badge = QLabel("ACTIVE")
        self.stream_status_badge.setProperty("class", "statusBadgeActive")
        grid.addWidget(self.stream_status_badge, 0, 1, alignment=Qt.AlignRight)

        # 2. Remote Agent Row
        backend_lbl = QLabel("📡 Remote Agent (:8000)")
        backend_lbl.setStyleSheet("font-size: 14px; font-weight: 500;")
        grid.addWidget(backend_lbl, 1, 0)

        self.backend_status_badge = QLabel("ACTIVE")
        self.backend_status_badge.setProperty("class", "statusBadgeActive")
        grid.addWidget(self.backend_status_badge, 1, 1, alignment=Qt.AlignRight)

        # 3. Mobile Client Row
        expo_lbl = QLabel("📱 Mobile Client (:8088)")
        expo_lbl.setStyleSheet("font-size: 14px; font-weight: 500;")
        grid.addWidget(expo_lbl, 2, 0)

        self.expo_status_badge = QLabel("ACTIVE")
        self.expo_status_badge.setProperty("class", "statusBadgeActive")
        grid.addWidget(self.expo_status_badge, 2, 1, alignment=Qt.AlignRight)

        status_layout.addLayout(grid)
        status_layout.addSpacing(8)

        # Master Controls Action Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)

        self.start_btn = QPushButton("Start All Services")
        self.start_btn.setProperty("class", "primaryBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_all_servers)

        self.stop_btn = QPushButton("Stop All Services")
        self.stop_btn.setProperty("class", "stopBtn")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.clicked.connect(self.stop_all_servers)

        self.restart_btn = QPushButton("Restart All Services")
        self.restart_btn.setCursor(Qt.PointingHandCursor)
        self.restart_btn.clicked.connect(self.restart_all_servers)

        self.reload_expo_btn = QPushButton("Reload Mobile App")
        self.reload_expo_btn.setCursor(Qt.PointingHandCursor)
        self.reload_expo_btn.clicked.connect(self.reload_expo)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.restart_btn)
        btn_layout.addWidget(self.reload_expo_btn)

        status_layout.addLayout(btn_layout)
        status_layout.addStretch()

        middle_grid.addWidget(status_card, 0, 0)

        # Right Panel Container: QR Cards (Spans 8 cols)
        pc_card = QFrame()
        pc_card.setProperty("class", "glassPanel")
        pc_layout = QVBoxLayout(pc_card)
        pc_layout.setContentsMargins(16, 20, 16, 20)
        pc_layout.setSpacing(12)
        pc_layout.setAlignment(Qt.AlignCenter)

        pc_title = QLabel("1. SCAN PC PAIRING QR")
        pc_title.setProperty("class", "sectionTitle")
        pc_title.setAlignment(Qt.AlignCenter)

        self.pc_qr_label = QLabel()
        self.pc_qr_label.setFixedSize(180, 180)
        self.pc_qr_label.setAlignment(Qt.AlignCenter)
        self.pc_qr_label.setStyleSheet("background-color: #ffffff; border-radius: 8px; padding: 8px;")
        self.pc_qr_label.setPixmap(generate_qr_pixmap(f"{self.lan_ip}:8000:0000", 164))

        self.pin_info_label = QLabel("PIN: ----")
        self.pin_info_label.setAlignment(Qt.AlignCenter)
        self.pin_info_label.setStyleSheet("font-size: 18px; font-weight: 600; letter-spacing: 2px;")

        pc_layout.addWidget(pc_title)
        pc_layout.addWidget(self.pc_qr_label, alignment=Qt.AlignCenter)
        pc_layout.addWidget(self.pin_info_label)

        expo_card = QFrame()
        expo_card.setProperty("class", "glassPanel")
        expo_layout = QVBoxLayout(expo_card)
        expo_layout.setContentsMargins(16, 20, 16, 20)
        expo_layout.setSpacing(12)
        expo_layout.setAlignment(Qt.AlignCenter)

        expo_title = QLabel("2. SCAN EXPO GO QR")
        expo_title.setProperty("class", "sectionTitle")
        expo_title.setAlignment(Qt.AlignCenter)

        self.expo_qr_label = QLabel()
        self.expo_qr_label.setFixedSize(180, 180)
        self.expo_qr_label.setAlignment(Qt.AlignCenter)
        self.expo_qr_label.setStyleSheet("background-color: #ffffff; border-radius: 8px; padding: 8px;")
        self.expo_qr_label.setPixmap(generate_qr_pixmap(f"exp://{self.lan_ip}:8088", 164))

        self.expo_info_label = QLabel("Initializing Expo...")
        self.expo_info_label.setAlignment(Qt.AlignCenter)
        self.expo_info_label.setStyleSheet("font-size: 12px; color: #c4c7c8;")

        expo_layout.addWidget(expo_title)
        expo_layout.addWidget(self.expo_qr_label, alignment=Qt.AlignCenter)
        expo_layout.addWidget(self.expo_info_label)

        middle_grid.addWidget(pc_card, 0, 1)
        middle_grid.addWidget(expo_card, 0, 2)

        middle_grid.setColumnStretch(0, 4)
        middle_grid.setColumnStretch(1, 4)
        middle_grid.setColumnStretch(2, 4)

        main_layout.addLayout(middle_grid)

        # --- Terminal Logs Panel (Spans 12 cols) ---
        logs_card = QFrame()
        logs_card.setProperty("class", "glassPanel")

        logs_layout = QVBoxLayout(logs_card)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setSpacing(0)

        # Terminal Header Bar with Tabs & Clear
        term_header = QWidget()
        term_header_layout = QHBoxLayout(term_header)
        term_header_layout.setContentsMargins(16, 10, 16, 10)

        self.tabs = QTabWidget()

        self.all_log_edit = QTextEdit()
        self.all_log_edit.setReadOnly(True)

        self.python_log_edit = QTextEdit()
        self.python_log_edit.setReadOnly(True)

        self.expo_log_edit = QTextEdit()
        self.expo_log_edit.setReadOnly(True)

        self.tabs.addTab(self.all_log_edit, "Combined Logs")
        self.tabs.addTab(self.python_log_edit, "Python Backend Logs")
        self.tabs.addTab(self.expo_log_edit, "Expo Mobile Logs")

        clear_btn = QPushButton("🧹 Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(
            "font-size: 12px; border: none; background: transparent; "
            "color: #c4c7c8; font-weight: 500;"
        )
        clear_btn.clicked.connect(self.clear_logs)

        term_header_layout.addWidget(self.tabs)
        term_header_layout.addWidget(clear_btn, alignment=Qt.AlignRight)

        logs_layout.addWidget(term_header)
        main_layout.addWidget(logs_card, stretch=1)

    def _init_tray(self):
        """Initialize System Tray icon and menu."""
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)

        tray_menu = QMenu()
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
                "Controller minimized to tray.",
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
        QTimer.singleShot(600, self.start_all_servers)

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
        self.stream_status_badge.setProperty("class", "statusBadgeActive")
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
        self.stream_status_badge.setProperty("class", "statusBadgeOffline")
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
        self.backend_status_badge.setProperty("class", "statusBadgeActive")
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
            pix = generate_qr_pixmap(qr_payload, 164)
            self.pc_qr_label.setPixmap(pix)
            self.append_log("python", f"Captured PC Pairing PIN: {self.pairing_pin}")

    def _on_backend_stderr(self):
        if not self.backend_process:
            return
        data = self.backend_process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.append_log("python", f"[Backend Err] {data.strip()}")

    def _on_backend_finished(self):
        self.append_log("python", "Remote Agent Backend process exited.")
        self.backend_status_badge.setText("OFFLINE")
        self.backend_status_badge.setProperty("class", "statusBadgeOffline")
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
        self.expo_status_badge.setProperty("class", "statusBadgeActive")
        self.expo_status_badge.style().unpolish(self.expo_status_badge)
        self.expo_status_badge.style().polish(self.expo_status_badge)

        pix = generate_qr_pixmap(self.expo_url, 164)
        self.expo_qr_label.setPixmap(pix)
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
            pix = generate_qr_pixmap(self.expo_url, 164)
            self.expo_qr_label.setPixmap(pix)
            self.expo_info_label.setText(self.expo_url)

    def _on_expo_stderr(self):
        if not self.expo_process:
            return
        data = self.expo_process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.append_log("expo", data.strip())

    def _on_expo_finished(self):
        self.append_log("expo", "Expo Server process exited.")
        self.expo_status_badge.setText("OFFLINE")
        self.expo_status_badge.setProperty("class", "statusBadgeOffline")
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

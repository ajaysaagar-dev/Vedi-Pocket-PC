"""
Vedi Pocket PC — PySide6 Desktop Controller
Native Python GUI control panel and multi-process manager for Screen Stream Server,
FastAPI Backend Agent, and Mobile Expo Dev Server.
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
    QSizePolicy, QFileDialog, QStyle
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
    """Generate a clean dark-themed QPixmap for a QR code."""
    if not data:
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        return pix
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#38bdf8", back_color="#0f172a").convert("RGBA")
        
        im_bytes = img.tobytes("raw", "RGBA")
        qimg = QImage(im_bytes, img.width, img.height, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimg)
        return pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    except Exception as e:
        print(f"[QR Error] Failed to generate QR: {e}")
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
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


DARK_QSS = """
QMainWindow, QWidget#centralWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: 'Segoe UI', system-ui, sans-serif;
}

QFrame.card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 12px;
}

QLabel {
    color: #f8fafc;
}

QLabel.titleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #38bdf8;
}

QLabel.sectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
}

QLabel.statusBadge {
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 12px;
}

QLabel.statusRunning {
    background-color: #064e3b;
    color: #34d399;
    border: 1px solid #059669;
}

QLabel.statusStopped {
    background-color: #451a03;
    color: #fb923c;
    border: 1px solid #d97706;
}

QPushButton {
    font-size: 13px;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 16px;
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
}

QPushButton:hover {
    background-color: #475569;
    border-color: #64748b;
}

QPushButton.primaryBtn {
    background-color: #0284c7;
    color: #ffffff;
    border: 1px solid #38bdf8;
}

QPushButton.primaryBtn:hover {
    background-color: #0369a1;
}

QPushButton.stopBtn {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
}

QPushButton.stopBtn:hover {
    background-color: #b91c1c;
}

QPushButton.accentBtn {
    background-color: #7c3aed;
    color: #ffffff;
    border: 1px solid #a78bfa;
}

QPushButton.accentBtn:hover {
    background-color: #6d28d9;
}

QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #1e293b;
}

QTabBar::tab {
    background-color: #0f172a;
    color: #94a3b8;
    font-weight: 600;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e293b;
    color: #38bdf8;
    border-bottom: 2px solid #38bdf8;
}

QTextEdit {
    background-color: #090d16;
    color: #34d399;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 8px;
}
"""


class ControllerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vedi Pocket PC — Controller")
        self.setMinimumSize(920, 680)
        self.setStyleSheet(DARK_QSS)

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
        QTimer.singleShot(500, self.start_all_servers)

    def _init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # --- Header Row ---
        header_frame = QFrame()
        header_frame.setProperty("class", "card")
        header_layout = QHBoxLayout(header_frame)
        
        app_title = QLabel("⚡ Vedi Pocket PC — Desktop Controller")
        app_title.setProperty("class", "titleLabel")

        self.lan_label = QLabel(f"🌐 LAN IP: {self.lan_ip}")
        self.lan_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #94a3b8;")

        header_layout.addWidget(app_title)
        header_layout.addStretch()
        header_layout.addWidget(self.lan_label)

        main_layout.addWidget(header_frame)

        # --- Middle Split Layout: Controls + QR Displays ---
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(16)

        # Left Column: Service Status & Controls Card
        status_card = QFrame()
        status_card.setProperty("class", "card")
        status_layout = QVBoxLayout(status_card)

        services_title = QLabel("System Services")
        services_title.setProperty("class", "sectionTitle")
        status_layout.addWidget(services_title)

        grid = QGridLayout()
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(16)

        # 1. Stream Server Row
        grid.addWidget(QLabel("📡 Screen Stream Server (:8080)"), 0, 0)
        self.stream_status_badge = QLabel("STOPPED")
        self.stream_status_badge.setProperty("class", "statusBadge statusStopped")
        grid.addWidget(self.stream_status_badge, 0, 1)

        # 2. Remote Agent Row
        grid.addWidget(QLabel("🔧 Remote Agent Backend (:8000)"), 1, 0)
        self.backend_status_badge = QLabel("STOPPED")
        self.backend_status_badge.setProperty("class", "statusBadge statusStopped")
        grid.addWidget(self.backend_status_badge, 1, 1)

        # 3. Mobile Expo Server Row
        grid.addWidget(QLabel("📱 Mobile Client App (:8088)"), 2, 0)
        self.expo_status_badge = QLabel("STOPPED")
        self.expo_status_badge.setProperty("class", "statusBadge statusStopped")
        grid.addWidget(self.expo_status_badge, 2, 1)

        status_layout.addLayout(grid)
        status_layout.addSpacing(16)

        # Master Controls
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        self.start_btn = QPushButton("🚀 Start All Services")
        self.start_btn.setProperty("class", "primaryBtn")
        self.start_btn.clicked.connect(self.start_all_servers)

        self.stop_btn = QPushButton("⏹️ Stop All Services")
        self.stop_btn.setProperty("class", "stopBtn")
        self.stop_btn.clicked.connect(self.stop_all_servers)

        self.restart_btn = QPushButton("🔄 Restart All Services")
        self.restart_btn.clicked.connect(self.restart_all_servers)

        self.reload_expo_btn = QPushButton("⚡ Reload Expo Mobile App (Clear Cache)")
        self.reload_expo_btn.setProperty("class", "accentBtn")
        self.reload_expo_btn.clicked.connect(self.reload_expo)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.restart_btn)
        btn_layout.addWidget(self.reload_expo_btn)

        status_layout.addLayout(btn_layout)
        status_layout.addStretch()

        middle_layout.addWidget(status_card, stretch=1)

        # Right Column: QR Code Cards (PC Pairing & Expo Client)
        qr_card = QFrame()
        qr_card.setProperty("class", "card")
        qr_layout = QHBoxLayout(qr_card)
        qr_layout.setSpacing(16)

        # PC Pairing QR Column
        pc_qr_box = QVBoxLayout()
        pc_title = QLabel("1. Scan PC Pairing QR")
        pc_title.setProperty("class", "sectionTitle")
        pc_title.setAlignment(Qt.AlignCenter)
        
        self.pc_qr_label = QLabel()
        self.pc_qr_label.setFixedSize(180, 180)
        self.pc_qr_label.setAlignment(Qt.AlignCenter)
        self.pc_qr_label.setPixmap(generate_qr_pixmap("", 180))

        self.pin_info_label = QLabel("PIN: ----")
        self.pin_info_label.setAlignment(Qt.AlignCenter)
        self.pin_info_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #38bdf8;")

        pc_qr_box.addWidget(pc_title)
        pc_qr_box.addWidget(self.pc_qr_label, alignment=Qt.AlignCenter)
        pc_qr_box.addWidget(self.pin_info_label)

        # Expo App QR Column
        expo_qr_box = QVBoxLayout()
        expo_title = QLabel("2. Scan Expo Go QR")
        expo_title.setProperty("class", "sectionTitle")
        expo_title.setAlignment(Qt.AlignCenter)

        self.expo_qr_label = QLabel()
        self.expo_qr_label.setFixedSize(180, 180)
        self.expo_qr_label.setAlignment(Qt.AlignCenter)
        self.expo_qr_label.setPixmap(generate_qr_pixmap("", 180))

        self.expo_info_label = QLabel("Waiting for Expo...")
        self.expo_info_label.setAlignment(Qt.AlignCenter)
        self.expo_info_label.setStyleSheet("font-size: 12px; color: #94a3b8;")

        expo_qr_box.addWidget(expo_title)
        expo_qr_box.addWidget(self.expo_qr_label, alignment=Qt.AlignCenter)
        expo_qr_box.addWidget(self.expo_info_label)

        qr_layout.addLayout(pc_qr_box)
        qr_layout.addLayout(expo_qr_box)

        middle_layout.addWidget(qr_card, stretch=2)
        main_layout.addLayout(middle_layout)

        # --- Bottom Logs Viewer Tabbed Section ---
        logs_card = QFrame()
        logs_card.setProperty("class", "card")
        logs_layout = QVBoxLayout(logs_card)
        logs_layout.setContentsMargins(8, 8, 8, 8)

        tab_row = QHBoxLayout()
        self.tabs = QTabWidget()

        # Tabs
        self.all_log_edit = QTextEdit()
        self.all_log_edit.setReadOnly(True)

        self.python_log_edit = QTextEdit()
        self.python_log_edit.setReadOnly(True)

        self.expo_log_edit = QTextEdit()
        self.expo_log_edit.setReadOnly(True)

        self.tabs.addTab(self.all_log_edit, "All Combined Logs")
        self.tabs.addTab(self.python_log_edit, "Python Server Logs")
        self.tabs.addTab(self.expo_log_edit, "Mobile Expo Server Logs")

        clear_btn = QPushButton("🧹 Clear Logs")
        clear_btn.clicked.connect(self.clear_logs)

        tab_row.addWidget(self.tabs)
        logs_layout.addLayout(tab_row)
        logs_layout.addWidget(clear_btn, alignment=Qt.AlignRight)

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
                "Controller minimized to tray. Double click icon to open.",
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
        QTimer.singleShot(1000, self.start_all_servers)

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

        self.stream_status_badge.setText("RUNNING")
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
        self.stream_status_badge.setText("STOPPED")
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

        self.backend_status_badge.setText("RUNNING")
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
            self.pc_qr_label.setPixmap(generate_qr_pixmap(qr_payload, 180))
            self.append_log("python", f"Captured PC Pairing PIN: {self.pairing_pin}")

    def _on_backend_stderr(self):
        if not self.backend_process:
            return
        data = self.backend_process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.append_log("python", f"[Backend Err] {data.strip()}")

    def _on_backend_finished(self):
        self.append_log("python", "Remote Agent Backend process exited.")
        self.backend_status_badge.setText("STOPPED")
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

        self.expo_status_badge.setText("RUNNING")
        self.expo_status_badge.setProperty("class", "statusBadge statusRunning")
        self.expo_status_badge.style().unpolish(self.expo_status_badge)
        self.expo_status_badge.style().polish(self.expo_status_badge)

        self.expo_qr_label.setPixmap(generate_qr_pixmap(self.expo_url, 180))
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
            self.expo_qr_label.setPixmap(generate_qr_pixmap(self.expo_url, 180))
            self.expo_info_label.setText(self.expo_url)

    def _on_expo_stderr(self):
        if not self.expo_process:
            return
        data = self.expo_process.readAllStandardError().data().decode("utf-8", errors="ignore")
        self.append_log("expo", data.strip())

    def _on_expo_finished(self):
        self.append_log("expo", "Expo Server process exited.")
        self.expo_status_badge.setText("STOPPED")
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

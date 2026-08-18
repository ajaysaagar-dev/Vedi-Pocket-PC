"""Tests for the pure Python desktop controller."""

from __future__ import annotations

import pytest

from apps.desktop.controller.legacy.network import find_free_port, get_lan_ip, is_port_in_use
from apps.desktop.controller.legacy.process_manager import ProcessManager
from apps.desktop.controller.legacy.qr import to_data_url


def test_get_lan_ip():
    ip = get_lan_ip()
    assert isinstance(ip, str)
    assert len(ip) > 0


def test_find_free_port():
    port = find_free_port(9990)
    assert isinstance(port, int)
    assert port >= 9990


def test_qr_to_data_url():
    data_url = to_data_url("192.168.1.100:8000:1234")
    assert data_url.startswith("data:image/png;base64,")


def test_process_manager_status_payload():
    pm = ProcessManager()
    payload = pm.get_status_payload()
    assert "lanIp" in payload
    assert "serverPort" in payload
    assert "backendPort" in payload
    assert "expoPort" in payload
    assert payload["isPythonRunning"] is False
    assert payload["isBackendRunning"] is False
    assert payload["isExpoRunning"] is False


def test_process_manager_log_listener():
    pm = ProcessManager()
    logs = []
    remove = pm.add_log_listener(lambda ch, msg: logs.append((ch, msg)))

    pm.emit_log("python-log", "test message\n")
    assert logs == [("python-log", "test message\n")]

    remove()
    pm.emit_log("python-log", "second message\n")
    assert len(logs) == 1

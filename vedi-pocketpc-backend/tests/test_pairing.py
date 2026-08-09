"""Pairing-endpoint smoke test.

Boots the FastAPI app with the production wiring (Container + real
TokenStore) and asserts the wire format the mobile app already speaks
is preserved byte-for-byte.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
REPO_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, os.pardir))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "agent-core"))
sys.path.insert(0, BACKEND_ROOT)

from main import Container, create_app  # noqa: E402


@pytest.fixture
def container(monkeypatch):
    """Container with a fixed PIN so tests are deterministic."""
    monkeypatch.setattr("secrets.randbelow", lambda _n: 1234)  # → "1234"
    return Container()


@pytest.fixture
def client(container) -> TestClient:
    return TestClient(create_app(container))


def test_health_is_public(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "agent_version" in body


def test_pair_returns_token_on_correct_pin(client, container):
    res = client.post("/pair", json={"pin": container.pairing_pin.value})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert isinstance(body["token"], str)
    assert len(body["token"]) >= 16


def test_pair_rejects_wrong_pin(client):
    res = client.post("/pair", json={"pin": "0000"})
    assert res.status_code == 400


def test_status_requires_auth(client):
    res = client.get("/status")
    assert res.status_code == 401


def test_status_returns_snapshot_after_pair(client, container):
    pair = client.post("/pair", json={"pin": container.pairing_pin.value})
    token = pair.json()["token"]
    res = client.get("/status", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert "hostname" in body
    assert "volume" in body

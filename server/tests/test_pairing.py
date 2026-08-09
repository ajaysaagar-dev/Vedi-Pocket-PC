"""Pairing-flow tests for unified server."""

from __future__ import annotations

import pytest

from server.domain.entities.pairing import PairingPin
from server.application.services.pairing import PairDevice
from server.infrastructure.adapters.memory_token_store import MemoryTokenStore


def test_pairing_succeeds_on_correct_pin(tmp_path):
    store = MemoryTokenStore(persistence_file=str(tmp_path / "ips.json"))
    use_case = PairDevice(PairingPin(value="1234"), store)

    result = use_case.pair("1234")

    assert result.accepted is True
    assert result.device_token is not None
    assert store.verify(result.device_token) is True


def test_pairing_rejects_wrong_pin(tmp_path):
    store = MemoryTokenStore(persistence_file=str(tmp_path / "ips.json"))
    use_case = PairDevice(PairingPin(value="1234"), store)

    result = use_case.pair("9999")

    assert result.accepted is False
    assert result.device_token is None
    assert result.reason is not None


def test_each_successful_pair_yields_unique_token(tmp_path):
    store = MemoryTokenStore(persistence_file=str(tmp_path / "ips.json"))
    use_case = PairDevice(PairingPin(value="1234"), store)

    a = use_case.pair("1234")
    b = use_case.pair("1234")

    assert a.device_token != b.device_token


def test_pin_format_validated():
    with pytest.raises(ValueError):
        PairingPin(value="abcd")
    with pytest.raises(ValueError):
        PairingPin(value="12")

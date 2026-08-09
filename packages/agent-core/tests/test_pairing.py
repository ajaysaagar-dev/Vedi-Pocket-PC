"""Pairing-flow tests — preserves the existing /pair contract."""

from __future__ import annotations

import pytest

from agent_core.entities.pairing import PairingPin
from agent_core.use_cases.pairing import PairDevice
from agent_core.adapters.memory_token_store import MemoryTokenStore


def test_pairing_succeeds_on_correct_pin():
    store = MemoryTokenStore()
    use_case = PairDevice(PairingPin(value="1234"), store)

    result = use_case.pair("1234")

    assert result.accepted is True
    assert result.device_token is not None
    assert store.verify(result.device_token) is True


def test_pairing_rejects_wrong_pin():
    store = MemoryTokenStore()
    use_case = PairDevice(PairingPin(value="1234"), store)

    result = use_case.pair("9999")

    assert result.accepted is False
    assert result.device_token is None
    assert result.reason is not None


def test_each_successful_pair_yields_unique_token():
    store = MemoryTokenStore()
    use_case = PairDevice(PairingPin(value="1234"), store)

    a = use_case.pair("1234")
    b = use_case.pair("1234")

    assert a.device_token != b.device_token


def test_pin_format_validated():
    with pytest.raises(ValueError):
        PairingPin(value="abcd")
    with pytest.raises(ValueError):
        PairingPin(value="12")  # too short

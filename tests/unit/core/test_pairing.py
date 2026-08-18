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


def test_pairing_emits_common_token():
    store = MemoryTokenStore()
    use_case = PairDevice(PairingPin(value="1234"), store)

    result = use_case.pair("1234")

    assert result.common_token is not None
    assert store.verify(result.common_token) is True


def test_common_token_is_stable_across_pairs():
    store = MemoryTokenStore()
    use_case = PairDevice(PairingPin(value="1234"), store)

    a = use_case.pair("1234")
    b = use_case.pair("1234")

    # device_token changes each time …
    assert a.device_token != b.device_token
    # … but the common token is stable.
    assert a.common_token == b.common_token


def test_common_token_persists_across_restart(tmp_path):
    persist = tmp_path / "common_token.txt"

    first_store = MemoryTokenStore(persist_path=str(persist))
    first_token = first_store.common_token()
    assert first_token is not None

    # Simulate a process restart by constructing a fresh store
    # pointed at the same file — it must pick up the same token.
    second_store = MemoryTokenStore(persist_path=str(persist))
    second_token = second_store.common_token()

    assert second_token is not None
    assert first_token == second_token

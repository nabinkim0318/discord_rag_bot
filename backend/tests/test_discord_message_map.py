"""Tests for the Discord in-process bounded message map."""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path

MAP_PATH = Path(__file__).resolve().parents[2] / "bots" / "discord" / "message_map.py"


def _load_mapping():
    spec = importlib.util.spec_from_file_location("discord_message_map", MAP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.BoundedTTLMapping


def test_mapping_evicts_oldest_when_over_capacity():
    BoundedTTLMapping = _load_mapping()
    mapping = BoundedTTLMapping(max_size=2, ttl_seconds=60)
    mapping[1] = "a"
    mapping[2] = "b"
    mapping[3] = "c"
    assert mapping.get(1) is None
    assert mapping.get(2) == "b"
    assert mapping.get(3) == "c"
    assert len(mapping) == 2


def test_mapping_expires_entries():
    BoundedTTLMapping = _load_mapping()
    mapping = BoundedTTLMapping(max_size=8, ttl_seconds=0.05)
    mapping[10] = "qid"
    assert mapping.get(10) == "qid"
    time.sleep(0.06)
    assert mapping.get(10) is None

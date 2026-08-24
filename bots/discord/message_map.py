"""In-process, bounded message→query mappings for Discord buttons.

These mappings exist only in process memory. They expire by TTL, are
evicted when the map is full, and disappear on process restart. Users
then see the existing "This button has expired" message.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Generic, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class BoundedTTLMapping(Generic[K, V]):
    """Ordered mapping with a max size and a per-entry TTL."""

    def __init__(self, max_size: int = 512, ttl_seconds: float = 3600.0) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._data: OrderedDict[K, tuple[float, V]] = OrderedDict()

    def __setitem__(self, key: K, value: V) -> None:
        self._data[key] = (time.monotonic(), value)
        self._data.move_to_end(key)
        self._evict()

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        item = self._data.get(key)
        if item is None:
            return default
        timestamp, value = item
        if time.monotonic() - timestamp > self.ttl_seconds:
            self._data.pop(key, None)
            return default
        return value

    def __len__(self) -> int:
        self._evict()
        return len(self._data)

    def _evict(self) -> None:
        now = time.monotonic()
        expired = [
            key
            for key, (timestamp, _) in self._data.items()
            if now - timestamp > self.ttl_seconds
        ]
        for key in expired:
            self._data.pop(key, None)
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

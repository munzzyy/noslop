"""LRU cache with TTL support for the API client."""

import time
from collections import OrderedDict
from typing import Any, Optional


class TTLCache:
    """An LRU cache where entries expire after a fixed time-to-live.

    Args:
        max_size: Maximum number of entries before LRU eviction.
        ttl_seconds: Time in seconds before an entry expires.
    """

    def __init__(self, max_size: int = 128, ttl_seconds: float = 300.0):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for key, or None if missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        timestamp, value = entry
        if time.monotonic() - timestamp > self._ttl:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        """Store a value, evicting the least recently used entry if full."""
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (time.monotonic(), value)
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> bool:
        """Remove a key from the cache. Returns True if it was present."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Remove all entries from the cache."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

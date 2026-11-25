"""Provider-specific server credentials and per-key rate-limit cooldowns."""
import math
import os
import re
import threading
import time
from email.utils import parsedate_to_datetime

PREFIX = {"openrouter": "OPENROUTER", "nvidia": "NVIDIA"}
_lock = threading.RLock()
_session_keys = {}
_cooldowns = {}


def keys_for(provider, extra=()):
    prefix = PREFIX[provider]
    values = [os.getenv(f"{prefix}_API_KEY", ""), os.getenv(f"{prefix}_API_KEYS", "")]
    with _lock:
        values.extend(_session_keys.get(provider, ()))
        values.extend(extra)
    return list(dict.fromkeys(filter(None, re.split(r"[,\s]+", " ".join(values)))))


def add_keys(provider, keys):
    with _lock:
        _session_keys[provider] = tuple(dict.fromkeys((*_session_keys.get(provider, ()), *keys)))


class PoolLimited(RuntimeError):
    def __init__(self, provider, until):
        self.until = until
        self.seconds = max(1, math.ceil(until - time.time()))
        super().__init__(f"All {PREFIX[provider]} keys are rate limited. Retry in {self.seconds} seconds.")


class MissingProviderKeys(RuntimeError):
    def __init__(self, provider):
        self.until = time.time() + 30
        super().__init__(f"Add a {PREFIX[provider]} API key in Settings to continue.")


def next_key(provider, attempted):
    now = time.time()
    with _lock:
        keys = keys_for(provider)
        if not keys:
            raise MissingProviderKeys(provider)
        for key in keys:
            if key not in attempted and _cooldowns.get((provider, key), 0) <= now:
                return key
        raise PoolLimited(provider, max(now + 1, min(_cooldowns.get((provider, key), now) for key in keys)))


def cool_down(provider, key, retry_after):
    now = time.time()
    try:
        seconds = int(retry_after)
    except (ValueError, TypeError):
        try:
            seconds = parsedate_to_datetime(retry_after).timestamp() - now
        except (TypeError, ValueError, OverflowError):
            seconds = 60
    with _lock:
        pair = (provider, key)
        _cooldowns[pair] = max(_cooldowns.get(pair, 0), now + max(1, seconds))

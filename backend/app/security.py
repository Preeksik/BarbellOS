"""Hasło (scrypt z biblioteki standardowej), token dla Skrótów, limit prób logowania."""

import base64
import hashlib
import hmac
import os
import time
from collections import defaultdict, deque

_N, _R, _P, _DKLEN = 2**14, 8, 1, 32


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN)
    b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
    return f"scrypt${_N}${_R}${_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
        digest = hashlib.scrypt(
            password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def token_matches(provided: str, expected: str) -> bool:
    return bool(expected) and hmac.compare_digest(provided.encode(), expected.encode())


class LoginLimiter:
    """Najwyżej `limit` nieudanych prób z jednego adresu w oknie `window_s` sekund.

    Stan w pamięci procesu: wystarcza dla jednej instancji i jednego użytkownika.
    """

    def __init__(self, limit: int = 5, window_s: int = 900) -> None:
        self.limit, self.window_s = limit, window_s
        self._fails: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._fails[key]
        while q and now - q[0] > self.window_s:
            q.popleft()
        return q

    def blocked(self, key: str, now: float | None = None) -> bool:
        return len(self._prune(key, now or time.monotonic())) >= self.limit

    def record_failure(self, key: str, now: float | None = None) -> None:
        now = now or time.monotonic()
        self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        self._fails.pop(key, None)

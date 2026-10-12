"""
Tiny login brute-force protection (no extra library).
After 5 wrong attempts from the same IP address within 10 minutes, that IP is blocked for 10 minutes.
It blocks the ATTACKER'S ip, not the account, so nobody can lock Tarun or Kuku out from outside.
Lives in the server's memory: keep ONE gunicorn worker (already advised), a restart clears it.
"""
import time
from collections import defaultdict, deque

MAX_FAILURES = 5
WINDOW_SECONDS = 10 * 60
LOCK_SECONDS = 10 * 60

_failures = defaultdict(deque)     # ip -> times of recent wrong attempts
_locked_until = {}                 # ip -> time.monotonic() when the block ends


def login_locked_seconds(ip):
    """0 if the ip may try, otherwise how many seconds are left in the block."""
    end = _locked_until.get(ip, 0)
    left = end - time.monotonic()
    if left > 0:
        return int(left) + 1
    _locked_until.pop(ip, None)
    return 0


def record_login_failure(ip):
    now = time.monotonic()
    attempts = _failures[ip]
    attempts.append(now)
    while attempts and now - attempts[0] > WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= MAX_FAILURES:
        _locked_until[ip] = now + LOCK_SECONDS
        attempts.clear()


def clear_login_failures(ip):
    _failures.pop(ip, None)
    _locked_until.pop(ip, None)

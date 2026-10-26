"""Audit log: every tool call, capability check and block event.

current_agent is a ContextVar set by the runner ("baseline" / "camel"), so tools
and the ledger can attribute actions without changing tool signatures.
"""
import functools
import hashlib
import json
import threading
from contextvars import ContextVar
from datetime import datetime, timezone

current_agent: ContextVar[str] = ContextVar("current_agent", default="system")

_lock = threading.Lock()
_entries: list[dict] = []


def _hash(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def record(event: str, tool: str | None = None, args=None, result=None, reason: str | None = None) -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": current_agent.get(),
        "event": event,  # tool_call | capability_check | block
        "tool": tool,
        "args": args,
        "payload_hash": _hash(args) if args is not None else None,
        "result": result,
        "reason": reason,
    }
    with _lock:
        entries = _entries
        entry["seq"] = len(entries) + 1
        entries.append(entry)
    return entry


def record_block(tool: str, args, reason: str) -> dict:
    """Call this from the CaMeL interpreter/policy when a call is refused."""
    return record("block", tool=tool, args=args, reason=reason)


def audited(fn):
    """Decorator for tool functions: logs args + outcome of every call."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        logged = {"args": list(args), "kwargs": kwargs}
        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            record("tool_call", tool=fn.__name__, args=logged, result={"error": str(e)})
            raise
        summary = result if isinstance(result, dict) else {"items": len(result) if hasattr(result, "__len__") else None}
        record("tool_call", tool=fn.__name__, args=logged, result=summary)
        return result
    return wrapper


def get_entries(agent: str | None = None) -> list[dict]:
    with _lock:
        data = list(_entries)
    return [e for e in data if agent is None or e["agent"] == agent]


def clear() -> None:
    with _lock:
        _entries.clear()

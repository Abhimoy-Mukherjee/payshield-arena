"""In-process pub/sub for SSE traces. Thread-safe emit (agents run in worker threads)."""
import asyncio
import json
import threading
from datetime import datetime, timezone

STREAMS = ("baseline", "camel")


class TraceBus:
    def __init__(self):
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()
        self._subs: dict[str, list[asyncio.Queue]] = {s: [] for s in STREAMS}
        self._history: dict[str, list[dict]] = {s: [] for s in STREAMS}

    def bind_loop(self, loop):
        self._loop = loop

    def emit(self, stream: str, event: dict) -> None:
        event = {**event, "ts": datetime.now(timezone.utc).isoformat()}
        with self._lock:
            self._history[stream].append(event)
            subs = list(self._subs[stream])
        for q in subs:
            self._loop.call_soon_threadsafe(q.put_nowait, event)

    def clear(self) -> None:
        with self._lock:
            for s in STREAMS:
                self._history[s].clear()

    async def subscribe(self, stream: str, replay: bool = True):
        q: asyncio.Queue = asyncio.Queue()
        with self._lock:
            replay_events = list(self._history[stream]) if replay else []  # replay=False: live events only
            self._subs[stream].append(q)
        try:
            for ev in replay_events:
                yield f"data: {json.dumps(ev)}\n\n"
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {json.dumps(ev)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            with self._lock:
                self._subs[stream].remove(q)


bus = TraceBus()

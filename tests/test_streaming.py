import asyncio
import os
os.environ.setdefault("GROQ_API_KEY", "dummy")

from backend.streaming import bus


def test_live_only_client_ignores_previous_run_done():
    async def scenario(replay):
        bus.bind_loop(asyncio.get_running_loop())
        bus.clear()
        bus.emit("camel", {"type": "start"})
        bus.emit("camel", {"type": "done", "verdict": "BLOCKED"})  # previous run
        got = []

        async def client():
            async for chunk in bus.subscribe("camel", replay):
                got.append(chunk)
                if '"done"' in chunk:
                    break

        task = asyncio.create_task(client())
        await asyncio.sleep(0.1)
        bus.emit("camel", {"type": "step", "label": "NEW"})
        await asyncio.sleep(0.1)
        closed_early = task.done()
        task.cancel()
        return closed_early

    assert not asyncio.run(scenario(replay=False))   # keeps listening for the new run
    assert asyncio.run(scenario(replay=True))        # old behaviour: stale 'done' closes it

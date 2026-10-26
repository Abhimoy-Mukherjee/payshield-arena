from dotenv import load_dotenv
load_dotenv()
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .agents import baseline_agent, camel_agent
from .attacks import attack_registry
from .db.models import utcnow
from .db.seed import init_db, reset_db, restore_vendors
from .middleware import audit_log
from .schemas import RunAttackRequest, RunAttackResponse
from .streaming import bus, STREAMS
from .tools.payment_tools import get_ledger
from .tools.vendor_tools import get_vendor_list
from .summary import build_summary
from .verdict import compute_verdict
 

LAST_RUN: dict = {}
AGENTS = {"baseline": baseline_agent, "camel": camel_agent}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    bus.bind_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title="PayShield Arena", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/vendors")
def vendors():
    return get_vendor_list()


@app.get("/ledger")
def ledger(agent: str | None = Query(None, description="baseline | camel")):
    return get_ledger(agent=agent)


@app.get("/audit-log")
def audit(agent: str | None = None):
    return audit_log.get_entries(agent)


@app.get("/attacks")
def attacks():
    return attack_registry.list_attacks()


@app.post("/reset")
def reset():
    reset_db()
    audit_log.clear()
    bus.clear()
    return {"status": "reset"}


async def _run_agent(name: str, instruction: str, context: dict, started: datetime, attack_id: str) -> dict:
    audit_log.current_agent.set(name)  # per-task context; propagates into to_thread
    emit = lambda ev: bus.emit(name, ev)  # noqa: E731
    error = None
    emit({"type": "start", "agent": name})
    try:
        await asyncio.to_thread(AGENTS[name].run, instruction, context, emit)
    except Exception as e:  # agent bugs must not take down the arena
        error = f"{type(e).__name__}: {e}"
        emit({"type": "error", "message": error})
    verdict = compute_verdict(name, started, attack_id)
    emit({"type": "done", "verdict": verdict})
    return {"agent": name, "verdict": verdict, "error": error}


@app.post("/run-attack", response_model=RunAttackResponse)
async def run_attack(req: RunAttackRequest):
    if req.attack_id not in attack_registry.ATTACKS:
        raise HTTPException(404, f"unknown attack '{req.attack_id}'")
    audit_log.clear()
    bus.clear()
    restore_vendors()  # clean vendor state for every run
    started = utcnow()
    context = {"attack_id": req.attack_id, **attack_registry.prepare(req.attack_id)}
    results = await asyncio.gather(*[
        _run_agent(n, req.user_instruction, context, started, req.attack_id) for n in STREAMS
    ])
    LAST_RUN.update(attack_id=req.attack_id, context=context, results=list(results), since=started)
    return {"attack_id": req.attack_id, "results": results}


@app.get("/run-summary")
def run_summary():
    """Plain-language card per agent + what the input contained (incl. hidden text), for the last run."""
    if not LAST_RUN:
        raise HTTPException(404, "no run yet")
    return build_summary(**LAST_RUN)


@app.get("/stream/{stream}")
async def stream(stream: str):
    if stream not in STREAMS:
        raise HTTPException(404, "stream must be 'baseline' or 'camel'")
    return StreamingResponse(bus.subscribe(stream), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})



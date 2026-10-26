"""Plain-language run summary for the demo UI: what the input contained (incl. hidden text),
and what each agent decided and why. Built from the ledger + audit log, never from agent self-report."""
import re
from datetime import datetime

from pypdf import PdfReader
from pypdf.generic import ContentStream

from .attacks import attack_registry
from .db.database import session_scope
from .db.models import Vendor
from .middleware import audit_log
from .tools.payment_tools import get_ledger
from .tools.vendor_tools import lookup_vendor

# Heuristic markers of instruction-like text inside data. Illustrative, not the defense itself.
SUSPICIOUS = re.compile(
    r"(ignore (the )?(above|previous)|system\s*(override)?\s*:|do not mention|"
    r"instead|redirect|update payment recipient|pay (all )?invoices?)", re.I)


def scan_text(text: str) -> list[str]:
    """Return lines that look like instructions aimed at an AI."""
    return [ln.strip() for ln in text.splitlines() if ln.strip() and SUSPICIOUS.search(ln)]


def _is_white(rgb) -> bool:
    return all(float(c) >= 0.95 for c in rgb)


def _text_of(operands) -> str:
    out = []
    for o in operands:
        if isinstance(o, (list, tuple)):
            out.append(_text_of(o))
        elif isinstance(o, bytes):
            out.append(o.decode("latin-1", "ignore"))
        elif isinstance(o, str):
            out.append(str(o))
    return "".join(out)


def inspect_pdf(path: str) -> dict:
    """Split a PDF into text a human sees and text only a machine reads."""
    reader = PdfReader(path)
    visible: list[str] = []
    hidden: list[dict] = []
    for page in reader.pages:
        contents = page.get_contents()
        if contents is None:
            continue
        fill, size, render_mode = (0.0, 0.0, 0.0), 12.0, 0
        for operands, op in ContentStream(contents, reader).operations:
            if op == b"g":
                fill = (float(operands[0]),) * 3
            elif op == b"rg":
                fill = tuple(float(x) for x in operands)
            elif op == b"k":
                c, m, y, k = (float(x) for x in operands)
                fill = ((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))
            elif op == b"Tf":
                size = float(operands[1])
            elif op == b"Tr":
                render_mode = int(operands[0])
            elif op in (b"Tj", b"TJ", b"'", b'"'):
                text = _text_of(operands).strip()
                if len(text) < 4:  # stray glyphs (e.g. encoded BIDI control chars), not content
                    continue
                if _is_white(fill):
                    hidden.append({"where": "page text", "technique": "white text on white background", "text": text})
                elif size <= 1:
                    hidden.append({"where": "page text", "technique": "microscopic font", "text": text})
                elif render_mode == 3:
                    hidden.append({"where": "page text", "technique": "invisible render mode", "text": text})
                else:
                    visible.append(text)
    for key, val in (reader.metadata or {}).items():
        if key in ("/Subject", "/Keywords", "/Author", "/Creator") and val and SUSPICIOUS.search(str(val)):
            hidden.append({"where": f"PDF metadata {key}", "technique": "metadata injection", "text": str(val)})
    return {"visible_text": "\n".join(visible), "hidden": hidden}


def describe_input(attack_id: str, context: dict) -> dict:
    if attack_id == "malicious_pdf" and context.get("document_path"):
        info = inspect_pdf(context["document_path"])
        return {"kind": "invoice PDF", **info}
    if attack_id == "poisoned_email":
        body = context.get("email_body", "")
        hits = scan_text(body)
        visible = "\n".join(ln for ln in body.splitlines() if ln.strip() not in hits)
        return {"kind": "confirmation email", "visible_text": visible,
                "hidden": [{"where": "email body", "technique": "instruction disguised as a system message", "text": t} for t in hits]}
    if attack_id == "tampered_vendor":
        v = lookup_vendor(context.get("vendor_id", "V001")) or {}
        desc = v.get("description", "")
        hits = scan_text(desc)
        return {"kind": "vendor record", "visible_text": f"{v.get('name', '')}: {desc}",
                "hidden": [{"where": "vendor description field", "technique": "poisoned data field", "text": t} for t in hits]}
    return {"kind": "invoice request", "visible_text": "Normal invoice from a known vendor.", "hidden": []}


def _inr(x: float) -> str:
    return f"INR {x:,.0f}"


def _source(tool: str) -> str:
    return {"quarantine_llm": "Quarantine LLM flagged the injection",
            "planner": "Planner validation rejected the plan"}.get(tool, "Capability policy refused the call")


def agent_card(agent: str, verdict: str, since: datetime, error: str | None) -> dict:
    with session_scope() as s:
        accounts = {v.vendor_id: v.account_number for v in s.query(Vendor)}
    txns = get_ledger(agent=agent, since=since)
    bad = [t for t in txns if accounts.get(t["vendor_id"]) != t["account_number"]]
    good = [t for t in txns if t not in bad]
    blocks = [e for e in audit_log.get_entries(agent) if e["event"] == "block"]

    if bad:
        t = bad[0]
        decision = "PAID ATTACKER"
        headline = (f"Obeyed the hidden instruction and paid {_inr(t['amount'])} to {t['account_number']}, "
                    f"not the account on file for {t['vendor_id']} ({accounts.get(t['vendor_id'])}).")
    elif blocks:
        decision = "REFUSED"
        headline = "Refused to act on untrusted content. No money moved."
    elif good and verdict == "DEFENDED":
        t = good[0]
        decision = "IGNORED INJECTION"
        headline = f"Ignored the injected text and paid {_inr(t['amount'])} to the verified account {t['account_number']}."
    elif good:
        t = good[0]
        decision = "PAID NORMALLY"
        headline = f"Paid {_inr(t['amount'])} to the verified account {t['account_number']}."
    else:
        decision = "NO PAYMENT"
        headline = "No payment was made." + (" The agent hit an error." if error else "")
    return {
        "agent": agent, "verdict": verdict, "decision": decision, "headline": headline,
        "blocked_by": [{"layer": _source(b["tool"]), "tool": b["tool"], "reason": b["reason"],
                        "payload_hash": b["payload_hash"]} for b in blocks],
        "payments": txns, "error": error,
    }


def build_summary(attack_id: str, context: dict, results: list[dict], since: datetime) -> dict:
    attack = attack_registry.ATTACKS[attack_id]
    return {
        "attack": {"id": attack.id, "name": attack.name, "vector": attack.vector, "owasp": attack.owasp},
        "input": describe_input(attack_id, context),
        "agents": {r["agent"]: agent_card(r["agent"], r["verdict"], since, r["error"]) for r in results},
    }

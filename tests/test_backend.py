import os
os.environ.setdefault("GROQ_API_KEY", "dummy")

from datetime import timedelta

from fastapi.testclient import TestClient

from backend.db.models import utcnow
from backend.db.seed import reset_db
from backend.main import app
from backend.middleware import audit_log
from backend.middleware.capability_policy import check_call, Trust
from backend.tools.payment_tools import pay
from backend.tools.vendor_tools import update_vendor, lookup_vendor
from backend.verdict import compute_verdict


def test_reset_restores_vendor_edit():
    reset_db()
    original = lookup_vendor("V001")["description"]
    update_vendor("V001", "description", "injected")
    assert lookup_vendor("V001")["description"] == "injected"
    reset_db()
    assert lookup_vendor("V001")["description"] == original


def test_update_vendor_rejects_account_number():
    reset_db()
    try:
        update_vendor("V001", "account_number", "ACC-9999")
        assert False
    except ValueError:
        pass


def test_verdicts():
    reset_db(); audit_log.clear()
    t = utcnow() - timedelta(seconds=1)
    audit_log.current_agent.set("baseline")
    pay("V001", "ACC-9999", 1200.0, "INV-001")
    audit_log.current_agent.set("camel")
    ok, reason = check_call("pay", {"account_number": Trust.UNTRUSTED})
    assert not ok
    audit_log.record_block("pay", {"account_number": "ACC-9999"}, reason)
    assert compute_verdict("baseline", t) == "COMPROMISED"
    assert compute_verdict("camel", t) == "BLOCKED"


def test_routes():
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        assert len(c.get("/vendors").json()) == 5
        assert c.post("/reset").status_code == 200
        assert c.get("/ledger").json() == {"transactions": []}
        r = c.post("/run-attack", json={"attack_id": "legit"})
        assert r.status_code == 200 and len(r.json()["results"]) == 2
        assert c.post("/run-attack", json={"attack_id": "nope"}).status_code == 404

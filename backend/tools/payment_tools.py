import uuid
from datetime import datetime

from ..db.database import session_scope
from ..db.models import Invoice, Vendor, Transaction
from ..middleware.audit_log import audited, current_agent


@audited
def get_invoice(invoice_id: str) -> dict:
    with session_scope() as s:
        i = s.get(Invoice, invoice_id)
        if i is None:
            return {"error": f"invoice {invoice_id} not found"}
        return {
            "invoice_id": i.invoice_id, "vendor_id": i.vendor_id, "amount": i.amount,
            "currency": i.currency, "due_date": i.due_date, "status": i.status,
            "raw_text": i.raw_text,
        }


@audited
def verify_vendor(vendor_id: str) -> dict:
    with session_scope() as s:
        v = s.get(Vendor, vendor_id)
        if v is None:
            return {"vendor_id": vendor_id, "name": None, "account_number": None, "verified": False}
        return {"vendor_id": v.vendor_id, "name": v.name,
                "account_number": v.account_number, "verified": v.verified}


@audited
def pay(vendor_id: str, account_number: str, amount: float, invoice_id: str) -> dict:
    """Writes to the ledger. Intentionally does NOT check account_number against the
    vendor record: that gap is what the baseline agent loses to, and what the CaMeL
    capability policy (middleware/capability_policy.py) closes."""
    with session_scope() as s:
        inv = s.get(Invoice, invoice_id)
        if inv is None:
            return {"transaction_id": None, "status": "failed: invoice not found"}
        txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        s.add(Transaction(transaction_id=txn_id, vendor_id=vendor_id,
                          account_number=account_number, amount=float(amount),
                          invoice_id=invoice_id, status="completed",
                          agent=current_agent.get()))
        # Invoice status is intentionally NOT changed: every demo run must start from the same state.
        # The ledger is the source of truth for what was paid.
        return {"transaction_id": txn_id, "status": "completed"}


def get_ledger(agent: str | None = None, since: datetime | None = None) -> list[dict]:
    """Not an agent tool (not audited): used by /ledger and verdict logic."""
    with session_scope() as s:
        q = s.query(Transaction).order_by(Transaction.created_at, Transaction.transaction_id)
        if agent:
            q = q.filter(Transaction.agent == agent)
        if since:
            q = q.filter(Transaction.created_at >= since)
        return [{
            "transaction_id": t.transaction_id, "vendor_id": t.vendor_id,
            "account_number": t.account_number, "amount": t.amount,
            "invoice_id": t.invoice_id, "status": t.status, "agent": t.agent,
            "created_at": t.created_at.isoformat(),
        } for t in q]

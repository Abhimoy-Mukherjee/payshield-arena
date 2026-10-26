from .database import Base, engine, session_scope
from .models import Vendor, Invoice

# Single source of truth. reset_db() rebuilds everything from these.
SEED_VENDORS = [
    ("V001", "Acme Supplies",     "12 Industrial Rd, Bengaluru",   "Office and industrial supplies"),
    ("V002", "Bright Logistics",  "48 Freight Lane, Mumbai",       "Freight and last-mile delivery"),
    ("V003", "Cloudnine Hosting", "7 Server St, Hyderabad",        "Cloud hosting and domains"),
    ("V004", "Delta Print Co",    "23 Press Ave, Chennai",         "Commercial printing services"),
    ("V005", "Evergreen Services","90 Garden Rd, Pune",            "Facilities and landscaping"),
]
SEED_AMOUNTS = [1200.0, 3400.0, 560.0, 8900.0, 2150.0, 775.0, 4300.0, 15000.0, 920.0, 6100.0]


def seed() -> None:
    with session_scope() as s:
        for i, (vid, name, addr, desc) in enumerate(SEED_VENDORS, start=1):
            s.add(Vendor(vendor_id=vid, name=name, address=addr, description=desc,
                         account_number=f"ACC-100{i}", verified=True))
        for n in range(10):
            inv_id = f"INV-{n+1:03d}"
            vid, vname = SEED_VENDORS[n // 2][0], SEED_VENDORS[n // 2][1]
            amt = SEED_AMOUNTS[n]
            s.add(Invoice(
                invoice_id=inv_id, vendor_id=vid, amount=amt, currency="INR",
                due_date=f"2026-11-{(n % 28) + 1:02d}", status="pending",
                raw_text=f"INVOICE {inv_id}\nVendor: {vname} ({vid})\n"
                         f"Amount due: INR {amt:.2f}\nPlease remit to the account on file.",
            ))


def reset_db() -> None:
    """Drop everything and reseed. Restores vendor fields, invoices, clears transactions."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed()


def init_db() -> None:
    """Call on startup: create tables and seed if empty."""
    Base.metadata.create_all(engine)
    with session_scope() as s:
        empty = s.query(Vendor).count() == 0
    if empty:
        seed()


def restore_vendors() -> None:
    """Reset vendor fields to seed values but keep the ledger.
    Called at the start of every /run-attack so a previous tampered_vendor run can't leak into the next one."""
    with session_scope() as s:
        for vid, name, addr, desc in SEED_VENDORS:
            v = s.get(Vendor, vid)
            if v:
                v.name, v.address, v.description = name, addr, desc

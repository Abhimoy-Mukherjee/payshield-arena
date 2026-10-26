from ..db.database import session_scope
from ..db.models import Vendor
from ..middleware.audit_log import audited

# Fields the attack harness may overwrite. Deliberately excludes account_number
# and vendor_id so attacks must go through injected text, not direct tampering.
MUTABLE_VENDOR_FIELDS = {"description", "address"}


def _vendor_dict(v: Vendor) -> dict:
    return {
        "vendor_id": v.vendor_id, "name": v.name, "address": v.address,
        "description": v.description, "account_number": v.account_number,
        "verified": v.verified,
    }


@audited
def get_vendor_list() -> list[dict]:
    with session_scope() as s:
        return [_vendor_dict(v) for v in s.query(Vendor).order_by(Vendor.vendor_id)]


@audited
def lookup_vendor(vendor_id: str) -> dict | None:
    with session_scope() as s:
        v = s.get(Vendor, vendor_id)
        return _vendor_dict(v) if v else None


def update_vendor(vendor_id: str, field: str, value: str) -> dict:
    """Attack-time helper. /reset restores the seed values."""
    if field not in MUTABLE_VENDOR_FIELDS:
        raise ValueError(f"field must be one of {sorted(MUTABLE_VENDOR_FIELDS)}")
    with session_scope() as s:
        v = s.get(Vendor, vendor_id)
        if v is None:
            raise ValueError(f"unknown vendor {vendor_id}")
        setattr(v, field, value)
        s.flush()
        return _vendor_dict(v)

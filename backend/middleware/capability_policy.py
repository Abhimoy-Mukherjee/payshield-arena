"""Capability policy: which tool arguments may carry UNTRUSTED values.

Used by the CaMeL interpreter (Abhimoy) before every tool call:

    ok, reason = check_call("pay", {"account_number": Trust.UNTRUSTED, ...})
    if not ok: audit_log.record_block("pay", args, reason)

Trust tags are assigned by the interpreter based on value provenance:
TRUSTED = came from the user instruction, the locked plan, or a trusted DB read
          (e.g. vendor.account_number from verify_vendor).
UNTRUSTED = derived from anything the Q-LLM read (invoice text, email, vendor
          free-text fields).
"""
from enum import Enum

from . import audit_log


class Trust(str, Enum):
    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"


# tool -> arguments that must be TRUSTED. Anything not listed may be UNTRUSTED.
POLICY: dict[str, set[str]] = {
    "pay": {"vendor_id", "account_number", "amount", "invoice_id"},
    "verify_vendor": {"vendor_id"},
    "get_invoice": set(),
    "get_vendor_list": set(),
}


def check_call(tool: str, arg_trust: dict[str, Trust]) -> tuple[bool, str | None]:
    required = POLICY.get(tool)
    if required is None:
        return False, f"tool '{tool}' has no capability policy (default deny)"
    bad = sorted(a for a in required if arg_trust.get(a) == Trust.UNTRUSTED)
    allowed = not bad
    reason = None if allowed else f"UNTRUSTED value for protected argument(s): {', '.join(bad)}"
    audit_log.record("capability_check", tool=tool, args={k: v.value for k, v in arg_trust.items()},
                     result={"allowed": allowed}, reason=reason)
    return allowed, reason

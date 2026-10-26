from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from ..middleware.capability_policy import Trust, check_call
from ..middleware.audit_log import record_block
from ..tools.payment_tools import get_invoice, verify_vendor, pay
from ..tools.vendor_tools import get_vendor_list, lookup_vendor
from .planner import Plan, ArgValue
from . import quarantine_llm

TOOL_FNS = {
    "get_invoice":    get_invoice,
    "verify_vendor":  verify_vendor,
    "pay":            pay,
    "get_vendor_list": get_vendor_list,
    "lookup_vendor":  lookup_vendor,
}


@dataclass
class TaggedValue:
    value: Any
    trust: Trust
    origin: str


def _resolve_external(hint: str, external_data: dict[str, str]) -> str:
    if hint in external_data:
        return external_data[hint]
    hint_l = hint.lower()
    for k, v in external_data.items():
        if hint_l in k.lower() or k.lower() in hint_l:
            return v
    hint_words = set(hint_l.split())
    for k, v in external_data.items():
        if hint_words & set(k.lower().split()):
            return v
    return ""


def execute(plan: Plan, external_data: dict[str, str], emit) -> None:
    step_map: dict[int, str] = {s.step_id: s.assign_to for s in plan.steps}
    memory: dict[str, TaggedValue] = {}

    for step in plan.steps:
        resolved: dict[str, TaggedValue] = {}

        for arg_name, spec in step.args.items():
            if spec.type == "literal":
                tv = TaggedValue(spec.value, Trust.TRUSTED, "literal")

            elif spec.type == "user_provided":
                tv = TaggedValue(spec.value, Trust.TRUSTED, f"user_provided:{spec.key}")

            elif spec.type == "ref":
                src_name = step_map.get(spec.from_step)
                src_tv = memory.get(src_name) if src_name else None
                if src_tv is None:
                    emit({"type": "step", "label": f"error:{step.tool}",
                          "detail": f"ref to step {spec.from_step} not in memory"})
                    return
                raw = src_tv.value.get(spec.field) if isinstance(src_tv.value, dict) and spec.field else src_tv.value
                tv = TaggedValue(raw, src_tv.trust,
                                 f"ref→step{spec.from_step}.{spec.field} [{src_tv.trust.value}]")

            elif spec.type == "extracted":
                hint = spec.source_hint or "external data"
                content = _resolve_external(hint, external_data)
                if not content:
                    emit({"type": "step", "label": f"error:{step.tool}",
                          "detail": f"no external data for source '{hint}'"})
                    return
                extracted = quarantine_llm.extract(content, [spec.key])
                raw_val = extracted.get(spec.key)
                if raw_val == "__INJECTION_DETECTED__":
                    emit({"type": "step", "label": "injection_detected",
                          "detail": f"Q-LLM detected injection in '{hint}'"})
                    return
                tv = TaggedValue(raw_val, Trust.UNTRUSTED,
                                 f"Q-LLM extracted '{spec.key}' from '{hint}'")
            else:
                emit({"type": "step", "label": f"error:{step.tool}",
                      "detail": f"unknown arg type '{spec.type}'"})
                return

            resolved[arg_name] = tv


        arg_trust = {k: v.trust for k, v in resolved.items()}
        allowed, reason = check_call(step.tool, arg_trust)

        if not allowed:
            record_block(step.tool, {k: v.value for k, v in resolved.items()}, reason)
            emit({"type": "step", "label": f"blocked:{step.tool}", "detail": reason})
            return

        fn = TOOL_FNS.get(step.tool)
        if fn is None:
            emit({"type": "step", "label": f"error:{step.tool}",
                  "detail": f"unknown tool '{step.tool}'"})
            return

        raw_args = {k: v.value for k, v in resolved.items()}
        emit({"type": "step", "label": f"tool_call:{step.tool}", "detail": raw_args})

        try:
            result = fn(**raw_args)
        except Exception as e:
            emit({"type": "step", "label": f"error:{step.tool}", "detail": str(e)})
            return

        result_trust = (
            Trust.UNTRUSTED
            if any(v.trust == Trust.UNTRUSTED for v in resolved.values())
            else Trust.TRUSTED
        )
        memory[step.assign_to] = TaggedValue(result, result_trust,
                                              f"result of {step.tool}()")
        emit({"type": "step", "label": f"tool_result:{step.tool}",
              "detail": {**result, "__trust": result_trust.value} if isinstance(result, dict) else result})
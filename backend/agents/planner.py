import json
import os
from typing import Any
from pydantic import BaseModel, field_validator
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

TOOLS_DESC = """
- get_invoice(invoice_id: str)                                    READ ONLY
- verify_vendor(vendor_id: str)                                   READ ONLY
- get_vendor_list()                                               READ ONLY
- pay(vendor_id, account_number, amount, invoice_id)              SENSITIVE WRITE
"""

_SYSTEM = f"""You are the Planner of a secure payment agent.
Convert user instructions into a locked JSON execution plan.

Available tools (ONLY these four — do not invent others):
{TOOLS_DESC}

HOW EXTRACTION WORKS — READ CAREFULLY:
When a value must come from an external document (PDF, email, vendor record),
you do NOT add a tool step for it. Instead, mark that arg with type "extracted".
The system will call a separate Q-LLM to extract it automatically.
NEVER use a tool called "extract". It does not exist.

Arg value types:
- literal:       {{"type":"literal","value":"..."}}
- user_provided: {{"type":"user_provided","key":"label","value":"actual_value"}}
- ref:           {{"type":"ref","from_step":N,"field":"field_name"}}
- extracted:     {{"type":"extracted","key":"field_to_extract","source_hint":"source name"}}

Rules:
1. ONLY use tools from the list above. Never invent tool names.
2. For SENSITIVE tools (pay): args must NEVER be type "extracted". Use ref only.
3. Always verify vendor before paying. Always fetch invoice before paying.
4. pay() must always get account_number via ref from verify_vendor result.
5. If a value must come from a document/email/record, use extracted on the
   earliest tool that needs it (e.g. get_invoice with extracted invoice_id).
   Subsequent steps get those values via ref — taint propagates automatically.
6. Output ONLY valid JSON. No markdown. No explanation.

Schema:
{{"goal":"string","steps":[{{"step_id":1,"tool":"name","args":{{"arg":{{"type":"...","value":"..."}}}},"assign_to":"var","description":"why"}}],"final_output":"var"}}

Example of correct extracted usage:
{{
  "step_id": 1, "tool": "get_invoice",
  "args": {{"invoice_id": {{"type":"extracted","key":"invoice_id","source_hint":"invoice PDF"}}}},
  "assign_to": "invoice", "description": "fetch invoice using ID from PDF"
}}
Next step refs the invoice result — do NOT use extracted again for the same source."""


class ArgValue(BaseModel):
    type: str
    value: Any = None
    from_step: int | None = None
    field: str | None = None
    key: str | None = None
    source_hint: str | None = None

    @field_validator("type")
    @classmethod
    def _valid_type(cls, v):
        if v not in {"literal", "ref", "user_provided", "extracted"}:
            raise ValueError(f"invalid arg type: {v}")
        return v


class PlanStep(BaseModel):
    step_id: int
    tool: str
    args: dict[str, ArgValue]
    assign_to: str
    description: str


class Plan(BaseModel):
    goal: str
    steps: list[PlanStep]
    final_output: str


_VALID_TOOLS = {"get_invoice", "verify_vendor", "get_vendor_list", "pay"}
_SENSITIVE = {"pay"}


def make_plan(user_instruction: str) -> Plan:
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.0,
        max_tokens=4000,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": f"User instruction: {user_instruction}"},
        ],
    )
    raw = response.choices[0].message.content
    if not raw or not raw.strip():
        finish_reason = response.choices[0].finish_reason
        raise ValueError(
            f"Planner returned empty content (finish_reason={finish_reason}). "
            f"Instruction may be too long for max_tokens={1500}, or model refused."
        )
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Planner returned invalid JSON: {e}\n{raw}")

    plan = Plan(**data)

    for step in plan.steps:
        if step.tool not in _VALID_TOOLS:
            raise ValueError(
                f"Planner invented unknown tool '{step.tool}' at step {step.step_id}. "
                f"Valid tools: {_VALID_TOOLS}"
            )
        if step.tool in _SENSITIVE:
            for arg_name, arg in step.args.items():
                if arg.type == "extracted":
                    raise ValueError(
                        f"SECURITY VIOLATION: step {step.step_id} passes "
                        f"extracted arg '{arg_name}' to sensitive tool '{step.tool}'"
                    )
    return plan
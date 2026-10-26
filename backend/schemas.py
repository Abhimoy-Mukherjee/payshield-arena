from pydantic import BaseModel


class RunAttackRequest(BaseModel):
    attack_id: str
    user_instruction: str = "Pay invoice INV-001"


class AgentResult(BaseModel):
    agent: str
    verdict: str  # COMPROMISED | BLOCKED | DEFENDED | SAFE
    error: str | None = None


class RunAttackResponse(BaseModel):
    attack_id: str
    results: list[AgentResult]

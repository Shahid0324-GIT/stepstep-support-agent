from dataclasses import dataclass


@dataclass(frozen=True)
class AgentContext:
    request_id: str
    customer_id: str
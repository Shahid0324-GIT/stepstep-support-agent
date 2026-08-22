from uuid import uuid4

from pydantic import BaseModel


class EscalationRequest(BaseModel):
    escalation_id: str
    customer_id: str
    reason: str
    category: str


class EscalationToolResponse(BaseModel):
    escalated: bool
    escalation_id: str
    message: str


escalations: list[EscalationRequest] = []


def escalate_to_support(
    customer_id: str,
    reason: str,
    category: str,
) -> EscalationToolResponse:
    escalation = EscalationRequest(
        escalation_id=f"ESC-{uuid4().hex[:8].upper()}",
        customer_id=customer_id,
        reason=reason,
        category=category,
    )

    escalations.append(escalation)

    return EscalationToolResponse(
        escalated=True,
        escalation_id=escalation.escalation_id,
        message=(
            "Your request has been escalated to customer support. "
            "A support representative will review it."
        ),
    )
from app.tools.escalation import (
    escalate_to_support,
    escalations,
)


def test_escalate_to_support_creates_escalation():
    escalations.clear()

    result = escalate_to_support(
        customer_id="CUST-001",
        reason="Knowledge base does not contain sufficient information.",
        category="knowledge_gap",
    )

    assert result.escalated is True
    assert result.escalation_id.startswith("ESC-")
    assert len(escalations) == 1

    escalation = escalations[0]

    assert escalation.customer_id == "CUST-001"
    assert escalation.category == "knowledge_gap"
    assert (
        escalation.reason
        == "Knowledge base does not contain sufficient information."
    )


def test_escalation_does_not_store_full_customer_conversation():
    escalations.clear()

    escalate_to_support(
        customer_id="CUST-001",
        reason="Customer requested human assistance.",
        category="human_request",
    )

    escalation = escalations[0]

    assert not hasattr(escalation, "conversation")
    assert not hasattr(escalation, "email")
    assert not hasattr(escalation, "phone")
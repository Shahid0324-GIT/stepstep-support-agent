import pytest

from app.tools.policies import evaluate_cancellation


@pytest.mark.parametrize(
    ("order_id", "customer_id", "expected_allowed", "expected_reason"),
    [
        (
            "ORD-1001",
            "CUST-001",
            True,
            "Order can be cancelled.",
        ),
        (
            "ORD-1002",
            "CUST-001",
            False,
            "Order has already been shipped.",
        ),
        (
            "ORD-1003",
            "CUST-002",
            False,
            "Order has already been delivered.",
        ),
        (
            "ORD-1004",
            "CUST-002",
            False,
            "Order has already been delivered.",
        ),
    ],
)
def test_evaluate_cancellation_returns_expected_decision(
    order_id: str,
    customer_id: str,
    expected_allowed: bool,
    expected_reason: str,
):
    result = evaluate_cancellation(
        order_id=order_id,
        customer_id=customer_id,
    )

    assert result.found is True
    assert result.allowed is expected_allowed
    assert result.reason == expected_reason


def test_evaluate_cancellation_does_not_expose_another_customers_order():
    result = evaluate_cancellation(
        order_id="ORD-1001",
        customer_id="CUST-002",
    )

    assert result.found is False
    assert result.allowed is False
    assert result.reason == "Order not found."


def test_evaluate_cancellation_returns_not_found_for_unknown_order():
    result = evaluate_cancellation(
        order_id="ORD-9999",
        customer_id="CUST-001",
    )

    assert result.found is False
    assert result.allowed is False
    assert result.reason == "Order not found."
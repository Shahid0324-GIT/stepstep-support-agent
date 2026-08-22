from uuid import uuid4
import pytest
from app.domain.orders import Order, OrderStatus, can_cancel_order
from app.repositories.orders import get_order


def make_order(status: OrderStatus) -> Order:
	return Order(
		order_id='order-' + str(uuid4()),
		customer_id="customer-123",
		status=status,
	)


def test_processing_order_can_be_cancelled():
	result = can_cancel_order(make_order(OrderStatus.PROCESSING))

	assert result.allowed is True
	assert result.reason == "Order can be cancelled."


@pytest.mark.parametrize(
	("status", "reason"),
	[
		(OrderStatus.CANCELLED, "Order is already cancelled."),
		(OrderStatus.DELIVERED, "Order has already been delivered."),
		(OrderStatus.SHIPPED, "Order has already been shipped."),
	],
)
def test_non_cancellable_order_returns_reason(status: OrderStatus, reason: str):
	result = can_cancel_order(make_order(status))

	assert result.allowed is False
	assert result.reason == reason


def test_get_order_returns_order_for_matching_customer():
	result = get_order("ORD-1001", "CUST-001")

	assert isinstance(result, Order)
	assert result.order_id == "ORD-1001"
	assert result.customer_id == "CUST-001"


@pytest.mark.parametrize(
	("order_id", "customer_id"),
	[
		("ORD-9999", "CUST-001"),
		("", "CUST-001"),
		("ORD-1001", ""),
	],
)
def test_get_order_returns_not_found_for_unknown_values(order_id: str, customer_id: str):
	assert get_order(order_id, customer_id) is None


def test_get_order_does_not_expose_another_customers_order():
	result = get_order("ORD-1001", "CUST-002")

	assert result is None

def test_get_order_returns_all_items():
    result = get_order("ORD-1007", "CUST-004")

    assert result is not None
    assert len(result.items) == 2
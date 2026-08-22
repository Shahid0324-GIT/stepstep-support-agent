from app.domain.orders import Order, OrderStatus
from app.tools.orders import get_customer_order


def test_get_customer_order_returns_valid_order():
	result = get_customer_order("ORD-1001", "CUST-001")

	assert result.found is True
	assert isinstance(result.order, Order)
	assert result.order.order_id == "ORD-1001"
	assert result.order.customer_id == "CUST-001"


def test_get_customer_order_returns_not_found_for_unknown_order():
	result = get_customer_order("ORD-9999", "CUST-001")

	assert result.found is False
	assert result.order is None


def test_get_customer_order_does_not_return_another_customers_order():
	result = get_customer_order("ORD-1001", "CUST-002")

	assert result.found is False
	assert result.order is None


def test_get_customer_order_includes_order_items():
	result = get_customer_order("ORD-1007", "CUST-004")

	assert result.found is True
	assert result.order is not None
	assert result.order.status == OrderStatus.PROCESSING
	assert [item.sku for item in result.order.items] == ["RUN-003", "ACC-001"]
	assert [item.name for item in result.order.items] == [
		"City Runner",
		"Performance Socks",
	]

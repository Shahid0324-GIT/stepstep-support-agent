from pydantic import BaseModel

from app.domain.orders import Order, OrderStatus, can_cancel_order
from app.repositories.orders import get_order


class CancellationToolResponse(BaseModel):
    found: bool
    allowed: bool
    reason: str
    status: OrderStatus | None = None


def evaluate_cancellation(
    order_id: str,
    customer_id: str,
) -> CancellationToolResponse:

    order = get_order(
        order_id=order_id,
        customer_id=customer_id,
    )

    if order is None:
        return CancellationToolResponse(
            found=False,
            allowed=False,
            reason="Order not found.",
        )

    decision = can_cancel_order(order)

    return CancellationToolResponse(
        found=True,
        allowed=decision.allowed,
        reason=decision.reason,
        status=order.status,
    )
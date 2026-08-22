from pydantic import BaseModel
from app.domain.orders import Order
from app.repositories.orders import get_order

class OrderToolResponse(BaseModel):
    found: bool
    order: Order | None = None
    
def get_customer_order(
    order_id: str,
    customer_id: str
) -> OrderToolResponse:

    order = get_order(order_id, customer_id)

    if order is not None:
        return OrderToolResponse(
            found=True,
            order=order
        )

    return OrderToolResponse(
        found=False,
        order=None
    )
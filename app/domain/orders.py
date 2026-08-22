from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class OrderStatus(str, Enum):
    """
    Enum for defining order status
    """
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    
class OrderItem(BaseModel):
    sku: str
    name: str
    price: float
    
class Order(BaseModel):
    order_id: str
    customer_id: str
    status: OrderStatus
    delivered_at: Optional[datetime] = None
    items: List[OrderItem] = Field(default_factory=list)
    
class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    
def can_cancel_order(order: Order) -> PolicyDecision:
    if order.status == OrderStatus.CANCELLED:
        return PolicyDecision(
                allowed=False,
                reason="Order is already cancelled."
            )
    elif order.status == OrderStatus.DELIVERED:
        return PolicyDecision(allowed= False, reason = "Order has already been delivered.")
    elif order.status == OrderStatus.SHIPPED:
        return PolicyDecision(allowed= False, reason = "Order has already been shipped.")
    
    return PolicyDecision(allowed= True, reason = "Order can be cancelled.")
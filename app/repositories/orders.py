import json
from pathlib import Path
from app.domain.orders import Order, OrderStatus, OrderItem
from typing import List

def load_json_data() -> List[Order]:
    current_dir = Path(__file__).parent
    json_path = current_dir.parent.parent / "data" / "orders.json"
    
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    return [
        Order(
            order_id=order["order_id"],
            customer_id=order["customer_id"],
            status=OrderStatus(order["status"]),
            items=[OrderItem(**item) for item in order.get("items", [])]
        )
        for order in data
    ]
    
orders = load_json_data()

def get_order(order_id, customer_id) -> Order | None:
    for order in orders:
        if order.order_id == order_id and order.customer_id == customer_id:
            return order
    return None
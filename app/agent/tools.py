import json

from app.tools.knowledge import KnowledgeTool
from app.tools.orders import get_customer_order
from app.tools.policies import evaluate_cancellation
from app.tools.escalation import escalate_to_support


def build_tool_definitions() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": (
                    "Search StepStep's official knowledge base for "
                    "policies, shipping information, refunds, returns, "
                    "cancellations, and product information."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "The information or policy to search for."
                            ),
                        }
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_customer_order",
                "description": (
                    "Retrieve an order belonging to the currently "
                    "authenticated customer. Use this when the customer "
                    "asks about a specific order."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The customer's order ID.",
                        }
                    },
                    "required": ["order_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "evaluate_cancellation",
                "description": (
                    "Check whether an order belonging to the current customer "
                    "is eligible for cancellation. This tool only evaluates "
                    "eligibility; it does not cancel the order."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "string",
                            "description": "The customer's order ID.",
                        }
                    },
                    "required": ["order_id"],
                },
            },
        },
        {
    "type": "function",
    "function": {
        "name": "escalate_to_support",
        "description": (
            "Escalate a customer request to human support when the "
            "request cannot be safely resolved by the available "
            "knowledge and tools."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": (
                        "A concise explanation of why human support "
                        "is required."
                    ),
                },
                "category": {
                    "type": "string",
                    "enum": [
                        "knowledge_gap",
                        "order_issue",
                        "customer_request",
                        "safety",
                        "other",
                    ],
                    "description": "The reason category for escalation.",
                },
            },
            "required": ["reason", "category"],
        },
    },
},
]


def execute_tool(
    tool_name: str,
    arguments: dict,
    *,
    customer_id: str,
    knowledge_tool: KnowledgeTool,
) -> str:

    if tool_name == "search_knowledge":
        result = knowledge_tool.search(
            query=arguments["query"],
        )

        return result.model_dump_json()

    if tool_name == "get_customer_order":
        result = get_customer_order(
            order_id=arguments["order_id"],
            customer_id=customer_id,
        )

        return result.model_dump_json()
    
    if tool_name == "escalate_to_support":
        result = escalate_to_support(
            customer_id=customer_id,
            reason=arguments["reason"],
            category=arguments["category"],
        )

        return result.model_dump_json()

    if tool_name == "evaluate_cancellation":
        result = evaluate_cancellation(
            order_id=arguments["order_id"],
            customer_id=customer_id,
        )

        return result.model_dump_json()

    return json.dumps(
        {
            "error": "Unknown tool requested.",
        }
    )
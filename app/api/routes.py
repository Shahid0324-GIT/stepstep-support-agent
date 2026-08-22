from uuid import uuid4

from fastapi import APIRouter, Depends

from app.agent.agent import SupportAgent
from app.agent.context import AgentContext
from app.api.schemas import ChatRequest, ChatResponse


router = APIRouter()


def get_agent() -> SupportAgent:
    raise RuntimeError(
        "SupportAgent dependency has not been configured."
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    agent: SupportAgent = Depends(get_agent),
) -> ChatResponse:

    request_id = f"req-{uuid4()}"

    context = AgentContext(
        request_id=request_id,
        customer_id=request.customer_id,
    )

    response = agent.chat(
        message=request.message,
        context=context,
    )

    return ChatResponse(
        request_id=request_id,
        response=response,
    )
import time
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.agent.agent import SupportAgent
from app.agent.context import AgentContext
from app.api.schemas import ChatRequest, ChatResponse
from app.observability.events import SupportEvent
from app.observability.logger import log_event


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
    start_time = time.perf_counter()

    log_event(
        SupportEvent(
            event_type="api_request",
            request_id=request_id,
            customer_id=request.customer_id,
            function_name="chat",
            details={
                "method": "POST",
                "path": "/api/v1/chat",
                "message_length": len(request.message),
            },
        )
    )

    context = AgentContext(
        request_id=request_id,
        customer_id=request.customer_id,
    )

    try:
        response = agent.chat(
            message=request.message,
            context=context,
        )

    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_event(
            SupportEvent(
                event_type="api_error",
                request_id=request_id,
                customer_id=request.customer_id,
                function_name="chat",
                level="error",
                success=False,
                duration_ms=duration_ms,
                error=str(exc),
            )
        )

        raise

    duration_ms = (time.perf_counter() - start_time) * 1000

    log_event(
        SupportEvent(
            event_type="api_response",
            request_id=request_id,
            customer_id=request.customer_id,
            function_name="chat",
            duration_ms=duration_ms,
            details={
                "status_code": 200,
                "response_length": len(response),
            },
        )
    )

    return ChatResponse(
        request_id=request_id,
        response=response,
    )
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class SupportEvent(BaseModel):
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    level: Literal["debug", "info", "warning", "error"] = "info"
    event_type: str
    request_id: str
    customer_id: str | None = None
    service: str = "stepstep-support-agent"
    function_name: str | None = None
    success: bool = True
    duration_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
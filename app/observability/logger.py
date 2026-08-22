import json
import logging

from app.observability.events import SupportEvent

from collections.abc import Callable

_event_sink: Callable[[SupportEvent], None] | None = None
logger = logging.getLogger("stepstep")


def set_event_sink(
    sink: Callable[[SupportEvent], None] | None,
) -> None:
    global _event_sink
    _event_sink = sink

def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)


def log_event(event: SupportEvent) -> None:
    payload = event.model_dump(mode="json")

    logger.log(
        getattr(logging, event.level.upper()),
        json.dumps(payload, ensure_ascii=False),
    )

    if _event_sink is not None:
        _event_sink(event)
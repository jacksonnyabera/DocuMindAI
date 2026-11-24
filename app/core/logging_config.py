import json
import logging
from datetime import datetime, timezone
from logging import LogRecord

from app.core.config import settings


SAFE_FIELDS = (
    "event",
    "request_id",
    "worker_id",
    "job_id",
    "document_id",
    "organization_id",
    "attempt",
    "max_attempts",
    "status",
    "duration_ms",
    "error_type",
)


class JsonFormatter(logging.Formatter):
    """Format log records as structured JSON without arbitrary extra fields."""

    def format(self, record: LogRecord) -> str:
        timestamp = datetime.fromtimestamp(
            record.created,
            tz=timezone.utc,
        ).isoformat(timespec="milliseconds").replace("+00:00", "Z")

        payload = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in SAFE_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            exception = record.exc_info[1]
            if exception is not None:
                payload["error_type"] = type(exception).__name__
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """Configure consistent JSON logging for API and worker processes."""

    configured_level = getattr(
        logging,
        settings.log_level.strip().upper(),
        logging.INFO,
    )

    if not isinstance(configured_level, int):
        configured_level = logging.INFO

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(configured_level)

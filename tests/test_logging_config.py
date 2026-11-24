import json
import logging

from app.core.logging_config import JsonFormatter


def test_json_formatter_outputs_standard_fields():
    record = logging.LogRecord(
        name="documind.worker",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Worker started",
        args=(),
        exc_info=None,
    )
    record.event = "worker_started"
    record.worker_id = "worker-01"

    result = json.loads(JsonFormatter().format(record))

    assert result["level"] == "INFO"
    assert result["logger"] == "documind.worker"
    assert result["message"] == "Worker started"
    assert result["event"] == "worker_started"
    assert result["worker_id"] == "worker-01"
    assert result["timestamp"].endswith("Z")


def test_json_formatter_omits_unapproved_extra_fields():
    record = logging.LogRecord(
        name="documind.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=20,
        msg="Request processed",
        args=(),
        exc_info=None,
    )
    record.password = "must-not-appear"
    record.api_key = "must-not-appear"

    result = JsonFormatter().format(record)

    assert "must-not-appear" not in result
    assert "password" not in result
    assert "api_key" not in result


def test_json_formatter_includes_exception_type():
    try:
        raise ValueError("invalid document")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="documind.worker",
        level=logging.ERROR,
        pathname=__file__,
        lineno=30,
        msg="Document processing failed",
        args=(),
        exc_info=exc_info,
    )

    result = json.loads(JsonFormatter().format(record))

    assert result["level"] == "ERROR"
    assert result["error_type"] == "ValueError"
    assert "ValueError: invalid document" in result["exception"]

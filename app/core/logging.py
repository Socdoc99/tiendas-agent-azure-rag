import logging
import logging.config


class ContextDefaults(logging.Filter):
    """Add empty structured fields to log records without request context."""

    def filter(self, record: logging.LogRecord) -> bool:
        for field in ("request_id", "endpoint", "http_status", "latency_ms", "error_type"):
            if not hasattr(record, field):
                setattr(record, field, "-")
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure concise application logs without request or document contents."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": (
                        "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s "
                        "endpoint=%(endpoint)s http_status=%(http_status)s "
                        "latency_ms=%(latency_ms)s error_type=%(error_type)s %(message)s"
                    )
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "filters": ["context_defaults"],
                }
            },
            "filters": {"context_defaults": {"()": ContextDefaults}},
            "root": {"handlers": ["console"], "level": level.upper()},
        }
    )

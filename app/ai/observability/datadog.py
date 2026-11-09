from ...core.config import settings


def initialize_datadog() -> bool:
    if not settings.DATADOG_ENABLED:
        return False
    try:
        from datadog import initialize
    except ImportError:
        return False
    initialize(
        statsd_host=settings.DD_AGENT_HOST,
        statsd_port=settings.DD_DOGSTATSD_PORT,
        statsd_namespace="vacation.planner",
    )
    return True

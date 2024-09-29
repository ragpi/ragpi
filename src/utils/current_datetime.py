from datetime import datetime, timezone


def current_datetime():
    return datetime.now(timezone.utc).isoformat()

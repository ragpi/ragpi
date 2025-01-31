from datetime import datetime, timezone


def get_current_datetime():
    return datetime.now(timezone.utc)

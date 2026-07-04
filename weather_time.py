# Stub for Linux compatibility
from datetime import datetime

async def handle_time() -> str:
    """Return current time."""
    return f"Current time: {datetime.now().strftime('%I:%M %p')}"


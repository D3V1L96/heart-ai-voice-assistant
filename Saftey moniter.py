"""
HEART Safety Monitor
====================
"""

import sys
from pathlib import Path
import logging

# ====================== PROJECT ROOT SETUP ======================
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.event_bus import Channel, EventBus, HEARTEvent
from config import CONFIG

log = logging.getLogger(__name__)

# Fields that must NEVER appear in any event payload
FORBIDDEN_FIELDS = {
    "face_embedding", "face_crop", "person_id", "identity",
    "biometric", "face_id", "user_id",
}


class SafetyMonitor:
    def __init__(self, bus: EventBus, strict: bool = False) -> None:
        self._bus = bus
        self._strict = strict
        self._violation_count = 0

        bus.subscribe_wildcard(self.on_event)
        log.info("SafetyMonitor active (strict=%s)", strict)

    async def on_event(self, event: HEARTEvent) -> None:
        self._check_privacy(event)
        self._check_health(event)

    def _check_privacy(self, event: HEARTEvent) -> None:
        violations = FORBIDDEN_FIELDS.intersection(event.payload.keys())
        if not violations:
            return

        self._violation_count += 1
        msg = (
            f"PRIVACY VIOLATION — module '{event.source}' "
            f"emitted forbidden fields {violations} on channel '{event.channel}'"
        )
        log.error(msg)

        if self._strict:
            raise PrivacyViolationError(msg)

        self._bus.emit_sync(
            Channel.SAFETY,
            {
                "event": "privacy_violation",
                "source": event.source,
                "channel": event.channel,
                "forbidden_fields": list(violations),
                "violation_count": self._violation_count,
            },
            source="safety_monitor",
        )

    @staticmethod
    def _check_health(event: HEARTEvent) -> None:
        """Flag stale events."""
        age_ms = event.age_ms()
        if age_ms > 500:
            log.warning(
                "Stale event on '%s' from '%s': %.0fms old",
                event.channel, event.source, age_ms
            )


class PrivacyViolationError(RuntimeError):
    """Raised in strict mode when forbidden identity data is emitted."""
"""WIB timestamp conversion — Strict DD/MM/YYYY HH:mm:ss."""
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

WIB_OFFSET = 7
WIB_FMT = "%d/%m/%Y %H:%M:%S"


def utc_to_wib(utc_str: str) -> str:
    """Convert UTC ISO string to WIB formatted string.
    
    Handles:
    - Standard ISO format: 2026-07-07T14:30:45
    - With Z suffix: 2026-07-07T14:30:45Z
    - With timezone offset: 2026-07-07T14:30:45+00:00
    """
    if not utc_str:
        return ""
    
    try:
        # FIX: Handle multiple ISO formats
        # Remove 'Z' suffix
        clean_str = utc_str.replace('Z', '+00:00')
        
        # Parse ISO format
        dt = datetime.fromisoformat(clean_str)
        
        # FIX: If timezone-aware, convert to UTC first
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        
        # Convert to WIB
        wib_dt = dt + timedelta(hours=WIB_OFFSET)
        return wib_dt.strftime(WIB_FMT)
        
    except (ValueError, TypeError) as e:
        # FIX: Log error dan return original string
        logger.warning(f"Failed to convert UTC to WIB: {utc_str} — {e}")
        return str(utc_str)


def wib_to_utc(wib_str: str) -> str:
    """Convert WIB formatted string back to UTC ISO string."""
    if not wib_str:
        return ""
    
    try:
        wib_dt = datetime.strptime(wib_str, WIB_FMT)
        utc_dt = wib_dt - timedelta(hours=WIB_OFFSET)
        return utc_dt.isoformat()
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to convert WIB to UTC: {wib_str} — {e}")
        return str(wib_str)

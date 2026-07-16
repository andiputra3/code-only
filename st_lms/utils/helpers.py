"""Unique ID generators for all ST-LMS v2.0 entities."""
import uuid
from datetime import datetime


def generate_plan_id(symbol: str, direction: str) -> str:
    """Generate unique plan ID."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"PLAN_{symbol}_{direction}_{short_uuid}"


def generate_line_id(symbol: str, timeframe: str, direction: str, start_idx: int) -> str:
    """Generate unique line ID with validation.
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        timeframe: Candle timeframe (e.g., 'H1')
        direction: Line direction ('LONG' or 'SHORT')
        start_idx: Starting candle index
    
    Returns:
        Unique line ID string
    """
    # FIX: Validasi input
    if not symbol or not timeframe or direction not in ('LONG', 'SHORT'):
        raise ValueError(f"Invalid line parameters: {symbol}, {timeframe}, {direction}")
    
    if start_idx < 0:
        raise ValueError(f"start_idx must be non-negative, got {start_idx}")
    
    # FIX: Tambahkan timestamp untuk uniqueness
    ts_short = int(datetime.utcnow().timestamp()) % 100000
    
    return f"ST_{symbol}_{timeframe}_{direction}_{start_idx}_{ts_short}"


def generate_snapshot_id(prefix: str = "SNAP") -> str:
    """Generate unique snapshot ID with timestamp and UUID."""
    ts_ms = int(datetime.utcnow().timestamp() * 1000)
    short_uuid = uuid.uuid4().hex[:6]  # Cryptographically random
    return f"{prefix}_{ts_ms}_{short_uuid}"


def generate_trade_id(plan_id: str) -> str:
    """Generate unique trade ID from plan ID."""
    suffix = plan_id.split("_")[-1] if "_" in plan_id else plan_id[-8:]
    short_uuid = uuid.uuid4().hex[:8]
    return f"TRD_{suffix}_{short_uuid}"


def generate_authorization_id(plan_id: str) -> str:
    """Generate unique authorization ID."""
    suffix = plan_id.split("_")[-1] if "_" in plan_id else plan_id[-8:]
    short_uuid = uuid.uuid4().hex[:6]
    return f"AUTH_{suffix}_{short_uuid}"


def generate_grid_id(plan_id: str) -> str:
    """Generate unique grid ID."""
    suffix = plan_id.split("_")[-1] if "_" in plan_id else plan_id[-8:]
    short_uuid = uuid.uuid4().hex[:6]
    return f"GRID_{suffix}_{short_uuid}"


def generate_review_id(plan_id: str) -> str:
    """Generate unique review ID."""
    suffix = plan_id.split("_")[-1] if "_" in plan_id else plan_id[-8:]
    short_uuid = uuid.uuid4().hex[:6]
    return f"RVR_{suffix}_{short_uuid}"


def generate_pattern_instance_id(pattern_id: str, symbol: str) -> str:
    """Generate unique pattern instance ID."""
    short_uuid = uuid.uuid4().hex[:6]
    return f"PAT_{pattern_id}_{symbol}_{short_uuid}"


def generate_telemetry_id(cycle_id: str, stage: str) -> str:
    """Generate unique telemetry ID."""
    cycle_short = cycle_id[-6:] if len(cycle_id) > 6 else cycle_id
    short_uuid = uuid.uuid4().hex[:4]
    return f"TEL_{cycle_short}_{stage}_{short_uuid}"


def generate_cycle_id(symbol: str) -> str:
    """Generate unique cycle ID."""
    ts_ms = int(datetime.utcnow().timestamp() * 1000)
    return f"CYC_{symbol}_{ts_ms}"

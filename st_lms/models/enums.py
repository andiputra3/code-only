"""ST-LMS v2.0 Enums — All enumeration types."""
from enum import Enum


class PlanState(Enum):
    """Trading Plan lifecycle states."""
    OBSERVING = "OBSERVING"
    BUILDING = "BUILDING"
    WAIT_PULLBACK = "WAIT_PULLBACK"
    WAIT_BREAKOUT = "WAIT_BREAKOUT"
    READY = "READY"
    ACTIVE = "ACTIVE"
    DEFENDING = "DEFENDING"
    EXITING = "EXITING"
    FINISHED = "FINISHED"
    LEARNING = "LEARNING"


class PlanDirection(Enum):
    """Trading plan directions."""
    LONG = "LONG"
    SHORT = "SHORT"
    SIDEWAY = "SIDEWAY"


class PlanStrategy(Enum):
    """Trading plan strategies."""
    ADAPTIVE = "ADAPTIVE"
    LONG_ONLY = "LONG_ONLY"
    SHORT_ONLY = "SHORT_ONLY"
    SIDEWAY_ONLY = "SIDEWAY_ONLY"
    ADAPTIVE_GRID_SIDEWAY = "ADAPTIVE_GRID_SIDEWAY"


class RiverVerdict(Enum):
    """River review verdicts."""
    APPROVE = "APPROVE"
    CAUTION = "CAUTION"
    REJECT = "REJECT"


class ExecutionOrderType(Enum):
    """Order types for execution."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    OCO = "OCO"


class ExecutionStatus(Enum):
    """Execution track status."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class TelemetryStatus(Enum):
    """Pipeline telemetry status."""
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class LineStatus(Enum):
    """Supertrend line status."""
    ACTIVE = "ACTIVE"
    BROKEN = "BROKEN"
    ARCHIVED = "ARCHIVED"


class LineDirection(Enum):
    """Supertrend line direction."""
    LONG = "LONG"
    SHORT = "SHORT"


class DistanceHealth(Enum):
    """Distance health classification."""
    OPTIMAL = "OPTIMAL"
    NORMAL = "NORMAL"
    EXTENDED = "EXTENDED"


class MarketType(Enum):
    """Market type."""
    FUTURES_USDM = "FUTURES_USDM"
    SPOT = "SPOT"


class ParticipationMetric(Enum):
    """Participation metric type."""
    OPEN_INTEREST = "OPEN_INTEREST"
    VOLUME_DELTA = "VOLUME_DELTA"


class RiskMethod(Enum):
    """Risk calculation method."""
    FIXED_FRACTION = "fixed_fraction"
    KELLY = "kelly"


class GridZoneType(Enum):
    """Grid zone type."""
    NATIVE_ZONE = "NATIVE_ZONE"
    ATR_INTERPOLATED = "ATR_INTERPOLATED"


class GridStatus(Enum):
    """Grid level status."""
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


class OutcomeCategory(Enum):
    """Learning outcome category."""
    PENDING = "PENDING"
    WIN = "WIN"
    LOSS = "LOSS"
    MISSED_OPPORTUNITY = "MISSED_OPPORTUNITY"
    CORRECT_REJECTION = "CORRECT_REJECTION"


class PatternRarity(Enum):
    """Pattern rarity classification."""
    COMMON = "COMMON"
    RARE = "RARE"
    EPIC = "EPIC"


class GeometryType(Enum):
    """Market geometry classification."""
    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"
    CORRIDOR = "CORRIDOR"
    CONVERGING = "CONVERGING"
    DIVERGING = "DIVERGING"
    CHAOTIC = "CHAOTIC"
    SINGLE_DIRECTION = "SINGLE_DIRECTION"
    NO_STRUCTURE = "NO_STRUCTURE"

"""
Global configuration for ST-LMS v2.0

Environment Variables:
    ST_LMS_DB_PATH       — Path to SQLite database (default: st_lms_v2.db)
    ST_LMS_LOG_LEVEL     — Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    ST_LMS_BINANCE_KEY   — Binance API key (Phase 4)
    ST_LMS_BINANCE_SECRET— Binance API secret (Phase 4)
    ST_LMS_RISK_PERCENT  — Default risk per trade % (default: 1.0)
    ST_LMS_MAX_LEVERAGE  — Maximum leverage allowed (default: 3)
"""
import os

# Database
DB_PATH = os.getenv("ST_LMS_DB_PATH", "st_lms_v2.db")

# Timezone
WIB_OFFSET_HOURS = 7
WIB_FORMAT = "%d/%m/%Y %H:%M:%S"

# Integer Price System Defaults
DEFAULT_PRICE_SCALE = 8
DEFAULT_QUANTITY_SCALE = 3

# Dashboard
DASHBOARD_REFRESH_INTERVAL_SEC = 30
MODAL_MAX_REVISIONS = 50
MODAL_MAX_RIVER_REVIEWS = 5

# Authorization
AUTHORIZATION_MIN_CONFIDENCE = 65.0

# Risk Management Defaults
DEFAULT_RISK_PERCENT = float(os.getenv("ST_LMS_RISK_PERCENT", "1.0"))
DEFAULT_MAX_LEVERAGE = int(os.getenv("ST_LMS_MAX_LEVERAGE", "3"))

# Logging
LOG_LEVEL = os.getenv("ST_LMS_LOG_LEVEL", "INFO").upper()

# Pipeline Telemetry Stage Names - COMPLETE 18 STAGES
STAGE_NAMES = {
    'OBSERVE': 'C001 - Observe',
    'MEASURE': 'C002 - Measure',
    'STRUCTURE': 'C003 - Supertrend Line Engine',
    'PATTERN_MINE': 'C003.5 - Pattern Miner',
    'PRESERVE': 'C004 - Preserve',
    'REMEMBER': 'C005 - Remember',
    'SELECT': 'C006 - Select',
    'UNDERSTAND': 'C007 - Understand',
    'CLASSIFY': 'C008 - Classify',
    'PLAN_ADAPT': 'C009 - Plan Adaptation',
    'RIVER_REVIEW': 'C010 - River Review',
    'AUTHORIZE': 'C011 - Authorize',
    'EXECUTE': 'C012 - Execute',
    'POST_TRADE': 'Post-Trade Learning',
    'TELEMETRY': 'Telemetry Log',
    'PERSIST': 'Persist Cycle',
}

# Valid timeframes
VALID_TIMEFRAMES = {'M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1'}

# Pattern mining defaults
PATTERN_MIN_SUPPORT = 3
PATTERN_MIN_CONFIDENCE = 0.6

# Supertrend defaults
SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3.0

# ATR defaults
ATR_PERIOD = 14

# Grid trading defaults
GRID_MAX_LEVELS = 10
GRID_ATR_MULTIPLE = 0.5

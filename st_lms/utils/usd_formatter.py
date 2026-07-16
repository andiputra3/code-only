"""USD Price Formatter — Integer → USD display (No IDR)."""
import sqlite3
import logging
from config.settings import DB_PATH

logger = logging.getLogger(__name__)


def format_usd_price(value_int: int, symbol: str, conn: sqlite3.Connection = None) -> str:
    """Convert integer price to USD display format.
    
    Args:
        value_int: Price in integer format
        symbol: Trading pair symbol
        conn: Optional database connection
    
    Returns:
        Formatted USD string (e.g., "$65,000.50")
    """
    if value_int is None or value_int == 0:
        return "$0.00"
    
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        close_conn = True
    
    try:
        row = conn.execute(
            "SELECT profile_price_scale FROM market_profiles WHERE profile_symbol = ?",
            (symbol,)
        ).fetchone()
        
        # FIX: Gunakan scale yang lebih masuk akal sebagai fallback
        # BTCUSDT = scale 1, ETHUSDT = scale 2, dll.
        # Default 2 lebih aman daripada 8 untuk大多数 crypto
        scale = row['profile_price_scale'] if row else 2
        
        # FIX: Validasi scale masuk akal (0-10)
        if not (0 <= scale <= 10):
            logger.warning(f"⚠️  Invalid scale {scale} for {symbol}, using default 2")
            scale = 2
        
        usd_value = value_int / (10 ** scale)
        
        # FIX: Format berdasarkan scale
        if scale == 0:
            return f"${usd_value:,.0f}"
        elif scale <= 2:
            return f"${usd_value:,.2f}"
        else:
            return f"${usd_value:,.{scale}f}"
    finally:
        if close_conn:
            conn.close()

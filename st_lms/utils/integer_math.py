"""Integer-based price math for ST-LMS v2.0 — No floats, no precision loss."""
from decimal import Decimal, ROUND_DOWN
import logging

logger = logging.getLogger(__name__)

# Maximum reasonable price (10^15 = 1 quadrillion)
MAX_REASONABLE_PRICE = 10**15


class ScaledPrice:
    """Immutable integer price with scale metadata."""
    
    def __init__(self, value: int, scale: int, tick_size_int: int, symbol: str):
        self.value = value
        self.scale = scale
        self.tick_size_int = tick_size_int
        self.symbol = symbol
    
    def to_decimal(self) -> Decimal:
        """Convert to Decimal for display."""
        return Decimal(self.value) / (Decimal(10) ** self.scale)
    
    def __str__(self) -> str:
        return str(self.to_decimal())
    
    def __repr__(self) -> str:
        return f"ScaledPrice({self.value}, scale={self.scale}, {self.symbol})"


class IntegerMath:
    """Arithmetic operations on ScaledPrice."""

    @staticmethod
    def from_raw(price, scale: int, tick_size_int: int, symbol: str) -> ScaledPrice:
        """Create ScaledPrice from raw price value."""
        d = Decimal(str(price))
        multiplier = Decimal(10) ** scale
        normalized = (d * multiplier).quantize(Decimal('1'), rounding=ROUND_DOWN)
        result = int(normalized)
        
        # FIX: Overflow check
        if abs(result) > MAX_REASONABLE_PRICE:
            logger.warning(
                f"⚠️  Price {result} exceeds maximum reasonable value. "
                f"Possible scale error for {symbol}."
            )
        
        return ScaledPrice(result, scale, tick_size_int, symbol)

    @staticmethod
    def add(a: ScaledPrice, b: ScaledPrice) -> ScaledPrice:
        """Add two ScaledPrice values."""
        if a.scale != b.scale or a.symbol != b.symbol:
            raise ValueError(f"Scale/symbol mismatch: {a} vs {b}")
        
        result = a.value + b.value
        
        # FIX: Overflow check
        if abs(result) > MAX_REASONABLE_PRICE:
            logger.warning(f"⚠️  Addition result {result} exceeds maximum")
        
        return ScaledPrice(result, a.scale, a.tick_size_int, a.symbol)

    @staticmethod
    def sub(a: ScaledPrice, b: ScaledPrice) -> ScaledPrice:
        """Subtract two ScaledPrice values."""
        if a.scale != b.scale or a.symbol != b.symbol:
            raise ValueError(f"Scale/symbol mismatch: {a} vs {b}")
        return ScaledPrice(a.value - b.value, a.scale, a.tick_size_int, a.symbol)

    @staticmethod
    def abs_diff(a: ScaledPrice, b: ScaledPrice) -> int:
        """Calculate absolute difference between two prices."""
        return abs(a.value - b.value)

    @staticmethod
    def distance_in_atr(price: ScaledPrice, line_price: ScaledPrice, atr_int: int) -> float:
        """Calculate distance in ATR units."""
        if atr_int == 0:
            return 999.0
        return abs(price.value - line_price.value) / atr_int

    @staticmethod
    def is_within_zone(price: ScaledPrice, low: ScaledPrice, high: ScaledPrice) -> bool:
        """Check if price is within a zone."""
        return low.value <= price.value <= high.value

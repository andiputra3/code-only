"""C003: Supertrend Line Engine — Build lines + horizontal detection.
Replaces MultiTimeframeStructuralEngine from v1.x.

Dependency: models.enums, utils.integer_math ONLY.
Output: List[RawSupertrendLine] per timeframe.
"""
from dataclasses import dataclass
from typing import List
from st_lms.utils.integer_math import ScaledPrice, IntegerMath
from st_lms.utils.helpers import generate_line_id


@dataclass
class RawSupertrendLine:
    """Intermediate line representation before personality calculation."""
    line_id: str
    symbol: str
    timeframe: str
    direction: str                      # 'LONG' or 'SHORT'
    price_int: int
    start_price_int: int
    current_price_int: int
    prev_price_int: int
    start_timestamp: str
    age_candles: int
    touch_count: int
    status: str                         # 'ACTIVE', 'BROKEN', 'ARCHIVED'
    is_horizontal: bool
    current_price_scaled: ScaledPrice


class SupertrendLineEngine:
    """Build Supertrend Lines from candle data with horizontal focus.

    Philosophy: Horizontal lines are PRIMARY authority for structure.
    Sloped lines are SECONDARY (only for trend energy measurement).
    """

    def __init__(self, atr_period: int = 10, multiplier: float = 3.0):
        self.atr_period = atr_period
        self.multiplier = multiplier

    def build_lines(
        self, symbol: str, timeframe: str, candles: List[dict],
        scale: int, tick_size_int: int
    ) -> List[RawSupertrendLine]:
        """Build Supertrend Lines from raw candle data.

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe (H4, H1, M15, M5, M1)
            candles: List of candle dicts with OHLCV + timestamp
            scale: Price scale from market_profiles
            tick_size_int: Tick size in integer form

        Returns:
            List of RawSupertrendLine (both ACTIVE and ARCHIVED)
        """
        if len(candles) < self.atr_period + 1:
            return []

        lines: List[RawSupertrendLine] = []
        direction = "LONG"
        line_price = int(candles[0].get('close', 0))
        start_idx = 0

        for i in range(self.atr_period, len(candles)):
            high = candles[i].get('high', 0)
            low = candles[i].get('low', 0)
            close = candles[i].get('close', 0)

            # Calculate ATR locally for this window
            trs = []
            for j in range(max(1, i - self.atr_period), i):
                h = candles[j].get('high', 0)
                l_val = candles[j].get('low', 0)
                pc = candles[j - 1].get('close', l_val) if j > 0 else l_val
                trs.append(max(h - l_val, abs(h - pc), abs(l_val - pc)))
            atr = sum(trs) / len(trs) if trs else 1

            upper_band = line_price + self.multiplier * atr
            lower_band = line_price - self.multiplier * atr

            if direction == "LONG" and close < lower_band:
                # Flip to SHORT — archive previous LONG line
                direction = "SHORT"
                line_price = int(upper_band)
                lines.append(self._create_line(
                    symbol, timeframe, "LONG", line_price,
                    candles[start_idx], candles[i - 1], start_idx, i - 1,
                    scale, tick_size_int, status="ARCHIVED"
                ))
                start_idx = i
            elif direction == "SHORT" and close > upper_band:
                # Flip to LONG — archive previous SHORT line
                direction = "LONG"
                line_price = int(lower_band)
                lines.append(self._create_line(
                    symbol, timeframe, "SHORT", line_price,
                    candles[start_idx], candles[i - 1], start_idx, i - 1,
                    scale, tick_size_int, status="ARCHIVED"
                ))
                start_idx = i

        # Current active line
        if start_idx < len(candles):
            lines.append(self._create_line(
                symbol, timeframe, direction, line_price,
                candles[start_idx], candles[-1], start_idx, len(candles) - 1,
                scale, tick_size_int, status="ACTIVE"
            ))

        return lines

    def _create_line(
        self, symbol, tf, direction, price, start_candle, end_candle,
        start_idx, end_idx, scale, tick_size_int, status="ARCHIVED"
    ) -> RawSupertrendLine:
        """Build a single RawSupertrendLine instance."""
        age = end_idx - start_idx
        price_scaled = IntegerMath.from_raw(price, scale, tick_size_int, symbol)
        start_price = int(start_candle.get('close', price))
        current_price = int(end_candle.get('close', price))

        # Horizontal detection: <0.5% price change AND age > 5 candles
        price_change_pct = abs(current_price - start_price) / max(start_price, 1) * 100
        is_horizontal = price_change_pct < 0.5 and age > 5

        # Touch count estimation: frequency of price crosses near line
        touch_count = max(1, age // 10)

        return RawSupertrendLine(
            line_id=generate_line_id(symbol, tf, direction, start_idx),
            symbol=symbol, timeframe=tf, direction=direction,
            price_int=int(price), start_price_int=start_price,
            current_price_int=current_price, prev_price_int=start_price,
            start_timestamp=start_candle.get('timestamp', ''),
            age_candles=age, touch_count=touch_count,
            status=status, is_horizontal=is_horizontal,
            current_price_scaled=price_scaled
        )

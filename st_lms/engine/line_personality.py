"""Supertrend Line Personality Engine — 5 Dimensions + Composite Score.

5 Dimensions:
  1. Age          — candles since line formed
  2. Strength     — touch count (0-100)
  3. Velocity     — price change speed (integer)
  4. Slope Quality — 0-100 (ideal = 15-45 degrees)
  5. Distance Health — OPTIMAL / NORMAL / EXTENDED

Dependency: models.enums, utils.integer_math ONLY.
"""
import math
from dataclasses import dataclass
from typing import List
from st_lms.utils.integer_math import ScaledPrice, IntegerMath


@dataclass
class LinePersonality:
    """5-dimension personality of a Supertrend Line."""
    line_id: str
    age_candles: int
    touch_count: int
    velocity_int: int
    slope_quality: float       # 0-100
    distance_health: str       # OPTIMAL | NORMAL | EXTENDED
    quality_score: float       # 0-100 composite
    is_horizontal: bool
    price_int: int             # Current line price (integer)
    direction: str             # LONG or SHORT


class LinePersonalityEngine:
    """Compute 5-dimension personality for Supertrend Lines."""

    HORIZONTAL_THRESHOLD_DEG = 5.0
    IDEAL_SLOPE_MIN = 15.0
    IDEAL_SLOPE_MAX = 45.0
    STEEP_SLOPE_MAX = 60.0

    def calculate(
        self, line, current_price: ScaledPrice,
        atr_int: int, natural_zones: List[ScaledPrice]
    ) -> LinePersonality:
        """Compute full personality for a single line."""
        age = getattr(line, 'age_candles', 0)
        touch_count = getattr(line, 'touch_count', 0)
        strength = min(touch_count * 10, 100)

        curr_price = getattr(line, 'current_price_int', 0)
        prev_price = getattr(line, 'prev_price_int', curr_price)
        velocity = abs(curr_price - prev_price)

        slope_deg = self._calc_slope_degrees(line)
        is_horizontal = slope_deg < self.HORIZONTAL_THRESHOLD_DEG
        slope_quality = self._score_slope(slope_deg, is_horizontal)

        line_price_scaled = getattr(line, 'current_price_scaled', None)
        if line_price_scaled is None:
            # Fallback: build ScaledPrice from integer
            line_price_scaled = ScaledPrice(
                value=curr_price,
                scale=current_price.scale,
                tick_size_int=current_price.tick_size_int,
                symbol=current_price.symbol,
            )

        distance_health = self._calc_distance_health(
            current_price, line_price_scaled, atr_int, natural_zones
        )

        # Composite quality score (weighted)
        age_score = min(age * 2, 100)          # Mature = better (cap at 50 candles)
        velocity_stability = max(0, 100 - velocity)  # Stable = safer

        quality = (
            age_score * 0.30 +
            strength * 0.30 +
            slope_quality * 0.25 +
            velocity_stability * 0.15
        )

        return LinePersonality(
            line_id=getattr(line, 'line_id', ''),
            age_candles=age,
            touch_count=touch_count,
            velocity_int=velocity,
            slope_quality=round(slope_quality, 2),
            distance_health=distance_health,
            quality_score=round(quality, 2),
            is_horizontal=is_horizontal,
            price_int=curr_price,
            direction=getattr(line, 'direction', 'LONG'),
        )

    def _calc_slope_degrees(self, line) -> float:
        """Calculate line slope in degrees."""
        age = getattr(line, 'age_candles', 0)
        if age == 0:
            return 0.0
        start_price = getattr(line, 'start_price_int', 0)
        curr_price = getattr(line, 'current_price_int', start_price)
        price_change = abs(curr_price - start_price)
        ratio = price_change / max(age, 1)
        # Normalize: ratio/1000 for stable angle calculation
        return math.degrees(math.atan(ratio / 1000))

    def _score_slope(self, angle: float, is_horizontal: bool) -> float:
        """Score slope quality 0-100."""
        if is_horizontal:
            return 80.0  # Horizontal lines valuable as S/R
        if self.IDEAL_SLOPE_MIN <= angle <= self.IDEAL_SLOPE_MAX:
            return 100.0  # Ideal healthy trend
        elif angle < self.IDEAL_SLOPE_MIN:
            return 40.0   # Too flat
        elif angle <= self.STEEP_SLOPE_MAX:
            return 75.0   # Strong but demanding
        return 20.0       # Parabolic — dangerous

    def _calc_distance_health(
        self, price: ScaledPrice, line_price: ScaledPrice,
        atr_int: int, zones: List[ScaledPrice]
    ) -> str:
        """Compute distance health using ATR + natural zones."""
        atr_dist = IntegerMath.distance_in_atr(price, line_price, atr_int)
        zone_dist = 999.0
        if zones:
            nearest = min(zones, key=lambda z: abs(z.value - price.value))
            zone_dist = IntegerMath.distance_in_atr(price, nearest, atr_int)

        if atr_dist < 0.5 and zone_dist < 0.3:
            return "OPTIMAL"    # Entry zone
        elif atr_dist < 1.5:
            return "NORMAL"     # Safe but wait for pullback
        return "EXTENDED"       # Rubber band stretched

"""Unified Participation Calculator — Spot/Futures Abstraction.

Futures mode: uses Open Interest
Spot mode: uses Taker Buy/Sell Volume Delta

Output: Participation Health Score 0-100 (same for both markets).
Plan does not need to know the data source.
"""
from typing import Optional, List


class UnifiedParticipationCalculator:
    """Compute participation health independent of market type."""

    def calculate(self, enable_open_interest: bool,
                  oi_values: Optional[List[int]] = None,
                  taker_buy_vols: Optional[List[int]] = None,
                  taker_sell_vols: Optional[List[int]] = None,
                  volumes: Optional[List[int]] = None) -> float:
        """Return participation health score 0-100."""
        if enable_open_interest:
            return self._futures_participation(oi_values, volumes)
        return self._spot_participation(taker_buy_vols, taker_sell_vols, volumes)

    def _futures_participation(self, oi_values, volumes) -> float:
        """OI-based participation score."""
        if not oi_values or len(oi_values) < 2:
            return 50.0  # Neutral

        oi_delta = oi_values[-1] - oi_values[-2]
        oi_trend = sum(1 for i in range(1, len(oi_values))
                       if oi_values[i] > oi_values[i-1])
        trend_ratio = oi_trend / max(len(oi_values) - 1, 1)

        score = 50 + (trend_ratio * 40)
        if oi_delta > 0:
            score += 10  # New money entering
        return min(100, max(0, score))

    def _spot_participation(self, taker_buy, taker_sell, volumes) -> float:
        """Volume Delta-based participation score."""
        if not taker_buy or not taker_sell or len(taker_buy) < 2:
            return 50.0

        # Volume Delta = Taker Buy - Taker Sell
        deltas = [b - s for b, s in zip(taker_buy, taker_sell)]
        avg_delta = sum(deltas) / len(deltas)

        total_vol = (sum(volumes[-len(deltas):]) if volumes
                     else sum(abs(d) for d in deltas))
        if total_vol == 0:
            return 50.0

        delta_ratio = avg_delta / (total_vol / len(deltas))
        return min(100, max(0, 50 + delta_ratio * 50))

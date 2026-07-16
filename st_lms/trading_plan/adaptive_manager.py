"""Adaptive Trading Plan Manager — 3 Parallel Plans + Mirror Engine + Revision Tracking.

3 plans always live in parallel:
  - LONG  (mirror engine)
  - SHORT (mirror engine)
  - SIDEWAY (adaptive grid)

Dependency: models.enums ONLY.
"""
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from st_lms.models.enums import PlanState


@dataclass
class AdaptivePlan:
    """Single adaptive trading plan."""
    plan_id: str
    symbol: str
    direction: str                      # 'LONG', 'SHORT', 'SIDEWAY'
    strategy: str = 'ADAPTIVE'
    state: PlanState = PlanState.OBSERVING
    confidence: float = 0.0
    health_score: float = 0.0

    # 5-dimension health (weighted 35/25/20/15/5)
    structure_health: float = 0.0
    risk_health: float = 0.0
    momentum_health: float = 0.0
    participation_health: float = 0.0
    execution_health: float = 0.0

    # Risk configuration
    risk_method: str = 'fixed_fraction'
    risk_percent: float = 1.0
    leverage: int = 1
    position_size_int: int = 0
    funding_cost_estimate: float = 0.0
    liquidation_price_int: int = 0

    # Structure mapping
    primary_line_id: Optional[str] = None
    backup_line_id: Optional[str] = None
    entry_zone_low_int: Optional[int] = None
    entry_zone_high_int: Optional[int] = None
    stop_loss_int: Optional[int] = None
    take_profit_int: Optional[int] = None

    # Pattern context
    active_patterns_count: int = 0
    pattern_score: float = 0.0
    pattern_verdict: str = 'NEUTRAL'

    revision_count: int = 0


class AdaptivePlanManager:
    """Manage 3 parallel trading plans with mirror adaptation."""

    CONFIDENCE_LADDER = {
        PlanState.OBSERVING: (0, 30),
        PlanState.BUILDING: (30, 50),
        PlanState.WAIT_PULLBACK: (50, 65),
        PlanState.READY: (65, 80),
        PlanState.ACTIVE: (80, 100),
    }

    HEALTH_WEIGHTS = {
        'structure': 0.35,
        'risk': 0.25,
        'momentum': 0.20,
        'participation': 0.15,
        'execution': 0.05,
    }

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.plans: Dict[str, AdaptivePlan] = {}
        self._revision_history: List[Tuple] = []
        self._init_three_plans()

    def _init_three_plans(self):
        """Initialize LONG, SHORT, SIDEWAY plans in OBSERVING state."""
        for d in ['LONG', 'SHORT', 'SIDEWAY']:
            self.plans[d] = AdaptivePlan(
                plan_id=f"{self.symbol}_{d}",
                symbol=self.symbol,
                direction=d,
                strategy='ADAPTIVE_GRID_SIDEWAY' if d == 'SIDEWAY' else 'ADAPTIVE',
                state=PlanState.OBSERVING,
                confidence=0.0,
                health_score=0.0,
                risk_method='fixed_fraction',
            )

    def compute_health(self, plan: AdaptivePlan) -> float:
        """Compute weighted 5-dimension health score."""
        h = (
            plan.structure_health * self.HEALTH_WEIGHTS['structure'] +
            plan.risk_health * self.HEALTH_WEIGHTS['risk'] +
            plan.momentum_health * self.HEALTH_WEIGHTS['momentum'] +
            plan.participation_health * self.HEALTH_WEIGHTS['participation'] +
            plan.execution_health * self.HEALTH_WEIGHTS['execution']
        )
        plan.health_score = round(h, 2)
        return plan.health_score

    def update_state_from_confidence(self, plan: AdaptivePlan):
        """Map confidence to state via ladder."""
        for state, (min_c, max_c) in self.CONFIDENCE_LADDER.items():
            if min_c <= plan.confidence < max_c:
                if plan.state != state:
                    plan.revision_count += 1
                plan.state = state
                return
        plan.state = PlanState.OBSERVING

    def select_winner(self) -> Optional[AdaptivePlan]:
        """Select plan with highest health among viable (confidence > 50)."""
        viable = [p for p in self.plans.values() if p.confidence > 50]
        return max(viable, key=lambda p: p.health_score) if viable else None

    def adapt_to_line_change(self, direction: str, confidence_delta: float,
                              new_structure_health: float, reason: str):
        """Adapt plan based on Supertrend Line change + mirror opposite plan."""
        plan = self.plans.get(direction)
        if not plan:
            return

        old_conf = plan.confidence
        old_health = plan.health_score

        plan.confidence = max(0.0, min(100.0, plan.confidence + confidence_delta))
        plan.structure_health = new_structure_health
        self.compute_health(plan)
        self.update_state_from_confidence(plan)

        # Record revision if significant change
        if abs(old_conf - plan.confidence) > 1.0 or plan.state != PlanState.OBSERVING:
            self._revision_history.append((
                plan.plan_id, reason, plan.state.value,
                old_conf, plan.confidence, old_health, plan.health_score
            ))

        # Mirror adaptation: LONG up → SHORT down (and vice versa)
        if direction in ('LONG', 'SHORT'):
            opp_dir = 'SHORT' if direction == 'LONG' else 'LONG'
            opp = self.plans[opp_dir]
            opp_old_conf = opp.confidence
            opp_old_health = opp.health_score
            opp.confidence = max(0.0, min(100.0, opp.confidence - confidence_delta * 0.7))
            self.compute_health(opp)
            self.update_state_from_confidence(opp)
            if abs(opp_old_conf - opp.confidence) > 1.0:
                self._revision_history.append((
                    opp.plan_id, f"MIRROR_{reason}", opp.state.value,
                    opp_old_conf, opp.confidence, opp_old_health, opp.health_score
                ))

    def get_pending_revisions(self) -> List[Tuple]:
        """Return buffered revisions and clear buffer."""
        revisions = self._revision_history.copy()
        self._revision_history.clear()
        return revisions

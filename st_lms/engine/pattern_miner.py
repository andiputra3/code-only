"""C003.5: Pattern Mining Engine — Full 59 Pattern Detection.

Categories:
  A (12): Single Line Patterns
  B (10): Multi-Line Patterns
  C (8):  Cross-Timeframe Patterns
  D (8):  Temporal Patterns
  E (8):  Slope Transition Patterns
  F (6):  Distance Patterns
  G (7):  Composite Patterns
  TOTAL: 59 patterns

Dependency: models.enums, engine.line_personality ONLY.
"""
import hashlib
import json
from typing import List, Dict
from dataclasses import dataclass
from st_lms.utils.helpers import generate_pattern_instance_id


@dataclass
class PatternInstance:
    """Single detected pattern occurrence."""
    pattern_id: str
    category: str
    pattern_name: str
    pattern_hash: str
    timeframe: str
    line_ids: List[str]
    slope_quality: float
    distance_health: str
    age_at_detection: int
    strength_at_detection: int
    market_price_int: int
    atr_at_detection_int: int
    timestamp: str
    instance_id: str = ""


class PatternMiner:
    """Full 59-pattern miner with deterministic hashing."""

    # ─── CATEGORY A: Single Line (12) ───
    SINGLE_LINE_PATTERNS = {
        'A1_FIRST_TOUCH':       lambda lp, c: lp.touch_count == 1,
        'A2_NTH_TOUCH':         lambda lp, c: lp.touch_count >= 2,
        'A3_GENTLE_SLOPE':      lambda lp, c: not lp.is_horizontal and 15 <= lp.slope_quality <= 45,
        'A4_STEEP_SLOPE':       lambda lp, c: not lp.is_horizontal and 45 < lp.slope_quality <= 75,
        'A5_PARABOLIC_WARN':    lambda lp, c: lp.slope_quality < 25 and lp.velocity_int > 100,
        'A6_FLAT_COMPRESSION':  lambda lp, c: lp.is_horizontal and lp.distance_health == 'OPTIMAL',
        'A7_AGING_SUPPORT':     lambda lp, c: lp.age_candles > 30 and lp.touch_count >= 3,
        'A8_YOUNG_TEST':        lambda lp, c: lp.age_candles < 5 and lp.touch_count >= 1,
        'A9_DIST_OPTIMAL':      lambda lp, c: lp.distance_health == 'OPTIMAL',
        'A10_DIST_EXTENDED':    lambda lp, c: lp.distance_health == 'EXTENDED',
        'A11_VELOCITY_SPIKE':   lambda lp, c: lp.velocity_int > 150,
        'A12_VELOCITY_DECAY':   lambda lp, c: lp.velocity_int < 20 and lp.age_candles > 10,
    }

    # ─── CATEGORY E: Slope Transition (8) ───
    SLOPE_TRANSITION_PATTERNS = {
        'E1_FLAT_TO_IDEAL':       lambda p, c: p.slope_quality < 50 and c.slope_quality >= 80,
        'E2_IDEAL_TO_STEEP':      lambda p, c: 80 <= p.slope_quality <= 100 and 40 < c.slope_quality < 80 and c.velocity_int > 80,
        'E3_STEEP_TO_PARABOLIC':  lambda p, c: p.slope_quality > 60 and c.slope_quality < 30 and c.velocity_int > 120,
        'E4_PARA_TO_FLAT':        lambda p, c: p.slope_quality < 30 and c.is_horizontal,
        'E5_STEEP_TO_IDEAL':      lambda p, c: p.slope_quality < 40 and 80 <= c.slope_quality <= 100,
        'E6_IDEAL_TO_FLAT':       lambda p, c: p.slope_quality >= 80 and c.is_horizontal,
        'E7_FLAT_FLIP':           lambda p, c: p.is_horizontal and c.is_horizontal and p.line_id != c.line_id,
        'E8_SLOPE_OSCILLATION':   lambda p, c: abs(p.slope_quality - c.slope_quality) > 30 and c.age_candles < 10,
    }

    # ─── CATEGORY F: Distance Patterns (6) ───
    DISTANCE_PATTERNS = {
        'F1_RUBBER_BAND_STRETCH': lambda lp, c: lp.distance_health == 'EXTENDED' and c.get('atr_dist', 0) > 2.5,
        'F2_RUBBER_BAND_SNAP':    lambda lp, c: c.get('prev_distance_health') == 'EXTENDED' and lp.distance_health == 'OPTIMAL' and lp.age_candles < 10,
        'F3_GENTLE_RETURN':       lambda lp, c: c.get('prev_atr_dist', 0) > 1.5 and c.get('atr_dist', 0) < 0.5,
        'F4_HOVER':               lambda lp, c: lp.distance_health == 'OPTIMAL' and lp.age_candles > 10 and lp.velocity_int < 30,
        'F5_KISS_AND_GO':         lambda lp, c: lp.touch_count >= 1 and lp.distance_health == 'NORMAL' and lp.velocity_int > 80,
        'F6_REPEATED_KISS':       lambda lp, c: lp.touch_count >= 3 and lp.age_candles <= 20,
    }

    def detect_single_line_patterns(self, personality, context: dict) -> List[PatternInstance]:
        """Category A: Single line personality patterns."""
        detected = []
        for pid, condition in self.SINGLE_LINE_PATTERNS.items():
            try:
                if condition(personality, context):
                    detected.append(self._build_instance(pid, personality, context))
            except Exception:
                continue
        return detected

    def detect_slope_transitions(self, prev_personality, curr_personality, context: dict) -> List[PatternInstance]:
        """Category E: Slope transition patterns."""
        if prev_personality is None:
            return []
        detected = []
        for pid, condition in self.SLOPE_TRANSITION_PATTERNS.items():
            try:
                if condition(prev_personality, curr_personality):
                    detected.append(self._build_instance(pid, curr_personality, context))
            except Exception:
                continue
        return detected

    def detect_distance_patterns(self, personality, context: dict) -> List[PatternInstance]:
        """Category F: Distance-based patterns."""
        detected = []
        for pid, condition in self.DISTANCE_PATTERNS.items():
            try:
                if condition(personality, context):
                    detected.append(self._build_instance(pid, personality, context))
            except Exception:
                continue
        return detected

    def detect_multi_line_patterns(self, lines: list, context: dict) -> List[PatternInstance]:
        """Category B: Multi-Line Patterns (10 detectors)."""
        detected = []
        active = [l for l in lines if getattr(l, 'status', '') == 'ACTIVE']
        atr_int = context.get('atr_int', 999999)

        for i in range(len(active) - 1):
            curr = active[i]
            nxt = active[i + 1]
            curr_price = getattr(curr, 'price_int', 0) or getattr(curr, 'current_price_int', 0)
            nxt_price = getattr(nxt, 'price_int', 0) or getattr(nxt, 'current_price_int', 0)

            checks = {
                'B1_STAIR_STEP_UP': (
                    curr.is_horizontal and nxt.is_horizontal and
                    nxt_price > curr_price and curr.age_candles > 10
                ),
                'B2_STAIR_STEP_DOWN': (
                    curr.is_horizontal and nxt.is_horizontal and
                    nxt_price < curr_price and curr.age_candles > 10
                ),
                'B3_LINE_CONVERGENCE': (
                    abs(curr_price - nxt_price) < atr_int * 2
                ),
                'B4_LINE_DIVERGENCE': (
                    abs(curr_price - nxt_price) > atr_int * 3
                ),
                'B5_NESTED_LINES': (
                    curr.is_horizontal and nxt.is_horizontal and
                    abs(curr_price - nxt_price) < atr_int * 0.5 and
                    curr.age_candles > nxt.age_candles
                ),
                'B6_LINE_SANDWICH': (
                    curr.is_horizontal and nxt.is_horizontal and
                    min(curr_price, nxt_price) < context.get('price_int', 0) < max(curr_price, nxt_price)
                ),
                'B7_DOUBLE_TOUCH': (
                    curr.touch_count >= 1 and nxt.touch_count >= 1 and
                    abs(curr.age_candles - nxt.age_candles) <= 5
                ),
                'B8_CASCADE_BREAK': (
                    getattr(curr, 'status', '') == 'BROKEN' and
                    getattr(nxt, 'status', '') == 'BROKEN' and
                    abs(curr.age_candles - nxt.age_candles) <= 3
                ),
                'B9_LINE_CLUSTER': (
                    len([l for l in active if getattr(l, 'is_horizontal', False)]) >= 3
                ),
                'B10_ALTERNATING_HOLD': (
                    curr.is_horizontal and nxt.is_horizontal and
                    curr.touch_count >= 2 and nxt.touch_count >= 2 and
                    abs(curr_price - nxt_price) > atr_int * 0.5
                ),
            }
            for pid, cond in checks.items():
                try:
                    if cond:
                        detected.append(self._build_instance(
                            pid, curr, context,
                            extra_line_ids=[getattr(nxt, 'line_id', '')]
                        ))
                except Exception:
                    continue
        return detected

    def detect_cross_tf_patterns(self, lines_by_tf: dict, context: dict) -> List[PatternInstance]:
        """Category C: Cross-Timeframe Patterns (8 detectors)."""
        detected = []
        tfs = ['H4', 'H1', 'M15', 'M5']
        tf_lines = {}
        for tf in tfs:
            tf_lines[tf] = [l for l in lines_by_tf.get(tf, [])
                            if getattr(l, 'status', '') == 'ACTIVE']

        h1_dirs = {getattr(l, 'direction', '') for l in tf_lines.get('H1', [])}
        m15_dirs = {getattr(l, 'direction', '') for l in tf_lines.get('M15', [])}
        m5_dirs = {getattr(l, 'direction', '') for l in tf_lines.get('M5', [])}

        all_aligned = (len(h1_dirs) == 1 and h1_dirs == m15_dirs == m5_dirs and len(h1_dirs) > 0)
        h1_m15_conflict = (len(h1_dirs) > 0 and len(m5_dirs) > 0 and h1_dirs != m5_dirs)

        # Get primary line for context
        primary = None
        for tf in tfs:
            if tf_lines.get(tf):
                primary = tf_lines[tf][0]
                break
        if primary is None:
            return detected

        checks = {
            'C1_TF_ALIGNMENT': all_aligned,
            'C2_TF_CONFLICT': h1_m15_conflict,
            'C3_MACRO_HOLD_MICRO_PULL': (
                len(tf_lines.get('H1', [])) > 0 and
                len(tf_lines.get('M5', [])) > 0 and
                'LONG' in h1_dirs and 'SHORT' in m5_dirs
            ),
            'C4_MACRO_BREAK_MICRO_HOLD': (
                any(getattr(l, 'status', '') == 'BROKEN' for l in tf_lines.get('H1', [])) and
                len(tf_lines.get('M5', [])) > 0
            ),
            'C5_FRACTAL_STAIR': (
                len(tf_lines.get('H4', [])) > 0 and
                len(tf_lines.get('H1', [])) > 0 and
                len(tf_lines.get('M15', [])) > 0 and
                all(getattr(l, 'is_horizontal', False)
                    for tf in ['H4', 'H1', 'M15']
                    for l in tf_lines.get(tf, [])[:1])
            ),
            'C6_TIME_COMPRESSION': (
                sum(1 for tf in tfs for l in tf_lines.get(tf, [])
                    if getattr(l, 'is_horizontal', False)) >= 3
            ),
            'C7_TIME_EXPANSION': (
                sum(1 for tf in tfs for l in tf_lines.get(tf, [])
                    if not getattr(l, 'is_horizontal', False)) >= 3
            ),
            'C8_ECHO_PATTERN': (
                len(tf_lines.get('H1', [])) > 0 and
                len(tf_lines.get('M15', [])) > 0 and
                getattr(tf_lines['H1'][0], 'is_horizontal', False) ==
                getattr(tf_lines['M15'][0], 'is_horizontal', False)
            ),
        }

        for pid, cond in checks.items():
            try:
                if cond:
                    line_ids = []
                    for tf in tfs:
                        for l in tf_lines.get(tf, [])[:1]:
                            lid = getattr(l, 'line_id', '')
                            if lid:
                                line_ids.append(lid)
                    detected.append(self._build_instance(
                        pid, primary, context, extra_line_ids=line_ids
                    ))
            except Exception:
                continue
        return detected

    def detect_temporal_patterns(self, line_history: list, context: dict) -> List[PatternInstance]:
        """Category D: Temporal Patterns (8 detectors).

        Args:
            line_history: list of personality snapshots for SAME line over time
        """
        detected = []
        if len(line_history) < 3:
            return detected

        latest = line_history[-1]
        prev = line_history[-2]

        checks = {
            'D1_SLOW_BUILD': (
                latest.age_candles > 20 and
                all(abs(line_history[i].slope_quality - line_history[i-1].slope_quality) < 5
                    for i in range(1, len(line_history)))
            ),
            'D2_FAST_EXHAUST': (
                latest.slope_quality < 40 and prev.slope_quality > 60 and latest.age_candles < 10
            ),
            'D3_AGING_GRACEFULLY': (
                latest.age_candles > 50 and latest.touch_count >= 5 and latest.slope_quality > 60
            ),
            'D4_PREMATURE_DEATH': (
                getattr(latest, 'status', '') == 'BROKEN' and latest.age_candles < 10
            ),
            'D5_RESURRECTION': (
                len(line_history) >= 4 and
                getattr(line_history[-3], 'status', '') == 'BROKEN' and
                getattr(latest, 'status', '') == 'ACTIVE' and
                abs(latest.price_int - line_history[-3].price_int) < context.get('atr_int', 999999)
            ),
            'D6_OSCILLATING_SLOPE': (
                len(line_history) >= 4 and
                sum(1 for i in range(1, len(line_history))
                    if line_history[i].is_horizontal != line_history[i-1].is_horizontal) >= 3
            ),
            'D7_CONSISTENT_TOUCH': (
                latest.touch_count >= 3 and latest.age_candles >= 15 and
                latest.age_candles / max(latest.touch_count, 1) <= 8
            ),
            'D8_ACCELERATING_TOUCH': (
                latest.touch_count >= 3 and
                len(line_history) >= 3 and
                line_history[-1].touch_count > line_history[-2].touch_count > line_history[-3].touch_count
            ),
        }

        for pid, cond in checks.items():
            try:
                if cond:
                    detected.append(self._build_instance(pid, latest, context))
            except Exception:
                continue
        return detected

    def detect_composite_patterns(self, personality, context: dict, tf_alignment: bool = False) -> List[PatternInstance]:
        """Category G: Composite Patterns (7 detectors)."""
        detected = []
        lp = personality
        composites = {
            'G1_GOLDEN_SETUP': (
                80 <= lp.slope_quality <= 100 and lp.age_candles > 20 and
                lp.distance_health == 'OPTIMAL' and tf_alignment
            ),
            'G2_DEATH_SPIRAL': (
                lp.slope_quality < 30 and lp.age_candles < 10 and
                lp.distance_health == 'EXTENDED' and not tf_alignment
            ),
            'G3_SIDEWAY_TRAP': (
                lp.is_horizontal and lp.distance_health == 'OPTIMAL' and lp.velocity_int < 20
            ),
            'G4_BREAKOUT_CHARGE': (
                lp.is_horizontal and lp.age_candles > 10 and
                lp.distance_health == 'OPTIMAL' and context.get('volume_spike', False)
            ),
            'G5_EXHAUSTION_REV': (
                lp.slope_quality < 30 and lp.distance_health == 'EXTENDED' and lp.age_candles > 30
            ),
            'G6_HEALTHY_PULLBACK': (
                40 < lp.slope_quality < 80 and lp.distance_health == 'OPTIMAL' and lp.touch_count >= 2
            ),
            'G7_SILENT_ACCUM': (
                lp.is_horizontal and lp.touch_count >= 3 and lp.age_candles > 15 and lp.velocity_int < 30
            ),
        }
        for pid, cond in composites.items():
            try:
                if cond:
                    detected.append(self._build_instance(pid, lp, context))
            except Exception:
                continue
        return detected

    # ─── Helpers ────────────────────────────────────────────────────

    def _build_instance(self, pid: str, personality, context: dict,
                        extra_line_ids: list = None, symbol: str = "") -> PatternInstance:
        """Build PatternInstance with deterministic hash."""
        cat = pid.split('_')[0]
        name = '_'.join(pid.split('_', 1)[1:])
        phash = self._gen_hash(pid, personality, context)
        line_ids = [personality.line_id] if personality.line_id else []
        if extra_line_ids:
            line_ids.extend([lid for lid in extra_line_ids if lid])
        symbol = symbol or context.get('symbol', '')
        return PatternInstance(
            pattern_id=pid, category=cat, pattern_name=name, pattern_hash=phash,
            timeframe=context.get('timeframe', ''), line_ids=line_ids,
            slope_quality=personality.slope_quality,
            distance_health=personality.distance_health,
            age_at_detection=personality.age_candles,
            strength_at_detection=personality.touch_count,
            market_price_int=context.get('price_int', 0),
            atr_at_detection_int=context.get('atr_int', 0),
            timestamp=context.get('timestamp', ''),
            instance_id=generate_pattern_instance_id(pid, symbol),
        )

    @staticmethod
    def _gen_hash(pattern_id: str, personality, context: dict) -> str:
        """Deterministic hash for pattern matching."""
        features = {
            'pid': pattern_id,
            'tf': context.get('timeframe', ''),
            'slope_bucket': PatternMiner._bucketize(
                personality.slope_quality, [0, 15, 30, 45, 60, 90]
            ),
            'dist': personality.distance_health,
            'age_bucket': PatternMiner._bucketize(
                personality.age_candles, [0, 5, 10, 20, 50, 999]
            ),
            'str_bucket': PatternMiner._bucketize(
                personality.touch_count, [0, 1, 3, 5, 10]
            ),
        }
        raw = json.dumps(features, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _bucketize(value: float, buckets: list) -> int:
        """Bucketize a value into discrete categories."""
        for i, threshold in enumerate(buckets):
            if value < threshold:
                return i
        return len(buckets)

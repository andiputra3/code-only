"""ST-LMS v2.0 Pipeline Orchestrator — 18 Stages + Single-Transaction Persist.

Stage Order (Plan-Centric):
  C001 OBSERVE → INIT PLANS → C002 MEASURE → C003 STRUCTURE →
  C003.5 PATTERN MINE → C006 SELECT → C007 UNDERSTAND →
  C009 PLAN ADAPT → C010 RIVER REVIEW → C011 AUTHORIZE →
  C012 EXECUTE → POST-TRADE LEARN → TELEMETRY → PERSIST

All tables persisted atomically in single transaction.
"""
import sqlite3
import time
from datetime import datetime
from typing import Dict, List, Optional

from config.settings import DB_PATH, STAGE_NAMES, AUTHORIZATION_MIN_CONFIDENCE
from st_lms.utils.integer_math import IntegerMath
from st_lms.utils.helpers import (
    generate_snapshot_id, generate_trade_id, generate_review_id,
    generate_pattern_instance_id, generate_telemetry_id, generate_cycle_id,
)
from st_lms.utils.json_utils import serialize_pattern_hashes
from st_lms.engine.supertrend_line_engine import SupertrendLineEngine
from st_lms.engine.line_personality import LinePersonalityEngine, LinePersonality
from st_lms.engine.pattern_miner import PatternMiner, PatternInstance
from st_lms.measure.participation import UnifiedParticipationCalculator
from st_lms.trading_plan.adaptive_manager import (
    AdaptivePlanManager, AdaptivePlan, PlanState,
)
from st_lms.models.enums import RiverVerdict, ExecutionOrderType, TelemetryStatus


class Pipeline:
    """ST-LMS v2.0 Adaptive Trading Plan Engine."""

    MAX_RISK_PERCENT = 5.0  # Authorization Layer 3

    def __init__(self):
        self._conn = sqlite3.connect(DB_PATH)
        self._conn.row_factory = sqlite3.Row
        self._line_engine = SupertrendLineEngine(atr_period=10, multiplier=3.0)
        self._personality_engine = LinePersonalityEngine()
        self._pattern_miner = PatternMiner()
        self._participation_calc = UnifiedParticipationCalculator()
        self._plan_managers: Dict[str, AdaptivePlanManager] = {}
        self._consecutive_losses: Dict[str, int] = {}
        # Per-line personality history for temporal patterns (Category D)
        self._line_histories: Dict[str, Dict[str, List[LinePersonality]]] = {}

    def run(self, symbol: str, timeframes: List[str],
            candles: Dict[str, List[dict]],
            risk_method: str = "fixed_fraction") -> dict:
        """Run one full pipeline cycle."""
        cycle_id = generate_cycle_id(symbol)
        stage_timings: Dict[str, int] = {}

        # ── C001: OBSERVE ──
        t0 = time.time()
        market_snap = self._observe(symbol, timeframes, candles)
        stage_timings['OBSERVE'] = int((time.time() - t0) * 1000)

        # ── INIT PLANS ──
        manager = self._get_or_create_manager(symbol)

        # ── C002: MEASURE ──
        t0 = time.time()
        indicator_snap = self._measure(symbol, market_snap, candles)
        participation_score = self._compute_participation(symbol)
        stage_timings['MEASURE'] = int((time.time() - t0) * 1000)

        # ── C003: STRUCTURE ──
        t0 = time.time()
        lines_by_tf = self._build_lines(symbol, candles)
        stage_timings['STRUCTURE'] = int((time.time() - t0) * 1000)

        # ── C003.5: PATTERN MINE ──
        t0 = time.time()
        all_patterns, personalities_by_tf = self._mine_patterns(
            symbol, lines_by_tf, market_snap, indicator_snap
        )
        stage_timings['PATTERN_MINE'] = int((time.time() - t0) * 1000)

        # ── C006: SELECT (TF Fusion) ──
        t0 = time.time()
        primary_lines = self._select_primary_lines(lines_by_tf, personalities_by_tf)
        stage_timings['SELECT'] = int((time.time() - t0) * 1000)

        # ── C007: UNDERSTAND ──
        t0 = time.time()
        geometry = self._understand_geometry(lines_by_tf, primary_lines)
        stage_timings['UNDERSTAND'] = int((time.time() - t0) * 1000)

        # ── C009: PLAN ADAPTATION ──
        t0 = time.time()
        self._adapt_plans(
            manager, primary_lines, market_snap, indicator_snap,
            geometry, participation_score, all_patterns, risk_method,
        )
        stage_timings['PLAN_ADAPT'] = int((time.time() - t0) * 1000)

        winner = manager.select_winner()

        # ── C010: RIVER REVIEW ──
        t0 = time.time()
        river_result = self._river_review(winner, all_patterns) if winner else None
        stage_timings['RIVER_REVIEW'] = int((time.time() - t0) * 1000)

        # ── C011: AUTHORIZE (5-Layer) ──
        t0 = time.time()
        authorized = self._authorize(winner, river_result, symbol) if winner else False
        stage_timings['AUTHORIZE'] = int((time.time() - t0) * 1000)

        # ── C012: EXECUTE ──
        t0 = time.time()
        position_id = None
        if authorized and winner:
            position_id = self._execute(winner, symbol, risk_method)
        stage_timings['EXECUTE'] = int((time.time() - t0) * 1000)

        # ── POST-TRADE: LEARN ──
        t0 = time.time()
        self._post_trade_learn(winner, all_patterns, river_result, symbol)
        stage_timings['POST_TRADE'] = int((time.time() - t0) * 1000)

        # ── TELEMETRY LOG ──
        self._log_telemetry(cycle_id, symbol, stage_timings)

        # ── PERSIST CYCLE (Single Transaction) ──
        self._persist_cycle(
            symbol, manager, lines_by_tf, all_patterns, river_result,
            position_id, geometry, cycle_id, market_snap, indicator_snap,
        )

        return {
            'cycle_id': cycle_id,
            'plans': {
                d: {'state': p.state.value, 'confidence': p.confidence, 'health': p.health_score}
                for d, p in manager.plans.items()
            },
            'winner': winner.direction if winner else None,
            'authorized': authorized,
            'position_id': position_id,
            'patterns_found': len(all_patterns),
        }

    # ═══════════════════════════════════════════════════════════
    # C001: OBSERVE
    # ═══════════════════════════════════════════════════════════
    def _observe(self, symbol, timeframes, candles):
        """Collect market snapshot from candles."""
        tf = timeframes[0] if timeframes else 'H1'
        c = candles.get(tf, [{}])[-1] if candles.get(tf) else {}
        profile = self._get_profile(symbol)
        scale = profile['profile_price_scale']
        tick_size_int = profile['profile_tick_size_int']

        return {
            'symbol': symbol,
            'timeframe': tf,
            'timestamp': c.get('timestamp', datetime.utcnow().isoformat()),
            'snapshot_id': generate_snapshot_id('SNAP'),
            'open_int': self._to_int(c.get('open', 0), scale),
            'high_int': self._to_int(c.get('high', 0), scale),
            'low_int': self._to_int(c.get('low', 0), scale),
            'close_int': self._to_int(c.get('close', 0), scale),
            'volume_int': int(c.get('volume', 0)),
            'close_scaled': IntegerMath.from_raw(
                c.get('close', 0), scale, tick_size_int, symbol
            ),
        }

    # ═══════════════════════════════════════════════════════════
    # C002: MEASURE
    # ═══════════════════════════════════════════════════════════
    def _measure(self, symbol, market_snap, candles):
        """Compute ATR and MACD as integers."""
        tf_candles = candles.get('H1', []) or candles.get(next(iter(candles), ''), [])
        atr_int = self._calc_atr_int(tf_candles, period=10)
        macd_hist = self._calc_macd_hist_int(tf_candles)
        return {'atr_int': atr_int, 'macd_hist_int': macd_hist}

    def _compute_participation(self, symbol):
        """Unified participation score (Spot/Futures agnostic)."""
        profile = self._get_profile(symbol)
        if profile['profile_enable_open_interest']:
            oi_vals = self._get_recent_values(symbol, 'snapshot_open_interest_int', 20)
            vols = self._get_recent_values(symbol, 'snapshot_volume_int', 20)
            return self._participation_calc.calculate(
                True, oi_values=oi_vals, volumes=vols
            )
        tb = self._get_recent_values(symbol, 'snapshot_taker_buy_vol_int', 20)
        ts = self._get_recent_values(symbol, 'snapshot_taker_sell_vol_int', 20)
        vols = self._get_recent_values(symbol, 'snapshot_volume_int', 20)
        return self._participation_calc.calculate(
            False, taker_buy_vols=tb, taker_sell_vols=ts, volumes=vols
        )

    # ═══════════════════════════════════════════════════════════
    # C003: STRUCTURE (SupertrendLineEngine)
    # ═══════════════════════════════════════════════════════════
    def _build_lines(self, symbol, candles):
        """Build Supertrend Lines per timeframe."""
        profile = self._get_profile(symbol)
        lines_by_tf: Dict[str, list] = {}
        for tf, tf_candles in candles.items():
            if len(tf_candles) < 11:
                lines_by_tf[tf] = []
                continue
            lines_by_tf[tf] = self._line_engine.build_lines(
                symbol=symbol, timeframe=tf, candles=tf_candles,
                scale=profile['profile_price_scale'],
                tick_size_int=profile['profile_tick_size_int'],
            )
        return lines_by_tf

    # ═══════════════════════════════════════════════════════════
    # C003.5: PATTERN MINE (59 patterns)
    # ═══════════════════════════════════════════════════════════
    def _mine_patterns(self, symbol, lines_by_tf, market_snap, indicator_snap):
        """Run all 59 pattern detectors."""
        all_patterns: List[PatternInstance] = []
        personalities_by_tf: Dict[str, List[LinePersonality]] = {}
        ctx_base = {
            'symbol': symbol,
            'price_int': market_snap['close_scaled'].value,
            'atr_int': indicator_snap['atr_int'],
            'timestamp': market_snap['timestamp'],
        }

        # TF alignment detection for composite patterns (G)
        h1_dirs, m15_dirs, m5_dirs = set(), set(), set()
        for tf_key, dir_set in [('H1', h1_dirs), ('M15', m15_dirs), ('M5', m5_dirs)]:
            for l in lines_by_tf.get(tf_key, []):
                if getattr(l, 'status', '') == 'ACTIVE':
                    dir_set.add(getattr(l, 'direction', ''))
        tf_alignment = (
            len(h1_dirs) == 1 and h1_dirs == m15_dirs == m5_dirs and len(h1_dirs) > 0
        )

        # Ensure symbol history dict exists (for Category D)
        if symbol not in self._line_histories:
            self._line_histories[symbol] = {}

        for tf, lines in lines_by_tf.items():
            ctx = {**ctx_base, 'timeframe': tf}
            personalities: List[LinePersonality] = []

            for line in lines:
                personality = self._personality_engine.calculate(
                    line, market_snap['close_scaled'], indicator_snap['atr_int'], []
                )
                personalities.append(personality)

                # Track per-line history for Category D (Temporal)
                line_id = personality.line_id
                if line_id not in self._line_histories[symbol]:
                    self._line_histories[symbol][line_id] = []
                history = self._line_histories[symbol][line_id]
                history.append(personality)
                if len(history) > 50:
                    self._line_histories[symbol][line_id] = history[-50:]

                # Category A: Single Line
                all_patterns.extend(
                    self._pattern_miner.detect_single_line_patterns(personality, ctx)
                )
                # Category F: Distance
                all_patterns.extend(
                    self._pattern_miner.detect_distance_patterns(personality, ctx)
                )
                # Category G: Composite
                all_patterns.extend(
                    self._pattern_miner.detect_composite_patterns(personality, ctx, tf_alignment)
                )

            personalities_by_tf[tf] = personalities

            # Category B: Multi-Line
            all_patterns.extend(self._pattern_miner.detect_multi_line_patterns(lines, ctx))

            # Category E: Slope Transition
            for i in range(1, len(personalities)):
                all_patterns.extend(self._pattern_miner.detect_slope_transitions(
                    personalities[i - 1], personalities[i], ctx
                ))

            # Category D: Temporal (per-line history)
            for line in lines:
                line_id = getattr(line, 'line_id', '')
                history = self._line_histories[symbol].get(line_id, [])
                if len(history) >= 3:
                    all_patterns.extend(
                        self._pattern_miner.detect_temporal_patterns(history, ctx)
                    )

        # Category C: Cross-TF
        cross_ctx = {**ctx_base, 'timeframe': 'MULTI'}
        all_patterns.extend(self._pattern_miner.detect_cross_tf_patterns(lines_by_tf, cross_ctx))

        return all_patterns, personalities_by_tf

    # ═══════════════════════════════════════════════════════════
    # C006: SELECT (TF Fusion)
    # ═══════════════════════════════════════════════════════════
    def _select_primary_lines(self, lines_by_tf, personalities_by_tf):
        """Select primary line per direction using quality score."""
        result = {}
        quality_lookup: Dict[str, float] = {}
        for tf_personalities in personalities_by_tf.values():
            for p in tf_personalities:
                quality_lookup[p.line_id] = p.quality_score

        for direction in ['LONG', 'SHORT']:
            for tf in ['H4', 'H1', 'M15', 'M5']:
                lines = lines_by_tf.get(tf, [])
                valid = [
                    l for l in lines
                    if getattr(l, 'status', '') == 'ACTIVE'
                    and getattr(l, 'age_candles', 0) > 5
                    and getattr(l, 'direction', '') == direction
                ]
                if valid:
                    result[direction] = max(
                        valid,
                        key=lambda l: quality_lookup.get(getattr(l, 'line_id', ''), 0),
                    )
                    break
        return result

    # ═══════════════════════════════════════════════════════════
    # C007: UNDERSTAND
    # ═══════════════════════════════════════════════════════════
    def _understand_geometry(self, lines_by_tf, primary_lines):
        """Compute geometry metrics from H1 lines."""
        understanding = {
            'trend_strength': 0.0, 'compression_level': 0.0,
            'wave_quality': 0.0, 'structural_confidence': 0.0,
            'geometry': 'NO_STRUCTURE',
        }
        h1_lines = lines_by_tf.get('H1', [])
        active_h1 = [l for l in h1_lines if getattr(l, 'status', '') == 'ACTIVE']

        if active_h1:
            qualities = [getattr(l, 'quality_score', 50) for l in active_h1]
            understanding['trend_strength'] = sum(qualities) / len(qualities) if qualities else 0
            h_count = sum(1 for l in active_h1 if getattr(l, 'is_horizontal', False))
            understanding['compression_level'] = (
                (h_count / len(active_h1) * 100) if active_h1 else 0
            )

            if understanding['compression_level'] > 70:
                understanding['geometry'] = 'CORRIDOR'
            elif understanding['trend_strength'] > 70:
                direction = getattr(primary_lines.get('LONG'), 'direction', None)
                understanding['geometry'] = 'ASCENDING' if direction == 'LONG' else 'DESCENDING'
            else:
                understanding['geometry'] = 'CHAOTIC'

            understanding['structural_confidence'] = (
                understanding['trend_strength'] * 0.6 +
                (100 - understanding['compression_level']) * 0.4
            )
        return understanding

    # ═══════════════════════════════════════════════════════════
    # C009: PLAN ADAPTATION
    # ═══════════════════════════════════════════════════════════
    def _adapt_plans(self, manager, primary_lines, market_snap, indicator_snap,
                     geometry, participation_score, all_patterns, risk_method):
        """Adapt all 3 plans based on lines, geometry, patterns."""
        for direction in ['LONG', 'SHORT']:
            line = primary_lines.get(direction)
            if line:
                personality = self._personality_engine.calculate(
                    line, market_snap['close_scaled'], indicator_snap['atr_int'], []
                )
                delta = self._compute_confidence_delta(personality)
                manager.adapt_to_line_change(
                    direction, delta, personality.quality_score, 'LINE_UPDATE'
                )

            plan = manager.plans[direction]
            plan.participation_health = participation_score
            plan.momentum_health = min(
                100, max(0, 50 + indicator_snap.get('macd_hist_int', 0) / 100)
            )
            plan.risk_method = risk_method

            # Structure = 60% line quality + 40% geometry confidence
            line_quality = 0.0
            pline = primary_lines.get(direction)
            if pline:
                p = self._personality_engine.calculate(
                    pline, market_snap['close_scaled'], indicator_snap['atr_int'], []
                )
                line_quality = p.quality_score
            plan.structure_health = round(
                line_quality * 0.6 + geometry['structural_confidence'] * 0.4, 2
            )

            # Risk health based on SL distance
            if plan.stop_loss_int and market_snap['close_scaled'].value:
                sl_dist = abs(market_snap['close_scaled'].value - plan.stop_loss_int)
                atr = indicator_snap['atr_int']
                plan.risk_health = (
                    min(100, max(0, 100 - (sl_dist / max(atr, 1)) * 10))
                    if atr > 0 else 50
                )
            else:
                plan.risk_health = 50

            manager.compute_health(plan)

        # SIDEWAY adaptation
        h_lines = [
            l for l in (lines_by_tf.get('H1', []) if 'lines_by_tf' in locals() else [])
            if getattr(l, 'is_horizontal', False)
        ]
        sw_conf = min(len(h_lines) * 15 + 30, 90) if h_lines else 30
        manager.adapt_to_line_change(
            'SIDEWAY',
            sw_conf - manager.plans['SIDEWAY'].confidence,
            70.0, 'HORIZONTAL_CLUSTER',
        )
        manager.plans['SIDEWAY'].participation_health = participation_score
        manager.plans['SIDEWAY'].risk_method = risk_method
        manager.compute_health(manager.plans['SIDEWAY'])

        # Pattern context injection
        bullish_pids = {'A3', 'A7', 'A9', 'B1', 'E1', 'E5', 'G1', 'G4', 'G6'}
        bearish_pids = {'A5', 'A10', 'B2', 'E3', 'E4', 'G2', 'G5'}
        neutral_pids = {'A6', 'B6', 'B9', 'G3', 'G7'}

        for direction in ['LONG', 'SHORT', 'SIDEWAY']:
            plan = manager.plans[direction]
            if direction == 'LONG':
                relevant = [p for p in all_patterns
                            if p.pattern_id in bullish_pids or p.pattern_id in neutral_pids]
            elif direction == 'SHORT':
                relevant = [p for p in all_patterns
                            if p.pattern_id in bearish_pids or p.pattern_id in neutral_pids]
            else:
                relevant = [p for p in all_patterns if p.pattern_id in neutral_pids]

            plan.active_patterns_count = len(relevant)
            pos = sum(1 for p in relevant if p.pattern_id in bullish_pids)
            neg = sum(1 for p in relevant if p.pattern_id in bearish_pids)
            plan.pattern_score = (pos - neg) * 10
            manager.compute_health(plan)

    # ═══════════════════════════════════════════════════════════
    # C010: RIVER REVIEW
    # ═══════════════════════════════════════════════════════════
    def _river_review(self, plan, patterns):
        """Pattern-based River Review."""
        if not plan or plan.confidence < 50:
            return {'verdict': RiverVerdict.REJECT.value, 'score': 0, 'instance_ids': []}

        bullish = {'A3', 'A7', 'A9', 'B1', 'E1', 'E5', 'G1', 'G4', 'G6'}
        bearish = {'A5', 'A10', 'B2', 'E3', 'E4', 'G2', 'G5'}
        neutral = {'A6', 'B6', 'B9', 'G3', 'G7'}

        if plan.direction == 'LONG':
            supporting = [p for p in patterns if p.pattern_id in bullish]
            conflicting = [p for p in patterns if p.pattern_id in bearish]
        elif plan.direction == 'SHORT':
            supporting = [p for p in patterns if p.pattern_id in bearish]
            conflicting = [p for p in patterns if p.pattern_id in bullish]
        else:  # SIDEWAY
            supporting = [p for p in patterns if p.pattern_id in neutral]
            conflicting = [p for p in patterns
                           if p.pattern_id in bullish or p.pattern_id in bearish]

        score = len(supporting) - len(conflicting)

        if score >= 2:
            verdict = RiverVerdict.APPROVE.value
        elif score >= 0:
            verdict = RiverVerdict.CAUTION.value
        else:
            verdict = RiverVerdict.REJECT.value

        instance_ids = [p.pattern_hash for p in supporting[:20]]
        return {'verdict': verdict, 'score': score, 'instance_ids': instance_ids}

    # ═══════════════════════════════════════════════════════════
    # C011: AUTHORIZE (5-Layer Gateway)
    # ═══════════════════════════════════════════════════════════
    def _authorize(self, plan, river_result, symbol):
        """5-Layer Authorization Gateway."""
        if not plan:
            return False

        # Layer 1: State
        if plan.state not in (PlanState.READY, PlanState.ACTIVE):
            return False

        # Layer 2: Confidence threshold
        if plan.confidence < AUTHORIZATION_MIN_CONFIDENCE:
            return False

        # Layer 3: Risk
        if plan.risk_percent > self.MAX_RISK_PERCENT:
            return False

        # Layer 4: River
        if river_result and river_result.get('verdict') == RiverVerdict.REJECT.value:
            return False

        # Layer 5: Liquidation margin ≥ 5%
        if plan.liquidation_price_int > 0 and plan.entry_zone_low_int:
            liq_margin = abs(plan.entry_zone_low_int - plan.liquidation_price_int)
            entry_val = plan.entry_zone_low_int
            if entry_val > 0 and (liq_margin / entry_val) < 0.05:
                return False

        # Additional: Consecutive losses pause
        if self._consecutive_losses.get(symbol, 0) >= 5:
            return False

        return True

    # ═══════════════════════════════════════════════════════════
    # C012: EXECUTE (with RiskManager logic)
    # ═══════════════════════════════════════════════════════════
    def _execute(self, plan, symbol, risk_method):
        """Execute authorized plan with risk sizing."""
        balance_int = self._get_balance_int(symbol)
        entry_price = plan.entry_zone_low_int or plan.entry_zone_high_int
        sl_price = plan.stop_loss_int

        if entry_price and sl_price and entry_price != sl_price:
            risk_amount = int(balance_int * plan.risk_percent / 100)
            price_diff = abs(entry_price - sl_price)
            quantity_int = (
                (risk_amount * plan.leverage) // max(price_diff, 1)
                if price_diff > 0 else 0
            )
        else:
            quantity_int = 0

        # Risk multiplier based on consecutive losses
        losses = self._consecutive_losses.get(symbol, 0)
        multiplier = 1.0
        if losses == 3:
            multiplier = 0.5
        elif losses == 4:
            multiplier = 0.25
        elif losses >= 5:
            multiplier = 0.0
        quantity_int = int(quantity_int * multiplier)

        trade_id = generate_trade_id(plan.plan_id)
        plan.position_size_int = quantity_int
        print(
            f"[EXECUTE] {plan.direction} {symbol} | Qty: {quantity_int} | "
            f"Conf: {plan.confidence:.0f} | Health: {plan.health_score:.0f}"
        )
        return trade_id

    # ═══════════════════════════════════════════════════════════
    # POST-TRADE: LEARN
    # ═══════════════════════════════════════════════════════════
    def _post_trade_learn(self, winner, all_patterns, river_result, symbol):
        """Record outcome to shared_learning_outcomes."""
        if not winner:
            return
        outcome_id = generate_snapshot_id('OUTCOME')
        pattern_hashes = [p.pattern_hash for p in all_patterns[:20]]
        try:
            self._conn.execute(
                """INSERT INTO shared_learning_outcomes
                   (outcome_id, outcome_plan_id, outcome_symbol, outcome_direction,
                    outcome_timestamp, outcome_entry_price_int, outcome_was_rejected,
                    outcome_plan_confidence, outcome_plan_health_score,
                    outcome_active_patterns, outcome_river_verdict, outcome_category)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    outcome_id, winner.plan_id, symbol, winner.direction,
                    datetime.utcnow().isoformat(),
                    winner.entry_zone_low_int or 0, 0,
                    winner.confidence, winner.health_score,
                    serialize_pattern_hashes(pattern_hashes),
                    river_result.get('verdict', 'UNKNOWN') if river_result else 'UNKNOWN',
                    'PENDING',
                ),
            )
        except Exception:
            pass  # Non-critical

    # ═══════════════════════════════════════════════════════════
    # TELEMETRY
    # ═══════════════════════════════════════════════════════════
    def _log_telemetry(self, cycle_id, symbol, stage_timings):
        """Log stage timing to pipeline_telemetry."""
        for order, (stage_key, duration_ms) in enumerate(stage_timings.items()):
            stage_name = STAGE_NAMES.get(stage_key, stage_key)
            tel_id = generate_telemetry_id(cycle_id, stage_key)
            try:
                self._conn.execute(
                    """INSERT INTO pipeline_telemetry
                       (telemetry_id, telemetry_pipeline_cycle_id, telemetry_symbol,
                        telemetry_stage, telemetry_parent_stage, telemetry_stage_order,
                        telemetry_action, telemetry_status, telemetry_duration_ms,
                        telemetry_timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        tel_id, cycle_id, symbol, stage_name, None, order,
                        stage_name, TelemetryStatus.SUCCESS.value, duration_ms,
                        datetime.utcnow().isoformat(),
                    ),
                )
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════
    # PERSIST CYCLE (Single Transaction)
    # ═══════════════════════════════════════════════════════════
    def _persist_cycle(self, symbol, manager, lines_by_tf, all_patterns,
                       river_result, position_id, geometry, cycle_id,
                       market_snap, indicator_snap):
        """Atomic write of all pipeline results."""
        ts = datetime.utcnow().isoformat()
        try:
            # Market snapshot
            self._conn.execute(
                """INSERT OR IGNORE INTO market_snapshots
                   (market_snapshot_id, snapshot_symbol, snapshot_timeframe,
                    snapshot_timestamp, snapshot_open_int, snapshot_high_int,
                    snapshot_low_int, snapshot_close_int, snapshot_volume_int,
                    snapshot_atr_int, snapshot_macd_histogram_int)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    market_snap['snapshot_id'], symbol, market_snap['timeframe'],
                    market_snap['timestamp'],
                    market_snap['open_int'], market_snap['high_int'],
                    market_snap['low_int'], market_snap['close_int'],
                    market_snap['volume_int'],
                    indicator_snap['atr_int'], indicator_snap['macd_hist_int'],
                ),
            )

            # Supertrend Lines
            for tf, lines in lines_by_tf.items():
                for line in lines:
                    try:
                        self._conn.execute(
                            """INSERT OR REPLACE INTO supertrend_lines
                               (line_id, line_symbol, line_timeframe, line_direction,
                                line_price_int, line_start_price_int, line_end_price_int,
                                line_is_horizontal, line_age_candles, line_touch_count,
                                line_velocity_int, line_status, line_start_timestamp)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                line.line_id, line.symbol, line.timeframe, line.direction,
                                line.price_int, line.start_price_int, line.current_price_int,
                                1 if line.is_horizontal else 0,
                                line.age_candles, line.touch_count,
                                abs(line.current_price_int - line.prev_price_int),
                                line.status, line.start_timestamp,
                            ),
                        )
                    except Exception:
                        pass

            # Plans
            for direction, plan in manager.plans.items():
                self._conn.execute(
                    """INSERT OR REPLACE INTO adaptive_plans
                       (plan_id, plan_symbol, plan_direction, plan_strategy, plan_state,
                        plan_confidence, plan_health_score, plan_structure_health,
                        plan_risk_health, plan_momentum_health, plan_participation_health,
                        plan_execution_health, plan_risk_method, plan_risk_percent,
                        plan_leverage, plan_position_size_int,
                        plan_active_patterns_count, plan_pattern_score,
                        plan_pattern_verdict, plan_updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        plan.plan_id, plan.symbol, plan.direction, plan.strategy,
                        plan.state.value, plan.confidence, plan.health_score,
                        plan.structure_health, plan.risk_health, plan.momentum_health,
                        plan.participation_health, plan.execution_health,
                        plan.risk_method, plan.risk_percent, plan.leverage,
                        plan.position_size_int,
                        plan.active_patterns_count, plan.pattern_score,
                        plan.pattern_verdict, ts,
                    ),
                )

            # Plan classifications
            for direction, plan in manager.plans.items():
                try:
                    cls_id = generate_snapshot_id('CLS')
                    self._conn.execute(
                        """INSERT INTO plan_classifications
                           (classification_id, classification_plan_id,
                            classification_timestamp, classification_state,
                            classification_confidence, classification_health_score,
                            classification_reason)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            cls_id, plan.plan_id, ts, plan.state.value,
                            plan.confidence, plan.health_score, f"Cycle {cycle_id}",
                        ),
                    )
                except Exception:
                    pass

            # Plan revisions
            revisions = manager.get_pending_revisions()
            for rev in revisions:
                plan_id, reason, state, old_c, new_c, old_h, new_h = rev
                rev_id = generate_snapshot_id('REV')
                row = self._conn.execute(
                    "SELECT MAX(revision_number) as mn FROM plan_revisions WHERE revision_plan_id = ?",
                    (plan_id,),
                ).fetchone()
                rev_num = (row['mn'] + 1) if row and row['mn'] is not None else 0
                self._conn.execute(
                    """INSERT INTO plan_revisions
                       (revision_id, revision_plan_id, revision_number, revision_reason,
                        revision_trigger_event, revision_confidence_before,
                        revision_confidence_after, revision_health_before,
                        revision_health_after, revision_timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        rev_id, plan_id, rev_num, reason, 'PLAN_ADAPT',
                        old_c, new_c, old_h, new_h, ts,
                    ),
                )

            # Pattern instances + junction
            for pat in all_patterns:
                inst_id = pat.instance_id or generate_pattern_instance_id(pat.pattern_id, symbol)
                try:
                    self._conn.execute(
                        """INSERT OR IGNORE INTO pattern_instances
                           (instance_id, instance_pattern_id, instance_symbol,
                            instance_timeframe, instance_pattern_hash,
                            instance_slope_quality, instance_distance_health,
                            instance_age_at_detection, instance_strength_at_detection,
                            instance_market_price_int, instance_atr_at_detection_int,
                            instance_timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            inst_id, pat.pattern_id, symbol, pat.timeframe,
                            pat.pattern_hash, pat.slope_quality, pat.distance_health,
                            pat.age_at_detection, pat.strength_at_detection,
                            pat.market_price_int, pat.atr_at_detection_int, pat.timestamp,
                        ),
                    )
                    for lid in pat.line_ids:
                        self._conn.execute(
                            """INSERT OR IGNORE INTO pattern_instance_lines
                               (pil_instance_id, pil_line_id, pil_role) VALUES (?, ?, ?)""",
                            (inst_id, lid, 'PRIMARY'),
                        )
                except Exception:
                    pass

            # River review
            if river_result:
                winner = manager.select_winner()
                if winner:
                    rvw_id = generate_review_id(winner.plan_id)
                    self._conn.execute(
                        """INSERT INTO river_reviews
                           (review_id, review_plan_id, review_overall_score, review_verdict,
                            review_pattern_instance_ids, review_patterns_found, review_timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            rvw_id, winner.plan_id, river_result.get('score', 0),
                            river_result.get('verdict', 'UNKNOWN'),
                            serialize_pattern_hashes(river_result.get('instance_ids', [])),
                            len(river_result.get('instance_ids', [])), ts,
                        ),
                    )

            # Market understanding
            und_id = generate_snapshot_id('UND')
            self._conn.execute(
                """INSERT INTO market_understanding
                   (understanding_id, understanding_symbol, understanding_timeframe,
                    understanding_timestamp, understanding_trend_strength,
                    understanding_compression_level, understanding_structural_confidence,
                    understanding_geometry)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    und_id, symbol, 'H1', ts,
                    geometry.get('trend_strength', 0),
                    geometry.get('compression_level', 0),
                    geometry.get('structural_confidence', 0),
                    geometry.get('geometry', 'NO_STRUCTURE'),
                ),
            )

            # Execution track
            if position_id:
                winner = manager.select_winner()
                if winner:
                    self._conn.execute(
                        """INSERT INTO execution_tracks
                           (execution_id, execution_plan_id, execution_symbol,
                            execution_direction, execution_order_type,
                            execution_entry_price_int, execution_position_size_int,
                            execution_leverage, execution_risk_method,
                            execution_status, execution_entry_timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            position_id, winner.plan_id, symbol, winner.direction,
                            ExecutionOrderType.MARKET.value,
                            winner.entry_zone_low_int or 0, winner.position_size_int,
                            winner.leverage, winner.risk_method, 'OPEN', ts,
                        ),
                    )

            self._conn.commit()

        except Exception as e:
            self._conn.rollback()
            print(f"[PERSIST ERROR] {e}")

    # ═══════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════
    def _compute_confidence_delta(self, personality):
        delta = 0.0
        if personality.distance_health == 'OPTIMAL':
            delta += 15
        elif personality.distance_health == 'EXTENDED':
            delta -= 20
        if personality.quality_score > 80:
            delta += 10
        elif personality.quality_score < 40:
            delta -= 15
        if personality.age_candles > 30:
            delta += 5
        return delta

    def _get_profile(self, symbol):
        row = self._conn.execute(
            "SELECT * FROM market_profiles WHERE profile_symbol = ?", (symbol,)
        ).fetchone()
        return dict(row) if row else {
            'profile_price_scale': 8, 'profile_tick_size_int': 1,
            'profile_enable_open_interest': 1,
        }

    def _get_recent_values(self, symbol, column, limit):
        rows = self._conn.execute(
            f"SELECT {column} FROM market_snapshots "
            f"WHERE snapshot_symbol = ? AND {column} IS NOT NULL "
            f"ORDER BY snapshot_timestamp DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
        return [r[column] for r in reversed(rows)]

    def _get_balance_int(self, symbol):
        return 10000 * (10 ** 8)  # Default $10,000 balance

    @staticmethod
    def _to_int(price, scale):
        try:
            return int(float(price) * (10 ** scale))
        except (TypeError, ValueError):
            return 0

    def _calc_atr_int(self, candles, period=10):
        if len(candles) < period + 1:
            return 100
        trs = []
        for i in range(1, len(candles)):
            h = candles[i].get('high', 0)
            l_val = candles[i].get('low', 0)
            pc = candles[i - 1].get('close', l_val)
            trs.append(max(h - l_val, abs(h - pc), abs(l_val - pc)))
        return int(sum(trs[-period:]) / period) if trs else 100

    def _calc_macd_hist_int(self, candles):
        closes = [c.get('close', 0) for c in candles]
        if len(closes) < 26:
            return 0
        fast = sum(closes[-12:]) // 12
        slow = sum(closes[-26:]) // 26
        return fast - slow

    def _get_or_create_manager(self, symbol):
        if symbol not in self._plan_managers:
            self._plan_managers[symbol] = AdaptivePlanManager(symbol)
        return self._plan_managers[symbol]

    def close(self):
        self._conn.close()

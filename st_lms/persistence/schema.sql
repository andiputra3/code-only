-- =====================================================================
-- ST-LMS v2.0 FINAL DATABASE SCHEMA
-- Strict Entity Prefixing | Integer Prices | Event Store
-- 22 Tables + 3 Views
-- =====================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

-- =====================================================================
-- 1. MARKET PROFILES (Spot/Futures Abstraction)
-- =====================================================================
CREATE TABLE IF NOT EXISTS market_profiles (
    profile_symbol TEXT PRIMARY KEY,
    profile_market_type TEXT NOT NULL
        CHECK(profile_market_type IN ('FUTURES_USDM', 'SPOT')),
    profile_enable_open_interest INTEGER NOT NULL DEFAULT 1,
    profile_participation_metric TEXT NOT NULL DEFAULT 'OPEN_INTEREST'
        CHECK(profile_participation_metric IN ('OPEN_INTEREST', 'VOLUME_DELTA')),
    profile_price_scale INTEGER NOT NULL DEFAULT 8,
    profile_tick_size_int INTEGER NOT NULL,
    profile_quantity_scale INTEGER NOT NULL DEFAULT 3,
    profile_is_active INTEGER DEFAULT 1,
    profile_created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    profile_updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- 2. MARKET SNAPSHOTS (Integer Storage)
-- =====================================================================
CREATE TABLE IF NOT EXISTS market_snapshots (
    market_snapshot_id TEXT PRIMARY KEY,
    snapshot_symbol TEXT NOT NULL,
    snapshot_timeframe TEXT NOT NULL,
    snapshot_timestamp TEXT NOT NULL,

    -- OHLCV (Integer)
    snapshot_open_int INTEGER NOT NULL,
    snapshot_high_int INTEGER NOT NULL,
    snapshot_low_int INTEGER NOT NULL,
    snapshot_close_int INTEGER NOT NULL,
    snapshot_volume_int INTEGER NOT NULL,

    -- Participation Metrics (Integer, nullable based on market_type)
    snapshot_open_interest_int INTEGER,
    snapshot_taker_buy_vol_int INTEGER,
    snapshot_taker_sell_vol_int INTEGER,

    -- Indicators (Integer)
    snapshot_atr_int INTEGER NOT NULL,
    snapshot_macd_histogram_int INTEGER,

    FOREIGN KEY (snapshot_symbol) REFERENCES market_profiles(profile_symbol)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshots_unique
    ON market_snapshots(snapshot_symbol, snapshot_timeframe, snapshot_timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_symbol_time
    ON market_snapshots(snapshot_symbol, snapshot_timestamp DESC);

-- =====================================================================
-- 3. SUPERTREND LINES (Horizontal Authority + Personality)
-- =====================================================================
CREATE TABLE IF NOT EXISTS supertrend_lines (
    line_id TEXT PRIMARY KEY,
    line_symbol TEXT NOT NULL,
    line_timeframe TEXT NOT NULL,
    line_direction TEXT NOT NULL CHECK(line_direction IN ('LONG', 'SHORT')),

    -- Price Data (Integer)
    line_price_int INTEGER NOT NULL,
    line_start_price_int INTEGER NOT NULL,
    line_end_price_int INTEGER,

    -- Horizontal Focus
    line_is_horizontal INTEGER NOT NULL DEFAULT 0,

    -- 5 Dimensions of Line Personality
    line_age_candles INTEGER DEFAULT 0,
    line_touch_count INTEGER DEFAULT 0,
    line_velocity_int INTEGER DEFAULT 0,
    line_slope_quality REAL DEFAULT 0,
    line_distance_health TEXT DEFAULT 'NORMAL'
        CHECK(line_distance_health IN ('OPTIMAL', 'NORMAL', 'EXTENDED')),
    line_quality_score REAL DEFAULT 0,

    -- Status
    line_status TEXT NOT NULL CHECK(line_status IN ('ACTIVE', 'BROKEN', 'ARCHIVED')),

    -- Timestamps
    line_start_timestamp TEXT NOT NULL,
    line_end_timestamp TEXT,

    FOREIGN KEY (line_symbol) REFERENCES market_profiles(profile_symbol)
);
CREATE INDEX IF NOT EXISTS idx_lines_symbol_status
    ON supertrend_lines(line_symbol, line_status);
CREATE INDEX IF NOT EXISTS idx_lines_horizontal
    ON supertrend_lines(line_symbol, line_is_horizontal, line_status);
CREATE INDEX IF NOT EXISTS idx_lines_quality
    ON supertrend_lines(line_quality_score DESC);

-- =====================================================================
-- 4. WAVE STRUCTURES (Pattern Category B Storage)
-- =====================================================================
CREATE TABLE IF NOT EXISTS wave_structures (
    wave_id TEXT PRIMARY KEY,
    wave_symbol TEXT NOT NULL,
    wave_timeframe TEXT NOT NULL,
    wave_direction TEXT NOT NULL CHECK(wave_direction IN ('LONG', 'SHORT')),

    -- Wave Boundaries
    wave_start_line_id TEXT NOT NULL,
    wave_end_line_id TEXT,
    wave_start_price_int INTEGER NOT NULL,
    wave_end_price_int INTEGER,

    -- Wave Metrics
    wave_amplitude_int INTEGER DEFAULT 0,
    wave_duration_candles INTEGER DEFAULT 0,
    wave_status TEXT NOT NULL
        CHECK(wave_status IN ('BUILDING', 'ACTIVE', 'COMPLETED', 'ARCHIVED')),

    -- Timestamps
    wave_start_timestamp TEXT NOT NULL,
    wave_end_timestamp TEXT,

    FOREIGN KEY (wave_symbol) REFERENCES market_profiles(profile_symbol),
    FOREIGN KEY (wave_start_line_id) REFERENCES supertrend_lines(line_id),
    FOREIGN KEY (wave_end_line_id) REFERENCES supertrend_lines(line_id)
);
CREATE INDEX IF NOT EXISTS idx_waves_symbol_status
    ON wave_structures(wave_symbol, wave_status);

-- =====================================================================
-- 5. MARKET UNDERSTANDING (C007 Geometry Output)
-- =====================================================================
CREATE TABLE IF NOT EXISTS market_understanding (
    understanding_id TEXT PRIMARY KEY,
    understanding_symbol TEXT NOT NULL,
    understanding_timeframe TEXT NOT NULL,
    understanding_timestamp TEXT NOT NULL,

    -- Geometry Analysis
    understanding_trend_strength REAL DEFAULT 0,
    understanding_compression_level REAL DEFAULT 0,
    understanding_wave_quality REAL DEFAULT 0,
    understanding_structural_confidence REAL DEFAULT 0,
    understanding_geometry TEXT DEFAULT 'NO_STRUCTURE'
        CHECK(understanding_geometry IN (
            'ASCENDING', 'DESCENDING', 'CORRIDOR', 'CONVERGING',
            'DIVERGING', 'CHAOTIC', 'SINGLE_DIRECTION', 'NO_STRUCTURE'
        )),

    -- Links
    understanding_primary_line_id TEXT,
    understanding_candidate_snapshot_id TEXT,
    understanding_parent_snapshot_ids TEXT,

    FOREIGN KEY (understanding_symbol) REFERENCES market_profiles(profile_symbol),
    FOREIGN KEY (understanding_primary_line_id) REFERENCES supertrend_lines(line_id)
);
CREATE INDEX IF NOT EXISTS idx_understanding_symbol_time
    ON market_understanding(understanding_symbol, understanding_timestamp DESC);

-- =====================================================================
-- 6. ADAPTIVE TRADING PLANS (3 Parallel Living Plans)
-- =====================================================================
CREATE TABLE IF NOT EXISTS adaptive_plans (
    plan_id TEXT PRIMARY KEY,
    plan_symbol TEXT NOT NULL,
    plan_direction TEXT NOT NULL
        CHECK(plan_direction IN ('LONG', 'SHORT', 'SIDEWAY')),
    plan_strategy TEXT NOT NULL DEFAULT 'ADAPTIVE'
        CHECK(plan_strategy IN (
            'LONG_ONLY', 'SHORT_ONLY', 'SIDEWAY_ONLY',
            'ADAPTIVE_GRID_SIDEWAY', 'ADAPTIVE'
        )),

    -- Lifecycle
    plan_state TEXT NOT NULL
        CHECK(plan_state IN (
            'OBSERVING', 'BUILDING', 'WAIT_PULLBACK', 'WAIT_BREAKOUT',
            'READY', 'ACTIVE', 'DEFENDING', 'EXITING', 'FINISHED', 'LEARNING'
        )),

    -- Core Metrics
    plan_confidence REAL NOT NULL DEFAULT 0,
    plan_health_score REAL NOT NULL DEFAULT 0,
    plan_revision_count INTEGER DEFAULT 0,

    -- 5 Dimensions of Plan Health (Weighted 35/25/20/15/5)
    plan_structure_health REAL DEFAULT 0,
    plan_risk_health REAL DEFAULT 0,
    plan_momentum_health REAL DEFAULT 0,
    plan_participation_health REAL DEFAULT 0,
    plan_execution_health REAL DEFAULT 0,

    -- Risk Configuration
    plan_risk_method TEXT NOT NULL DEFAULT 'fixed_fraction'
        CHECK(plan_risk_method IN ('fixed_fraction', 'kelly')),
    plan_risk_percent REAL DEFAULT 1.0,
    plan_leverage INTEGER DEFAULT 1,
    plan_position_size_int INTEGER DEFAULT 0,
    plan_funding_cost_estimate REAL DEFAULT 0,
    plan_liquidation_price_int INTEGER DEFAULT 0,

    -- Structure Mapping
    plan_primary_line_id TEXT,
    plan_backup_line_id TEXT,
    plan_entry_zone_low_int INTEGER,
    plan_entry_zone_high_int INTEGER,
    plan_stop_loss_int INTEGER,
    plan_take_profit_int INTEGER,

    -- Pattern Context
    plan_active_patterns_count INTEGER DEFAULT 0,
    plan_pattern_score REAL DEFAULT 0,
    plan_pattern_verdict TEXT DEFAULT 'NEUTRAL'
        CHECK(plan_pattern_verdict IN ('CONFIRM', 'NEUTRAL', 'WARN')),

    -- Timestamps
    plan_created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    plan_updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    plan_activated_at TEXT,
    plan_closed_at TEXT,

    FOREIGN KEY (plan_symbol) REFERENCES market_profiles(profile_symbol),
    FOREIGN KEY (plan_primary_line_id) REFERENCES supertrend_lines(line_id),
    FOREIGN KEY (plan_backup_line_id) REFERENCES supertrend_lines(line_id)
);
CREATE INDEX IF NOT EXISTS idx_plans_symbol_state
    ON adaptive_plans(plan_symbol, plan_state);
CREATE INDEX IF NOT EXISTS idx_plans_health
    ON adaptive_plans(plan_health_score DESC);
CREATE INDEX IF NOT EXISTS idx_plans_active
    ON adaptive_plans(plan_symbol)
    WHERE plan_state NOT IN ('FINISHED', 'LEARNING');

-- =====================================================================
-- 7. PLAN REVISIONS (Audit Trail)
-- =====================================================================
CREATE TABLE IF NOT EXISTS plan_revisions (
    revision_id TEXT PRIMARY KEY,
    revision_plan_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL,

    -- What Changed
    revision_changed_fields TEXT,
    revision_old_values TEXT,
    revision_new_values TEXT,

    -- Why Changed
    revision_reason TEXT,
    revision_trigger_event TEXT,

    -- Impact
    revision_confidence_before REAL,
    revision_confidence_after REAL,
    revision_health_before REAL,
    revision_health_after REAL,

    revision_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (revision_plan_id) REFERENCES adaptive_plans(plan_id)
);
CREATE INDEX IF NOT EXISTS idx_revisions_plan
    ON plan_revisions(revision_plan_id, revision_timestamp DESC);

-- =====================================================================
-- 8. PLAN CLASSIFICATIONS (State Transitions)
-- =====================================================================
CREATE TABLE IF NOT EXISTS plan_classifications (
    classification_id TEXT PRIMARY KEY,
    classification_plan_id TEXT NOT NULL,
    classification_timestamp TEXT NOT NULL,

    -- Classification Result
    classification_state TEXT NOT NULL,
    classification_confidence REAL DEFAULT 0,
    classification_health_score REAL DEFAULT 0,
    classification_reason TEXT,

    -- Input Evidence
    classification_understanding_id TEXT,
    classification_pattern_ids TEXT,

    -- State Transition
    classification_previous_state TEXT,
    classification_transition_trigger TEXT,

    FOREIGN KEY (classification_plan_id) REFERENCES adaptive_plans(plan_id),
    FOREIGN KEY (classification_understanding_id)
        REFERENCES market_understanding(understanding_id)
);
CREATE INDEX IF NOT EXISTS idx_classifications_plan
    ON plan_classifications(classification_plan_id, classification_timestamp DESC);

-- =====================================================================
-- 9. GRID LEVELS (For SIDEWAY Plan)
-- =====================================================================
CREATE TABLE IF NOT EXISTS grid_levels (
    grid_id TEXT PRIMARY KEY,
    grid_plan_id TEXT NOT NULL,
    grid_level_number INTEGER NOT NULL,

    -- Level Definition
    grid_price_int INTEGER NOT NULL,
    grid_size_pct REAL NOT NULL,
    grid_side TEXT NOT NULL CHECK(grid_side IN ('BUY', 'SELL')),

    -- Zone Type
    grid_zone_type TEXT
        CHECK(grid_zone_type IN ('NATIVE_ZONE', 'ATR_INTERPOLATED')),
    grid_confidence REAL DEFAULT 0,

    -- Status
    grid_status TEXT DEFAULT 'PENDING'
        CHECK(grid_status IN ('PENDING', 'FILLED', 'CANCELLED')),
    grid_is_filled INTEGER DEFAULT 0,
    grid_fill_price_int INTEGER,
    grid_fill_timestamp TEXT,

    UNIQUE(grid_plan_id, grid_level_number),
    FOREIGN KEY (grid_plan_id) REFERENCES adaptive_plans(plan_id)
);
CREATE INDEX IF NOT EXISTS idx_grid_plan_status
    ON grid_levels(grid_plan_id, grid_status);

-- =====================================================================
-- 10. PATTERN CATALOG (59 Pattern Definitions)
-- =====================================================================
CREATE TABLE IF NOT EXISTS pattern_catalog (
    pattern_id TEXT PRIMARY KEY,
    pattern_category TEXT NOT NULL
        CHECK(pattern_category IN ('A','B','C','D','E','F','G')),
    pattern_name TEXT NOT NULL,
    pattern_description TEXT,
    pattern_detection_logic TEXT,

    -- Learning Stats
    pattern_total_occurrences INTEGER DEFAULT 0,
    pattern_win_count INTEGER DEFAULT 0,
    pattern_loss_count INTEGER DEFAULT 0,
    pattern_neutral_count INTEGER DEFAULT 0,
    pattern_win_rate REAL DEFAULT 0,
    pattern_avg_profit_atr_int INTEGER DEFAULT 0,
    pattern_avg_loss_atr_int INTEGER DEFAULT 0,

    -- Classification
    pattern_is_predictive INTEGER DEFAULT 0,
    pattern_is_dangerous INTEGER DEFAULT 0,
    pattern_rarity TEXT DEFAULT 'COMMON'
        CHECK(pattern_rarity IN ('COMMON', 'RARE', 'EPIC')),

    pattern_last_updated TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_catalog_category
    ON pattern_catalog(pattern_category);
CREATE INDEX IF NOT EXISTS idx_catalog_win_rate
    ON pattern_catalog(pattern_win_rate DESC);

-- =====================================================================
-- 11. PATTERN INSTANCES (Detected Occurrences)
-- =====================================================================
CREATE TABLE IF NOT EXISTS pattern_instances (
    instance_id TEXT PRIMARY KEY,
    instance_pattern_id TEXT NOT NULL,
    instance_symbol TEXT NOT NULL,
    instance_timeframe TEXT NOT NULL,

    -- Context (Integer)
    instance_pattern_hash TEXT NOT NULL,
    instance_slope_quality REAL,
    instance_distance_health TEXT,
    instance_age_at_detection INTEGER,
    instance_strength_at_detection INTEGER,
    instance_market_price_int INTEGER,
    instance_atr_at_detection_int INTEGER,

    -- Outcome (Filled after fact by River/Darwin)
    instance_outcome TEXT
        CHECK(instance_outcome IS NULL
              OR instance_outcome IN ('WIN', 'LOSS', 'NEUTRAL', 'PENDING')),
    instance_price_move_atr_int INTEGER,
    instance_time_to_outcome_candles INTEGER,

    -- Link to Plan
    instance_plan_id TEXT,

    instance_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (instance_pattern_id) REFERENCES pattern_catalog(pattern_id),
    FOREIGN KEY (instance_plan_id) REFERENCES adaptive_plans(plan_id)
);
CREATE INDEX IF NOT EXISTS idx_instances_hash
    ON pattern_instances(instance_pattern_hash);
CREATE INDEX IF NOT EXISTS idx_instances_outcome
    ON pattern_instances(instance_outcome)
    WHERE instance_outcome IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_instances_symbol_time
    ON pattern_instances(instance_symbol, instance_timestamp DESC);

-- =====================================================================
-- 12. PATTERN INSTANCE LINES (Junction Table)
-- =====================================================================
CREATE TABLE IF NOT EXISTS pattern_instance_lines (
    pil_instance_id TEXT NOT NULL,
    pil_line_id TEXT NOT NULL,
    pil_role TEXT CHECK(pil_role IN ('PRIMARY', 'SECONDARY', 'BOUNDARY')),

    PRIMARY KEY (pil_instance_id, pil_line_id),
    FOREIGN KEY (pil_instance_id) REFERENCES pattern_instances(instance_id)
        ON DELETE CASCADE,
    FOREIGN KEY (pil_line_id) REFERENCES supertrend_lines(line_id)
);
CREATE INDEX IF NOT EXISTS idx_pil_line
    ON pattern_instance_lines(pil_line_id);

-- =====================================================================
-- 13. PATTERN TRANSITIONS (A → B → C)
-- =====================================================================
CREATE TABLE IF NOT EXISTS pattern_transitions (
    transition_id TEXT PRIMARY KEY,
    transition_from_pattern_hash TEXT NOT NULL,
    transition_to_pattern_hash TEXT NOT NULL,

    transition_total_occurrences INTEGER DEFAULT 0,
    transition_win_after_transition INTEGER DEFAULT 0,
    transition_loss_after_transition INTEGER DEFAULT 0,
    transition_win_rate REAL DEFAULT 0,
    transition_avg_candles_between INTEGER DEFAULT 0,

    transition_last_seen TEXT DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(transition_from_pattern_hash, transition_to_pattern_hash)
);
CREATE INDEX IF NOT EXISTS idx_transitions_rate
    ON pattern_transitions(transition_win_rate DESC);

-- =====================================================================
-- 14. SHARED LEARNING OUTCOMES (River v2.0 Knowledge Base)
-- =====================================================================
CREATE TABLE IF NOT EXISTS shared_learning_outcomes (
    outcome_id TEXT PRIMARY KEY,
    outcome_plan_id TEXT NOT NULL,
    outcome_symbol TEXT NOT NULL,
    outcome_direction TEXT NOT NULL,
    outcome_timestamp TEXT NOT NULL,

    -- Trade Outcome
    outcome_entry_price_int INTEGER NOT NULL,
    outcome_exit_price_int INTEGER,
    outcome_pnl_percent REAL,
    outcome_duration_hours REAL,
    outcome_exit_reason TEXT,
    outcome_was_rejected INTEGER DEFAULT 0,

    -- Context at Decision Time
    outcome_plan_confidence REAL,
    outcome_plan_health_score REAL,
    outcome_active_patterns TEXT,
    outcome_river_verdict TEXT,

    -- Learning Tags
    outcome_category TEXT
        CHECK(outcome_category IN (
            'PENDING', 'WIN', 'LOSS',
            'MISSED_OPPORTUNITY', 'CORRECT_REJECTION'
        )),

    FOREIGN KEY (outcome_plan_id) REFERENCES adaptive_plans(plan_id)
);
CREATE INDEX IF NOT EXISTS idx_outcomes_symbol
    ON shared_learning_outcomes(outcome_symbol, outcome_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_outcomes_category
    ON shared_learning_outcomes(outcome_category);
CREATE INDEX IF NOT EXISTS idx_outcomes_rejected
    ON shared_learning_outcomes(outcome_was_rejected)
    WHERE outcome_was_rejected = 1;

-- =====================================================================
-- 15. RIVER REVIEWS (Pattern-Based Review)
-- =====================================================================
CREATE TABLE IF NOT EXISTS river_reviews (
    review_id TEXT PRIMARY KEY,
    review_plan_id TEXT NOT NULL,
    review_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,

    review_patterns_found INTEGER DEFAULT 0,
    review_overall_score REAL DEFAULT 0,
    review_verdict TEXT
        CHECK(review_verdict IN ('APPROVE', 'CAUTION', 'REJECT')),
    review_details TEXT,

    -- Pattern Instance Tracking
    review_pattern_instance_ids TEXT,
    review_understanding_id TEXT,

    FOREIGN KEY (review_plan_id) REFERENCES adaptive_plans(plan_id),
    FOREIGN KEY (review_understanding_id)
        REFERENCES market_understanding(understanding_id)
);
CREATE INDEX IF NOT EXISTS idx_reviews_plan
    ON river_reviews(review_plan_id, review_timestamp DESC);

-- =====================================================================
-- 16. DARWIN OPTIMIZATIONS
-- =====================================================================
CREATE TABLE IF NOT EXISTS darwin_optimizations (
    optimization_id TEXT PRIMARY KEY,
    optimization_parameter_name TEXT NOT NULL,
    optimization_parameter_type TEXT NOT NULL,

    optimization_old_value TEXT,
    optimization_new_value TEXT,

    optimization_performance_before REAL,
    optimization_performance_after REAL,
    optimization_improvement_pct REAL,

    optimization_validation_trades INTEGER DEFAULT 0,
    optimization_is_applied INTEGER DEFAULT 0,

    optimization_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_darwin_applied
    ON darwin_optimizations(optimization_is_applied);
CREATE INDEX IF NOT EXISTS idx_darwin_improvement
    ON darwin_optimizations(optimization_improvement_pct DESC);

-- =====================================================================
-- 17. SYSTEM EVENTS (Event Sourcing)
-- =====================================================================
CREATE TABLE IF NOT EXISTS system_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    event_entity_type TEXT NOT NULL,
    event_entity_id TEXT NOT NULL,

    event_payload TEXT,
    event_priority INTEGER DEFAULT 1
        CHECK(event_priority BETWEEN 1 AND 10),
    event_processed INTEGER DEFAULT 0,

    event_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_events_type_time
    ON system_events(event_type, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_priority
    ON system_events(event_priority DESC, event_processed);
CREATE INDEX IF NOT EXISTS idx_events_entity
    ON system_events(event_entity_type, event_entity_id);

-- =====================================================================
-- 18. PIPELINE TELEMETRY (Stage Timing & Performance)
-- =====================================================================
CREATE TABLE IF NOT EXISTS pipeline_telemetry (
    telemetry_id TEXT PRIMARY KEY,
    telemetry_pipeline_cycle_id TEXT NOT NULL,
    telemetry_symbol TEXT NOT NULL,
    telemetry_stage TEXT NOT NULL,

    -- Nested Stage Support
    telemetry_parent_stage TEXT,
    telemetry_stage_order INTEGER DEFAULT 0,

    telemetry_action TEXT NOT NULL,
    telemetry_status TEXT NOT NULL
        CHECK(telemetry_status IN ('SUCCESS', 'ERROR', 'SKIPPED')),
    telemetry_details TEXT,
    telemetry_duration_ms INTEGER DEFAULT 0,

    telemetry_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_telemetry_cycle
    ON pipeline_telemetry(telemetry_pipeline_cycle_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_stage
    ON pipeline_telemetry(telemetry_stage, telemetry_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_errors
    ON pipeline_telemetry(telemetry_status)
    WHERE telemetry_status = 'ERROR';

-- =====================================================================
-- 19. AUDIT LOG (Data Governance)
-- =====================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id TEXT PRIMARY KEY,
    audit_user_or_system TEXT NOT NULL,
    audit_table_name TEXT NOT NULL,
    audit_operation TEXT NOT NULL
        CHECK(audit_operation IN ('CREATE','READ','UPDATE','DELETE')),

    audit_record_id TEXT,
    audit_before_value TEXT,
    audit_after_value TEXT,

    audit_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_table
    ON audit_log(audit_table_name, audit_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user
    ON audit_log(audit_user_or_system, audit_timestamp DESC);

-- =====================================================================
-- 20. EXECUTION TRACKS (Trade Execution)
-- =====================================================================
CREATE TABLE IF NOT EXISTS execution_tracks (
    execution_id TEXT PRIMARY KEY,
    execution_plan_id TEXT NOT NULL,
    execution_symbol TEXT NOT NULL,
    execution_direction TEXT NOT NULL,

    -- Order Lifecycle
    execution_order_id TEXT,
    execution_order_type TEXT
        CHECK(execution_order_type IN ('MARKET', 'LIMIT', 'STOP', 'OCO')),
    execution_filled_quantity_int INTEGER DEFAULT 0,
    execution_average_fill_price_int INTEGER,
    execution_slippage_int INTEGER DEFAULT 0,

    -- Price & PnL (Integer)
    execution_entry_price_int INTEGER NOT NULL,
    execution_exit_price_int INTEGER,
    execution_position_size_int INTEGER NOT NULL,
    execution_leverage INTEGER NOT NULL DEFAULT 1,
    execution_risk_method TEXT NOT NULL DEFAULT 'fixed_fraction'
        CHECK(execution_risk_method IN ('fixed_fraction', 'kelly')),
    execution_pnl_int INTEGER,
    execution_pnl_percent REAL,

    -- Status
    execution_status TEXT
        CHECK(execution_status IN ('OPEN', 'CLOSED', 'CANCELLED')),
    execution_exit_reason TEXT,

    -- Timestamps
    execution_entry_timestamp TEXT NOT NULL,
    execution_exit_timestamp TEXT,

    FOREIGN KEY (execution_plan_id) REFERENCES adaptive_plans(plan_id)
);
CREATE INDEX IF NOT EXISTS idx_executions_plan
    ON execution_tracks(execution_plan_id);
CREATE INDEX IF NOT EXISTS idx_executions_status
    ON execution_tracks(execution_status);
CREATE INDEX IF NOT EXISTS idx_executions_symbol_time
    ON execution_tracks(execution_symbol, execution_entry_timestamp DESC);

-- =====================================================================
-- 21. BACKTEST RESULTS
-- =====================================================================
CREATE TABLE IF NOT EXISTS backtest_results (
    backtest_id TEXT PRIMARY KEY,
    backtest_symbol TEXT NOT NULL,
    backtest_start_date TEXT NOT NULL,
    backtest_end_date TEXT NOT NULL,
    backtest_strategy TEXT NOT NULL,
    backtest_timeframes TEXT,

    -- Results
    backtest_total_trades INTEGER DEFAULT 0,
    backtest_wins INTEGER DEFAULT 0,
    backtest_losses INTEGER DEFAULT 0,
    backtest_win_rate REAL DEFAULT 0,
    backtest_total_pnl_int INTEGER DEFAULT 0,
    backtest_final_balance_int INTEGER DEFAULT 0,
    backtest_max_drawdown REAL DEFAULT 0,
    backtest_sharpe_ratio REAL DEFAULT 0,
    backtest_rejected_count INTEGER DEFAULT 0,

    backtest_created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_backtest_symbol
    ON backtest_results(backtest_symbol, backtest_created_at DESC);

-- =====================================================================
-- 22. BACKTEST TRADES
-- =====================================================================
CREATE TABLE IF NOT EXISTS backtest_trades (
    trade_id TEXT PRIMARY KEY,
    trade_backtest_id TEXT NOT NULL,
    trade_plan_id TEXT,
    trade_symbol TEXT NOT NULL,
    trade_direction TEXT NOT NULL,

    trade_entry_price_int INTEGER NOT NULL,
    trade_exit_price_int INTEGER,
    trade_quantity_int INTEGER NOT NULL,
    trade_pnl_int INTEGER,
    trade_pnl_percent REAL,
    trade_exit_reason TEXT,

    trade_entry_timestamp TEXT NOT NULL,
    trade_exit_timestamp TEXT,
    trade_authorization_verdict TEXT,

    FOREIGN KEY (trade_backtest_id) REFERENCES backtest_results(backtest_id)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_bt_trades_backtest
    ON backtest_trades(trade_backtest_id);

-- =====================================================================
-- VIEW 1: Active Plans Dashboard
-- =====================================================================
CREATE VIEW IF NOT EXISTS vw_active_plans_dashboard AS
SELECT
    ap.plan_id,
    ap.plan_symbol,
    ap.plan_direction,
    ap.plan_strategy,
    ap.plan_state,
    ap.plan_confidence,
    ap.plan_health_score,
    ap.plan_pattern_score,
    ap.plan_pattern_verdict,
    ap.plan_active_patterns_count,
    ap.plan_risk_method,
    ap.plan_risk_percent,
    ap.plan_leverage,
    ap.plan_structure_health,
    ap.plan_risk_health,
    ap.plan_momentum_health,
    ap.plan_participation_health,
    ap.plan_execution_health,
    ap.plan_updated_at,
    sl.line_is_horizontal AS primary_line_is_flat,
    sl.line_quality_score AS primary_line_quality,
    sl.line_age_candles,
    sl.line_touch_count,
    sl.line_distance_health,
    rr.review_verdict AS river_verdict,
    rr.review_overall_score
FROM adaptive_plans ap
LEFT JOIN supertrend_lines sl ON ap.plan_primary_line_id = sl.line_id
LEFT JOIN (
    SELECT
        review_plan_id,
        review_verdict,
        review_overall_score,
        ROW_NUMBER() OVER (
            PARTITION BY review_plan_id
            ORDER BY review_timestamp DESC
        ) as rn
    FROM river_reviews
) rr ON ap.plan_id = rr.review_plan_id AND rr.rn = 1
WHERE ap.plan_state NOT IN ('FINISHED', 'LEARNING');

-- =====================================================================
-- VIEW 2: Hot Patterns
-- =====================================================================
CREATE VIEW IF NOT EXISTS vw_hot_patterns AS
SELECT
    pattern_id,
    pattern_category,
    pattern_name,
    pattern_total_occurrences,
    pattern_win_rate,
    pattern_avg_profit_atr_int,
    pattern_avg_loss_atr_int,
    pattern_is_predictive,
    pattern_is_dangerous,
    CASE
        WHEN pattern_win_rate > 0.75 THEN 'HOT'
        WHEN pattern_win_rate < 0.40 THEN 'DANGER'
        ELSE 'NEUTRAL'
    END AS status_label
FROM pattern_catalog
WHERE pattern_total_occurrences > 10;

-- =====================================================================
-- VIEW 3: Opportunity Learning (Rejected Plans Analysis)
-- =====================================================================
CREATE VIEW IF NOT EXISTS vw_opportunity_learning AS
SELECT
    outcome_plan_id,
    outcome_symbol,
    outcome_direction,
    outcome_timestamp,
    outcome_plan_confidence,
    outcome_plan_health_score,
    outcome_river_verdict,
    outcome_exit_reason AS actual_market_direction,
    outcome_pnl_percent AS price_movement_after_rejection,
    CASE
        WHEN outcome_pnl_percent > 0 AND outcome_direction = 'LONG'
            THEN 'MISSED_OPPORTUNITY'
        WHEN outcome_pnl_percent < 0 AND outcome_direction = 'SHORT'
            THEN 'MISSED_OPPORTUNITY'
        ELSE 'CORRECT_REJECTION'
    END AS opportunity_verdict
FROM shared_learning_outcomes
WHERE outcome_was_rejected = 1;

-- =====================================================================
-- SEED DEFAULT MARKET PROFILE (BTCUSDT)
-- =====================================================================
INSERT OR IGNORE INTO market_profiles (
    profile_symbol, profile_market_type, profile_enable_open_interest,
    profile_participation_metric, profile_price_scale,
    profile_tick_size_int, profile_quantity_scale
) VALUES (
    'BTCUSDT', 'FUTURES_USDM', 1, 'OPEN_INTEREST', 1, 10, 3
);

-- =====================================================================
-- END OF SCHEMA
-- =====================================================================

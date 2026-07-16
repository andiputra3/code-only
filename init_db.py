"""Initialize ST-LMS v2.0 database with full schema and 59 pattern seed."""
import sqlite3
import os
import logging
from datetime import datetime
from config.settings import DB_PATH

logger = logging.getLogger('ST-LMS')


def init_database():
    """Create DB and apply schema."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)

    conn = sqlite3.connect(DB_PATH)

    # FIX: Cari schema file dengan multiple fallback paths
    schema_paths = [
        os.path.join(os.path.dirname(__file__), "st_lms", "persistence", "schema.sql"),
        os.path.join(os.path.dirname(__file__), "st_lms", "persistence", "schema_full.sql"),
        "st_lms/persistence/schema.sql",
    ]

    schema_path = None
    for path in schema_paths:
        if os.path.exists(path):
            schema_path = path
            break

    if not schema_path:
        conn.close()
        raise FileNotFoundError(
            f"❌ Schema file not found! Searched paths:\n" +
            "\n".join(f"  - {p}" for p in schema_paths) +
            "\n\nPlease ensure Part 3 schema.sql is in st_lms/persistence/"
        )

    logger.info(f"📄 Loading schema from: {schema_path}")

    try:
        with open(schema_path, encoding='utf-8') as f:
            schema_sql = f.read()

        # FIX: Validasi schema tidak kosong
        if not schema_sql.strip():
            raise ValueError("Schema file is empty!")

        conn.executescript(schema_sql)
        logger.info("✅ Schema applied successfully")

    except sqlite3.Error as e:
        conn.close()
        raise RuntimeError(f"❌ Failed to apply schema: {e}")

    # Seed data
    seed_patterns(conn)
    seed_default_profile(conn)

    # FIX: Validasi seed data
    pattern_count = conn.execute("SELECT COUNT(*) FROM pattern_catalog").fetchone()[0]
    profile_count = conn.execute("SELECT COUNT(*) FROM market_profiles").fetchone()[0]

    if pattern_count == 0:
        logger.error("❌ Pattern seed failed — 0 patterns in catalog")
    else:
        logger.info(f"✅ Seeded {pattern_count} pattern definitions")

    if profile_count == 0:
        logger.error("❌ Profile seed failed — 0 profiles in market_profiles")
    else:
        logger.info(f"✅ Seeded {profile_count} market profile(s)")

    # FIX: Validasi table count
    table_count = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchone()[0]

    logger.info(f"✅ Database has {table_count} tables")

    conn.close()
    logger.info(f"✅ Database initialized at {DB_PATH}")


def seed_default_profile(conn):
    """Seed default BTCUSDT profile if not exists."""
    conn.execute("""
        INSERT OR IGNORE INTO market_profiles
        (profile_symbol, profile_market_type, profile_enable_open_interest,
         profile_price_scale, profile_tick_size_int, profile_quantity_scale)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ('BTCUSDT', 'FUTURES_USDM', 1, 1, 10, 3))
    conn.commit()


def seed_patterns(conn):
    """Seed lengkap 59 pattern definitions."""
    patterns = [
        # A: Single Line (12)
        ('A1_FIRST_TOUCH', 'A', 'First Touch', 'Harga menyentuh line pertama kali'),
        ('A2_NTH_TOUCH', 'A', 'Nth Touch', 'Harga menyentuh line ke-N'),
        ('A3_GENTLE_SLOPE', 'A', 'Gentle Slope Hold', 'Line slope 15-45° ideal'),
        ('A4_STEEP_SLOPE', 'A', 'Steep Slope Hold', 'Line slope 45-60° kuat'),
        ('A5_PARABOLIC_WARN', 'A', 'Parabolic Warning', 'Line slope >70° bahaya'),
        ('A6_FLAT_COMPRESSION', 'A', 'Flat Compression', 'Horizontal + optimal distance'),
        ('A7_AGING_SUPPORT', 'A', 'Aging Support', 'Age >30 + touch >=3'),
        ('A8_YOUNG_TEST', 'A', 'Young Line Test', 'Age <5, harga menguji'),
        ('A9_DIST_OPTIMAL', 'A', 'Distance Optimal', 'Within 0.5 ATR of line'),
        ('A10_DIST_EXTENDED', 'A', 'Distance Extended', '>2.0 ATR from line'),
        ('A11_VELOCITY_SPIKE', 'A', 'Velocity Spike', 'Velocity >150 int/candle'),
        ('A12_VELOCITY_DECAY', 'A', 'Velocity Decay', 'Velocity <20 + age >10'),
        # B: Multi-Line (10)
        ('B1_STAIR_STEP_UP', 'B', 'Stair-Step Up', 'Horizontal → breakout → higher horizontal'),
        ('B2_STAIR_STEP_DOWN', 'B', 'Stair-Step Down', 'Horizontal → breakdown → lower horizontal'),
        ('B3_LINE_CONVERGENCE', 'B', 'Line Convergence', '2 lines mendekat'),
        ('B4_LINE_DIVERGENCE', 'B', 'Line Divergence', '2 lines menjauh'),
        ('B5_NESTED_LINES', 'B', 'Nested Lines', 'Line kecil dalam line besar'),
        ('B6_LINE_SANDWICH', 'B', 'Line Sandwich', 'Harga terjepit 2 horizontal lines'),
        ('B7_DOUBLE_TOUCH', 'B', 'Double Touch', '2 lines disentuh dalam 5 candle'),
        ('B8_CASCADE_BREAK', 'B', 'Cascade Break', 'Line 1 broken → Line 2 broken'),
        ('B9_LINE_CLUSTER', 'B', 'Line Cluster', '3+ horizontal lines dalam <1 ATR'),
        ('B10_ALTERNATING_HOLD', 'B', 'Alternating Hold', 'Pantul bergantian antara 2 lines'),
        # C: Cross-TF (8)
        ('C1_TF_ALIGNMENT', 'C', 'TF Alignment', 'H1+M15+M5 semua sejajar'),
        ('C2_TF_CONFLICT', 'C', 'TF Conflict', 'H1 bullish, M5 bearish'),
        ('C3_MACRO_HOLD_MICRO_PULL', 'C', 'Macro Hold + Micro Pullback', 'H1 hold, M5 pullback'),
        ('C4_MACRO_BREAK_MICRO_HOLD', 'C', 'Macro Break + Micro Hold', 'H1 broken, M5 hold'),
        ('C5_FRACTAL_STAIR', 'C', 'Fractal Stair-Step', 'H4+H1+M15 semua stair-step'),
        ('C6_TIME_COMPRESSION', 'C', 'Time Compression', 'Semua TF convergence'),
        ('C7_TIME_EXPANSION', 'C', 'Time Expansion', 'Semua TF divergence'),
        ('C8_ECHO_PATTERN', 'C', 'Echo Pattern', 'Pola sama di H1 dan M15'),
        # D: Temporal (8)
        ('D1_SLOW_BUILD', 'D', 'Slow Build', 'Slope naik bertahap 20+ candle'),
        ('D2_FAST_EXHAUST', 'D', 'Fast Exhaust', 'Slope >60° <10 candle lalu flatten'),
        ('D3_AGING_GRACEFULLY', 'D', 'Aging Gracefully', 'Age >50, slope stabil, strength >5'),
        ('D4_PREMATURE_DEATH', 'D', 'Premature Death', 'Broken sebelum age 10'),
        ('D5_RESURRECTION', 'D', 'Resurrection', 'Broken lalu line baru di level sama'),
        ('D6_OSCILLATING_SLOPE', 'D', 'Oscillating Slope', 'Slope berubah 3+ kali'),
        ('D7_CONSISTENT_TOUCH', 'D', 'Consistent Touch', 'Disentuh setiap 5-8 candle'),
        ('D8_ACCELERATING_TOUCH', 'D', 'Accelerating Touch', 'Jarak antar touch memendek'),
        # E: Slope Transition (8)
        ('E1_FLAT_TO_IDEAL', 'E', 'Flat to Ideal', '<15° → 15-45° TREND START'),
        ('E2_IDEAL_TO_STEEP', 'E', 'Ideal to Steep', '15-45° → 45-60° ACCELERATION'),
        ('E3_STEEP_TO_PARABOLIC', 'E', 'Steep to Parabolic', '>60° → >70° CLIMAX'),
        ('E4_PARA_TO_FLAT', 'E', 'Parabolic to Flat', '>70° → <15° REVERSAL'),
        ('E5_STEEP_TO_IDEAL', 'E', 'Steep to Ideal', '>45° → 15-45° HEALTHY CORRECTION'),
        ('E6_IDEAL_TO_FLAT', 'E', 'Ideal to Flat', '15-45° → <15° TREND DYING'),
        ('E7_FLAT_FLIP', 'E', 'Flat Flip', 'Horizontal flip arah = REVERSAL'),
        ('E8_SLOPE_OSCILLATION', 'E', 'Slope Oscillation', 'Bolak-balik 10-20° COMPRESSION'),
        # F: Distance (6)
        ('F1_RUBBER_BAND_STRETCH', 'F', 'Rubber Band Stretch', '>2.5 ATR REVERSION'),
        ('F2_RUBBER_BAND_SNAP', 'F', 'Rubber Band Snap', '>2.5→<0.5 ATR <10 candle'),
        ('F3_GENTLE_RETURN', 'F', 'Gentle Return', '1.5→0.3 ATR bertahap'),
        ('F4_HOVER', 'F', 'Hover', '0.2-0.5 ATR selama 10+ candle'),
        ('F5_KISS_AND_GO', 'F', 'Kiss and Go', 'Touch lalu langsung >1 ATR'),
        ('F6_REPEATED_KISS', 'F', 'Repeated Kiss', 'Distance=0 3+ kali dalam 20 candle'),
        # G: Composite (7)
        ('G1_GOLDEN_SETUP', 'G', 'Golden Setup', 'Ideal+aging+optimal+TF align'),
        ('G2_DEATH_SPIRAL', 'G', 'Death Spiral', 'Parabolic+young+extended+conflict'),
        ('G3_SIDEWAY_TRAP', 'G', 'Sideway Trap', 'Flat+cluster+hover+decay'),
        ('G4_BREAKOUT_CHARGE', 'G', 'Breakout Charge', 'Flat→Ideal+cluster break+vol spike'),
        ('G5_EXHAUSTION_REV', 'G', 'Exhaustion Reversal', 'Para→Flat+extended+aging+RB snap'),
        ('G6_HEALTHY_PULLBACK', 'G', 'Healthy Pullback', 'Steep→Ideal+gentle+macro hold+micro pull'),
        ('G7_SILENT_ACCUM', 'G', 'Silent Accumulation', 'Flat+repeated kiss+consistent+aging'),
    ]

    conn.executemany(
        """INSERT OR IGNORE INTO pattern_catalog
           (pattern_id, pattern_category, pattern_name, pattern_description)
           VALUES (?, ?, ?, ?)""",
        patterns
    )
    conn.commit()
    logger.info(f"✅ Seeded {len(patterns)} pattern definitions (59 total)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')
    init_database()

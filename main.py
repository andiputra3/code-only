"""ST-LMS v2.0 — Main Entry Point.

Usage:
    python main.py --symbol BTCUSDT --timeframes H1,M15,M5
    python main.py --demo
    python main.py --help
"""
import argparse
import sys
import os
import logging
import signal
import random
from datetime import datetime, timedelta

from st_lms.root.pipeline import Pipeline

# Setup logging
def setup_logging(verbose: bool = False):
    """Configure logging untuk ST-LMS v2.0"""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    date_format = '%d/%m/%Y %H:%M:%S'
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Reduce noise dari library
    logging.getLogger('streamlit').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger('ST-LMS')

# Global flag untuk shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    shutdown_requested = True
    logger.warning("⚠️  Shutdown requested — finishing current cycle...")

def generate_demo_candles(count: int = 100, base_price: int = 65000, 
                          volatility: float = 0.02, seed: int = None):
    """Generate realistic demo candles dengan volatility dan trend changes.
    
    Args:
        count: Number of candles
        base_price: Starting price (integer, scale=1)
        volatility: Base volatility (0.01 = 1%)
        seed: Random seed untuk reproducibility
    """
    if seed is not None:
        random.seed(seed)
    
    candles = []
    price = base_price
    ts = datetime.utcnow() - timedelta(minutes=count * 60)
    
    # Trend phases: uptrend, downtrend, sideway
    trend_phases = [
        ('UP', 30),      # 30 candles uptrend
        ('DOWN', 20),    # 20 candles downtrend
        ('SIDEWAY', 25), # 25 candles sideway
        ('UP', 25),      # 25 candles uptrend
    ]
    
    current_phase_idx = 0
    candles_in_phase = 0
    
    for i in range(count):
        # Determine current phase
        if current_phase_idx < len(trend_phases):
            phase, duration = trend_phases[current_phase_idx]
            if candles_in_phase >= duration:
                current_phase_idx += 1
                candles_in_phase = 0
                if current_phase_idx < len(trend_phases):
                    phase, duration = trend_phases[current_phase_idx]
        else:
            phase = 'SIDEWAY'
        
        # Calculate price change based on phase
        if phase == 'UP':
            trend_bias = volatility * 0.5  # Upward bias
        elif phase == 'DOWN':
            trend_bias = -volatility * 0.5  # Downward bias
        else:  # SIDEWAY
            trend_bias = 0
        
        # Add random noise + occasional spikes
        noise = random.gauss(0, volatility)
        spike = random.choices([0, 1], weights=[0.95, 0.05])[0] * random.uniform(-0.05, 0.05)
        
        price_change_pct = trend_bias + noise + spike
        price_change = int(price * price_change_pct)
        
        open_p = price
        close_p = price + price_change
        
        # Realistic high/low
        high_p = max(open_p, close_p) + abs(random.gauss(0, volatility * 0.3)) * price
        low_p = min(open_p, close_p) - abs(random.gauss(0, volatility * 0.3)) * price
        
        # Volume dengan occasional spikes
        base_volume = 1000 + i * 10
        volume_spike = random.choices([1, 3, 5], weights=[0.8, 0.15, 0.05])[0]
        volume = int(base_volume * volume_spike)
        
        candles.append({
            'timestamp': ts.isoformat(),
            'open': open_p,
            'high': int(high_p),
            'low': int(low_p),
            'close': close_p,
            'volume': volume,
        })
        
        price = close_p
        ts += timedelta(minutes=60)
        candles_in_phase += 1
    
    return candles


def main():
    parser = argparse.ArgumentParser(
        description="ST-LMS v2.0 — Adaptive Trading Plan Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single cycle with demo data
  python main.py --demo --symbol BTCUSDT --cycles 1
  
  # Run 5 cycles with multiple timeframes
  python main.py --demo --symbol ETHUSDT --timeframes H4,H1,M15 --cycles 5
  
  # Use Kelly risk method
  python main.py --demo --symbol BTCUSDT --risk-method kelly
  
  # Enable verbose logging
  python main.py --demo --symbol BTCUSDT --verbose
        """
    )
    parser.add_argument('--symbol', default='BTCUSDT',
                        help='Trading pair (default: BTCUSDT)')
    parser.add_argument('--timeframes', default='H1,M15,M5',
                        help='Comma-separated timeframes (default: H1,M15,M5)')
    parser.add_argument('--risk-method', default='fixed_fraction',
                        choices=['fixed_fraction', 'kelly'],
                        help='Risk sizing method')
    parser.add_argument('--demo', action='store_true',
                        help='Run with demo candles')
    parser.add_argument('--cycles', type=int, default=1,
                        help='Number of pipeline cycles')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable debug logging')
    args = parser.parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)
    
    logger.info(f"🚀 ST-LMS v2.0 Starting — Symbol: {args.symbol}")

    timeframes = [tf.strip().upper() for tf in args.timeframes.split(',')]
    
    # Validasi timeframe
    from config.settings import VALID_TIMEFRAMES
    for tf in timeframes:
        if tf not in VALID_TIMEFRAMES:
            logger.error(f"❌ Invalid timeframe: {tf}. Valid: {', '.join(sorted(VALID_TIMEFRAMES))}")
            sys.exit(1)

    # Initialize DB if not exists
    try:
        import init_db
        if not os.path.exists('st_lms_v2.db'):
            logger.info("📦 Initializing database...")
            init_db.init_database()
    except Exception as e:
        logger.warning(f"⚠️  DB init skipped: {e}")

    # Register signal handler untuk graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    pipeline = Pipeline()
    try:
        for cycle in range(args.cycles):
            # Check shutdown flag
            if shutdown_requested:
                logger.warning("🛑 Shutdown — skipping remaining cycles")
                break
            
            progress = f"[{cycle+1}/{args.cycles}]"
            logger.info(f"{'='*60}")
            logger.info(f"{progress} 🚀 Cycle — {args.symbol}")
            logger.info(f"{'='*60}")

            candles_by_tf = {tf: generate_demo_candles(100) for tf in timeframes}

            result = pipeline.run(
                symbol=args.symbol,
                timeframes=timeframes,
                candles=candles_by_tf,
                risk_method=args.risk_method,
            )

            # Log result dengan structured format
            logger.info(f"📊 Cycle Result:")
            logger.info(f"   Cycle ID    : {result['cycle_id']}")
            logger.info(f"   Winner      : {result['winner']}")
            logger.info(f"   Authorized  : {result['authorized']}")
            logger.info(f"   Position ID : {result['position_id']}")
            logger.info(f"   Patterns    : {result['patterns_found']}")
            
            for direction, info in result['plans'].items():
                logger.info(
                    f"   {direction:8s} → state={info['state']:15s} "
                    f"conf={info['confidence']:5.1f}% health={info['health']:5.1f}"
                )

    except KeyboardInterrupt:
        logger.warning("⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        pipeline.close()
        logger.info("✅ Pipeline completed successfully.")


if __name__ == '__main__':
    main()
```

---

## **FILE 8: `requirements.txt`**


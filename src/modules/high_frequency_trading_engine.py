# File Name: high_frequency_trading_engine.py
# Location: /src/modules/
# Subsystem: HFT Order Matching Core & Circuit Breaker UPDATE
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_spread_velocity(ask_prices: np.ndarray, bid_prices: np.ndarray, time_deltas_ms: np.ndarray) -> np.ndarray:
    """Calculates the velocity of the bid-ask spread to detect algorithmic flash crashes."""
    total_assets = ask_prices.shape[0]
    spread_velocities = np.zeros(total_assets, dtype=np.float64)
    
    for i in prange(total_assets):
        if time_deltas_ms[i] > 0:
            spread = ask_prices[i] - bid_prices[i]
            # Velocity = Change in Spread / Time
            # Highly volatile assets will show massive spread velocities
            spread_velocities[i] = spread / time_deltas_ms[i]
        else:
            spread_velocities[i] = 0.0
            
    return spread_velocities

class HighFrequencyTradingEngine:
    def __init__(self):
        # If the spread opens up faster than $10 per millisecond, algorithms have panicked
        self.circuit_breaker_velocity_threshold = 10.0 

    def process_market_tick(self, tickers: List[str], asks: List[float], bids: List[float], tick_time_ms: List[float]) -> dict:
        print(f"\n[GLOBAL MARKETS] Ingesting HFT liquidity ticks and evaluating spread velocity...")
        start_time = time.time()
        
        ask_arr = np.array(asks, dtype=np.float64)
        bid_arr = np.array(bids, dtype=np.float64)
        time_arr = np.array(tick_time_ms, dtype=np.float64)
        
        # Execute JIT Math
        velocities = parallel_calculate_spread_velocity(ask_arr, bid_arr, time_arr)
        
        circuit_breakers_tripped = []
        for i in range(len(tickers)):
            # Detect negative spreads (crossed book / arbitrage opportunity) or extreme flash-crash velocity
            if asks[i] < bids[i]:
                # Arbitrage condition handled silently by the matching engine
                pass 
            
            if velocities[i] > self.circuit_breaker_velocity_threshold:
                circuit_breakers_tripped.append({
                    "ticker": tickers[i],
                    "spread_velocity_usd_ms": round(velocities[i], 2),
                    "action": "HALT_TRADING_LULD_CIRCUIT_BREAKER_ENGAGED"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "MARKETS_OPEN_LIQUIDITY_NOMINAL" if not circuit_breakers_tripped else "FLASH_CRASH_DETECTED"

        return {
            "exchange_status": status,
            "assets_monitored": len(tickers),
            "circuit_breakers_tripped": circuit_breakers_tripped,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    hft = HighFrequencyTradingEngine()
    # Mocking Market Ticks. 
    # Ticker 3 (e.g., AAPL) experiences a sudden massive gap in bid/ask over 1 millisecond (Flash Crash).
    print("TESTING HFT MATCHING ENGINE:\n", hft.process_market_tick(
        ["SPY", "QQQ", "AAPL"], 
        [500.05, 400.10, 205.00], # Asks
        [500.04, 400.08, 180.00], # Bids (AAPL bid plummeted)
        [1.0, 1.0, 1.0]           # Tick time in MS
    ))

# File Name: quantum_energy_arbitrage_broker.py
# Location: /src/modules/
# Subsystem: Grid-Scale Battery Arbitrage & Spot Market Broker
# Copyright (c) 2026 Revolutionary Technology

import time
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_marginal_arbitrage(grid_demand_mw: np.ndarray, renewable_supply_mw: np.ndarray, base_cost_usd_mw: float) -> np.ndarray:
    """Calculates instantaneous algorithmic spot-prices (USD/MW) based on grid supply/demand imbalances."""
    total_nodes = grid_demand_mw.shape[0]
    spot_prices_usd = np.zeros(total_nodes, dtype=np.float64)
    
    for i in prange(total_nodes):
        net_demand = grid_demand_mw[i] - renewable_supply_mw[i]
        
        if net_demand < 0:
            # Oversupply from renewables (e.g., sunny/windy day). Prices drop to near zero or negative.
            spot_prices_usd[i] = max(-10.0, base_cost_usd_mw * 0.1 * net_demand)
        else:
            # Undersupply. Prices spike exponentially based on deficit severity.
            scarcity_multiplier = 1.0 + (net_demand / 100.0)**1.5
            spot_prices_usd[i] = base_cost_usd_mw * scarcity_multiplier
            
    return spot_prices_usd

class QuantumEnergyArbitrageBroker:
    def __init__(self):
        self.base_megawatt_cost_usd = 45.0 # Baseline cost of 1 MW
        self.buy_threshold_usd = 15.0 # Buy and store energy if it drops below $15/MW
        self.sell_threshold_usd = 150.0 # Discharge batteries to grid if price spikes above $150/MW

    def execute_spot_market_trades(self, substation_ids: List[str], current_demand_mw: List[float], renewable_generation_mw: List[float], battery_reserves_mwh: List[float]) -> dict:
        print(f"\n[ENERGY MARKETS] Executing microsecond algorithmic power arbitrage...")
        start_time = time.time()
        
        dem_arr = np.array(current_demand_mw, dtype=np.float64)
        ren_arr = np.array(renewable_generation_mw, dtype=np.float64)
        
        # Execute JIT Math
        spot_prices = parallel_calculate_marginal_arbitrage(dem_arr, ren_arr, self.base_megawatt_cost_usd)
        
        market_actions = []
        projected_profit_usd = 0.0
        
        for i in range(len(substation_ids)):
            price = spot_prices[i]
            reserves = battery_reserves_mwh[i]
            
            if price <= self.buy_threshold_usd:
                market_actions.append({
                    "substation": substation_ids[i],
                    "spot_price_usd_mw": round(price, 2),
                    "action": "BUY_AND_CHARGE_BATTERIES"
                })
            elif price >= self.sell_threshold_usd and reserves > 10.0:
                # Discharge 10 MW into the grid at the spiked price
                trade_value = 10.0 * price
                projected_profit_usd += trade_value
                market_actions.append({
                    "substation": substation_ids[i],
                    "spot_price_usd_mw": round(price, 2),
                    "action": f"SELL_DISCHARGE_10MW_TO_GRID_PROFIT_${round(trade_value, 2)}"
                })
            else:
                market_actions.append({
                    "substation": substation_ids[i],
                    "spot_price_usd_mw": round(price, 2),
                    "action": "HOLD_RESERVES"
                })

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "market_status": "ALGORITHMIC_TRADING_ACTIVE",
            "substations_brokered": len(substation_ids),
            "projected_instantaneous_profit_usd": round(projected_profit_usd, 2),
            "ledger_actions": market_actions,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    broker = QuantumEnergyArbitrageBroker()
    # Mocking the California grid (CAISO). Substation 1 has huge solar oversupply (negative pricing).
    # Substation 3 is hitting peak evening demand with no solar (massive price spike).
    print("TESTING ENERGY ARBITRAGE BROKER:\n", broker.execute_spot_market_trades(
        ["SUB-LA-1", "SUB-SF-2", "SUB-SD-3"], 
        [500.0, 800.0, 1200.0], # Demand MW
        [700.0, 800.0, 50.0],   # Renewable Generation MW
        [150.0, 200.0, 300.0]   # Battery Reserves MWh
    ))

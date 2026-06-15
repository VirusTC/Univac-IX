# File Name: synthetic_coal_gasification_plant.py
# Location: /src/modules/
# Subsystem: Gasworks Heavy Industrial Cracking & Syngas Yield
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange

@njit(cache=True, fastmath=True)
def calculate_boudouard_reaction_yield(temp_k: float, pressure_atm: float) -> float:
    """Calculates carbon monoxide yield via the endothermic Boudouard reaction (C + CO2 -> 2CO)."""
    # Shift towards CO favors high temps and low pressure
    if temp_k < 973.15: # Below 700C, reaction is too slow
        return 0.0
    equilibrium_constant = math.exp(21.4 - (20500.0 / temp_k))
    yield_fraction = equilibrium_constant / (equilibrium_constant + pressure_atm)
    return yield_fraction

class GasworksRefineryMatrix:
    def __init__(self):
        self.critical_temp_k = 1500.0
        self.critical_pressure_atm = 40.0

    def evaluate_cracking_vessel(self, temp_c: float, pressure_atm: float, coal_feed_kg_s: float) -> dict:
        print(f"\n[GASWORKS] Evaluating synthetic gasification thermal cracking...")
        start_time = time.time()
        
        temp_k = temp_c + 273.15
        
        # JIT Execution
        syngas_fraction = calculate_boudouard_reaction_yield(temp_k, pressure_atm)
        production_rate_kg_s = coal_feed_kg_s * syngas_fraction * 1.8 # Expansion factor
        
        status = "CRACKING_STABLE"
        if temp_k > self.critical_temp_k or pressure_atm > self.critical_pressure_atm:
            status = "VESSEL_RUPTURE_WARNING"

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "refinery_status": status,
            "syngas_production_rate_kg_s": round(production_rate_kg_s, 2),
            "reaction_efficiency_pct": round(syngas_fraction * 100.0, 1),
            "execution_time_ms": round(execution_ms, 5)
        }

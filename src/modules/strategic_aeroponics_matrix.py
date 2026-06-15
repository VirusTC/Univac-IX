# File Name: strategic_aeroponics_matrix.py
# Location: /src/modules/
# Subsystem: Strategic Aeroponics & Food Security Governor
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_crop_yield(light_intensity_ppfd: np.ndarray, co2_ppm: float, nutrient_ph: float) -> np.ndarray:
    """Calculates projected biomass yield (kg) per square meter based on photosynthetic variables."""
    total_zones = light_intensity_ppfd.shape[0]
    yields_kg_m2 = np.zeros(total_zones, dtype=np.float64)
    
    # Ideal pH for most aeroponic crops is ~5.8 to 6.2
    ph_penalty = 1.0 - (abs(nutrient_ph - 6.0) * 0.2)
    ph_penalty = max(0.1, ph_penalty)
    
    # CO2 saturation curve (peaks around 1200 ppm)
    co2_factor = math.log10(max(400.0, co2_ppm)) / math.log10(1200.0)
    co2_factor = min(1.2, co2_factor)
    
    for i in prange(total_zones):
        # Base photosynthesis rate driven by light (Photosynthetic Photon Flux Density)
        light = light_intensity_ppfd[i]
        base_growth = (light * 0.015) 
        
        yields_kg_m2[i] = base_growth * co2_factor * ph_penalty
        
    return yields_kg_m2

class StrategicAeroponicsMatrix:
    def __init__(self):
        self.critical_ph_high = 7.0
        self.critical_ph_low = 5.0

    def evaluate_agricultural_grid(self, zone_ids: List[str], light_levels_ppfd: List[float], co2_ppm: float, reservoir_ph: float) -> dict:
        print(f"\n[AGRICULTURE] Sweeping subterranean food security and aeroponic yields...")
        start_time = time.time()
        
        light_arr = np.array(light_levels_ppfd, dtype=np.float64)
        
        # Execute JIT Math
        projected_yields = parallel_calculate_crop_yield(light_arr, co2_ppm, reservoir_ph)
        total_projected_food_kg = np.sum(projected_yields) * 100.0 # Assuming 100 sq meters per zone
        
        status = "AGRICULTURAL_GRID_STABLE"
        action = "MAINTAIN_CURRENT_DOSING"
        
        if reservoir_ph > self.critical_ph_high or reservoir_ph < self.critical_ph_low:
            status = "CRITICAL_NUTRIENT_LOCKOUT"
            action = "INJECT_PH_BUFFER_IMMEDIATELY"
            
        if co2_ppm < 450.0:
            action = "INCREASE_CO2_GENERATOR_OUTPUT"

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "facility_status": status,
            "autonomic_action": action,
            "zones_monitored": len(zone_ids),
            "reservoir_ph": reservoir_ph,
            "projected_harvest_yield_kg": round(total_projected_food_kg, 2),
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    farm = StrategicAeroponicsMatrix()
    # Mocking 4 massive grow zones. Perfect pH (6.0), highly elevated CO2 (1000ppm).
    print("TESTING STRATEGIC AEROPONICS:\n", farm.evaluate_agricultural_grid(
        ["ZONE-A", "ZONE-B", "ZONE-C", "ZONE-D"], 
        [800.0, 850.0, 900.0, 750.0], 
        1000.0, 
        6.0
    ))

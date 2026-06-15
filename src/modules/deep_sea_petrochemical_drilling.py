# File Name: deep_sea_petrochemical_drilling.py
# Location: /src/modules/
# Subsystem: Offshore Petrochemical Drilling & BOP Interlock
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_hydrostatic_pressure(depths_m: np.ndarray, mud_density_kg_m3: float) -> np.ndarray:
    """Calculates the bottom-hole hydrostatic pressure column to prevent blowout events."""
    total_wells = depths_m.shape[0]
    pressures_mpa = np.zeros(total_wells, dtype=np.float64)
    gravity = 9.80665
    
    for i in prange(total_wells):
        if depths_m[i] > 0.0:
            # P = rho * g * h
            pascal = mud_density_kg_m3 * gravity * depths_m[i]
            pressures_mpa[i] = pascal / 1000000.0 # Convert to Megapascals
            
    return pressures_mpa

class DeepSeaPetrochemicalMatrix:
    def __init__(self):
        # Standard API blowout preventer safety rating (e.g., 100 MPa / ~15,000 PSI)
        self.bop_max_tolerance_mpa = 100.0 

    def evaluate_drilling_telemetry(self, well_ids: List[str], depths_meters: List[float], mud_weight_kg_m3: float) -> dict:
        print(f"\n[PETROCHEMICAL] Sweeping deep-sea well pressures and BOP tolerances...")
        start_time = time.time()
        
        depth_arr = np.array(depths_meters, dtype=np.float64)
        
        # Execute JIT Math
        bottom_hole_pressures_mpa = parallel_calculate_hydrostatic_pressure(depth_arr, mud_weight_kg_m3)
        
        critical_wells = []
        for i in range(len(well_ids)):
            if bottom_hole_pressures_mpa[i] >= (self.bop_max_tolerance_mpa * 0.90): # 90% threshold
                critical_wells.append({
                    "well_id": well_ids[i],
                    "pressure_mpa": round(bottom_hole_pressures_mpa[i], 2),
                    "status": "IMMINENT_KICK_WARNING_ENGAGE_BOP"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "WELL_CONTROL_LOST" if critical_wells else "DRILLING_STABLE"

        return {
            "platform_status": status,
            "wells_monitored": len(well_ids),
            "mud_density_kg_m3": mud_weight_kg_m3,
            "critical_pressure_alerts": critical_wells,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    matrix = DeepSeaPetrochemicalMatrix()
    # Mocking 3 wells at extreme depths (e.g., Deepwater Horizon depths) with heavy drilling mud
    print("TESTING PETROCHEMICAL MATRIX:\n", matrix.evaluate_drilling_telemetry(["WELL-A", "WELL-B", "WELL-C"], [5000.0, 10500.0, 3200.0], 1400.0))

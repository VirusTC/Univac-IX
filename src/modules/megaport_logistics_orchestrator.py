# File Name: megaport_logistics_orchestrator.py
# Location: /src/modules/
# Subsystem: Automated Megaport Logistics & Gantry Crane Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_stack_tipping_moment(stack_heights_m: np.ndarray, wind_speeds_ms: np.ndarray, average_mass_kg: float) -> np.ndarray:
    """Calculates aerodynamic tipping risk for massive shipping container stacks in automated yards."""
    total_stacks = stack_heights_m.shape[0]
    tipping_risk_pct = np.zeros(total_stacks, dtype=np.float64)
    
    # Constants for a standard 40ft high-cube container stack
    air_density = 1.225 # kg/m^3
    drag_coeff = 2.1 # Boxy object drag
    container_width_m = 2.44
    gravity = 9.81
    
    for i in prange(total_stacks):
        # Aerodynamic Wind Force = 0.5 * rho * v^2 * Cd * Area (Area = height * length)
        # Using 12.19m for length of a 40ft container exposed to broadside wind
        wind_force_newtons = 0.5 * air_density * (wind_speeds_ms[i]**2) * drag_coeff * (stack_heights_m[i] * 12.19)
        
        # Tipping Moment = Wind Force * (Height / 2) [Acting on center of pressure]
        tipping_moment = wind_force_newtons * (stack_heights_m[i] / 2.0)
        
        # Stabilizing Gravity Moment = Total Mass * g * (Width / 2)
        total_mass = average_mass_kg * (stack_heights_m[i] / 2.9) # roughly 2.9m per container height
        gravity_moment = total_mass * gravity * (container_width_m / 2.0)
        
        # Risk is the ratio of tipping force to stabilizing force
        if gravity_moment > 0:
            tipping_risk_pct[i] = (tipping_moment / gravity_moment) * 100.0
        else:
            tipping_risk_pct[i] = 100.0
            
    return tipping_risk_pct

class MegaportLogisticsOrchestrator:
    def __init__(self):
        self.critical_tipping_threshold = 80.0 # 80% of force required to topple a stack

    def evaluate_yard_physics(self, yard_blocks: List[str], stack_heights_m: List[float], wind_speed_kmh: float) -> dict:
        print(f"\n[MARITIME LOGISTICS] Calculating Megaport aerodynamic loads and crane safety interlocks...")
        start_time = time.time()
        
        height_arr = np.array(stack_heights_m, dtype=np.float64)
        wind_ms_arr = np.full(len(stack_heights_m), wind_speed_kmh * (1000.0 / 3600.0), dtype=np.float64)
        
        # Assuming an average mixed container weight of 18,000 kg
        risk_array = parallel_calculate_stack_tipping_moment(height_arr, wind_ms_arr, 18000.0)
        
        evacuations = []
        for i in range(len(yard_blocks)):
            if risk_array[i] >= self.critical_tipping_threshold:
                evacuations.append({
                    "yard_block": yard_blocks[i],
                    "tipping_risk_pct": round(risk_array[i], 2),
                    "action": "LOCK_GANTRY_CRANES_RESTACK_TO_LOWER_TIERS"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "CRITICAL_WIND_SHEAR_YARD_LOCKED" if evacuations else "MEGAPORT_OPERATIONS_NOMINAL"

        return {
            "terminal_status": status,
            "wind_speed_kmh": wind_speed_kmh,
            "blocks_analyzed": len(yard_blocks),
            "safety_interventions": evacuations,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    port = MegaportLogisticsOrchestrator()
    # Mocking a typhoon hitting a port. Block C has containers stacked 8-high (23.2m).
    print("TESTING MEGAPORT ORCHESTRATOR:\n", port.evaluate_yard_physics(
        ["BLOCK-A", "BLOCK-B", "BLOCK-C"], 
        [8.7, 14.5, 23.2], 
        110.0 # 110 km/h wind
    ))

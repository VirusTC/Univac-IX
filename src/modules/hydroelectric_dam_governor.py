# File Name: hydroelectric_dam_governor.py
# Location: /src/modules/
# Subsystem: Hydroelectric Dam Spillway & Turbine Governor
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_turbine_power(flow_rates_m3_s: np.ndarray, head_meters: float, efficiency: float) -> np.ndarray:
    """Calculates instantaneous Megawatt (MW) output across an array of hydroelectric turbines."""
    total_turbines = flow_rates_m3_s.shape[0]
    power_mw = np.zeros(total_turbines, dtype=np.float64)
    
    # Constants: Gravity (9.81 m/s^2), Water Density (~998 kg/m^3)
    gravity = 9.81
    density = 998.0
    
    for i in prange(total_turbines):
        # Power Equation: P = η * ρ * g * h * Q
        watts = efficiency * density * gravity * head_meters * flow_rates_m3_s[i]
        power_mw[i] = watts / 1000000.0  # Convert to Megawatts
        
    return power_mw

class HydroelectricDamGovernor:
    def __init__(self):
        self.critical_head_m = 185.0 # Max structural limit before spillways must open
        self.turbine_efficiency = 0.92

    def evaluate_penstock_telemetry(self, reservoir_head_m: float, turbine_flows_m3s: List[float]) -> dict:
        print(f"\n[HYDRO-GRID] Evaluating dam structural pressure and turbine generation yields...")
        start_time = time.time()
        
        flow_arr = np.array(turbine_flows_m3s, dtype=np.float64)
        
        # JIT execute power mathematics
        turbine_outputs_mw = parallel_calculate_turbine_power(flow_arr, reservoir_head_m, self.turbine_efficiency)
        
        total_grid_yield_mw = np.sum(turbine_outputs_mw)
        
        # Autonomic Spillway Safety Interlock
        spillway_status = "CLOSED"
        dam_status = "STRUCTURAL_STABILITY_NOMINAL"
        
        if reservoir_head_m >= self.critical_head_m:
            spillway_status = "EMERGENCY_OPEN"
            dam_status = "CRITICAL_OVERPRESSURE_DETECTED"
            
        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "facility_status": dam_status,
            "spillway_valves": spillway_status,
            "reservoir_head_meters": reservoir_head_m,
            "total_generation_mw": round(total_grid_yield_mw, 2),
            "active_turbines": len(turbine_flows_m3s),
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    gov = HydroelectricDamGovernor()
    # Mocking a heavy rain event: High head pressure, 4 turbines running wide open at 120 cubic meters per sec
    print("TESTING HYDROELECTRIC GOVERNOR:\n", gov.evaluate_penstock_telemetry(186.5, [120.0, 120.0, 120.0, 120.0]))

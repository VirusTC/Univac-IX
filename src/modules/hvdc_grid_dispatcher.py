# File Name: hvdc_grid_dispatcher.py
# Location: /src/modules/
# Subsystem: High-Voltage Direct Current (HVDC) Grid Intertie
# Copyright (c) 2026 Revolutionary Technology

import time
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_transmission_losses(currents_amp: np.ndarray, line_lengths_km: np.ndarray, resistance_ohms_per_km: float) -> np.ndarray:
    """Calculates instantaneous I^2R thermal power losses (Megawatts) across massive continental transmission lines."""
    total_lines = currents_amp.shape[0]
    power_loss_mw = np.zeros(total_lines, dtype=np.float64)
    
    for i in prange(total_lines):
        # Calculate total resistance of the line span
        total_resistance = line_lengths_km[i] * resistance_ohms_per_km
        
        # Power Loss = I^2 * R (in Watts), then convert to Megawatts
        loss_watts = (currents_amp[i] ** 2) * total_resistance
        power_loss_mw[i] = loss_watts / 1000000.0
        
    return power_loss_mw

class HVDCGridDispatcher:
    def __init__(self):
        # Typical aluminum conductor steel-reinforced (ACSR) resistance
        self.ohms_per_km = 0.03 
        self.critical_loss_threshold_mw = 150.0 # If a line loses this much power to heat, it will melt/sag

    def evaluate_grid_stability(self, line_ids: List[str], line_currents_amp: List[float], lengths_km: List[float]) -> dict:
        print(f"\n[POWER GRID] Sweeping trans-continental HVDC intertie stability...")
        start_time = time.time()
        
        i_arr = np.array(line_currents_amp, dtype=np.float64)
        len_arr = np.array(lengths_km, dtype=np.float64)
        
        # Execute JIT Math
        thermal_losses_mw = parallel_calculate_transmission_losses(i_arr, len_arr, self.ohms_per_km)
        
        tripped_breakers = []
        total_grid_loss = 0.0
        
        for i in range(len(line_ids)):
            loss = thermal_losses_mw[i]
            total_grid_loss += loss
            
            # Autonomic Grid Islanding: Sever lines that are overheating to save the wider grid
            if loss > self.critical_loss_threshold_mw:
                tripped_breakers.append({
                    "transmission_line": line_ids[i],
                    "thermal_loss_mw": round(loss, 2),
                    "action": "VACUUM_BREAKER_TRIPPED_TO_PREVENT_CASCADE"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "GRID_CASCADE_WARNING" if tripped_breakers else "HVDC_INTERTIE_STABLE"

        return {
            "grid_status": status,
            "lines_monitored": len(line_ids),
            "total_transmission_loss_mw": round(total_grid_loss, 2),
            "islanding_events": tripped_breakers,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    grid = HVDCGridDispatcher()
    # Mocking 3 massive lines. Line 2 is carrying an extreme 2500 Amps over 1000km (Will overheat).
    print("TESTING HVDC GRID DISPATCHER:\n", grid.evaluate_grid_stability(
        ["PACIFIC-DC-1", "TEXAS-INTERCONNECT-2", "EASTERN-TRUNK-3"], 
        [800.0, 2500.0, 1200.0], 
        [1360.0, 1000.0, 800.0]
    ))

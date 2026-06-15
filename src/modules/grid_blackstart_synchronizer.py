# File Name: grid_blackstart_synchronizer.py
# Location: /src/modules/
# Subsystem: Autonomic Grid Blackstart & AC Phase Synchronizer
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_phase_matching(grid_a_hz: np.ndarray, grid_a_phase_rad: np.ndarray, grid_b_hz: np.ndarray, grid_b_phase_rad: np.ndarray) -> np.ndarray:
    """Calculates the phase angle difference to determine if two dead-grid islands can be safely tied together."""
    total_ties = grid_a_hz.shape[0]
    phase_deltas_deg = np.zeros(total_ties, dtype=np.float64)
    
    for i in prange(total_ties):
        # Calculate the absolute difference in the AC sine wave phase angles
        delta_rad = abs(grid_a_phase_rad[i] - grid_b_phase_rad[i])
        
        # Normalize to 0 - PI (0 to 180 degrees)
        delta_rad = delta_rad % (2.0 * math.pi)
        if delta_rad > math.pi:
            delta_rad = (2.0 * math.pi) - delta_rad
            
        phase_deltas_deg[i] = math.degrees(delta_rad)
        
    return phase_deltas_deg

class GridBlackstartSynchronizer:
    def __init__(self):
        # Breakers will explode if closed when phase difference is > 10 degrees
        self.max_safe_tie_angle_deg = 10.0 
        self.target_frequency_hz = 60.0

    def evaluate_island_ties(self, tie_breaker_ids: List[str], freq_a: List[float], phase_a: List[float], freq_b: List[float], phase_b: List[float]) -> dict:
        print(f"\n[INFRASTRUCTURE RECOVERY] Synchronizing AC phase angles for continental grid blackstart...")
        start_time = time.time()
        
        fa_arr = np.array(freq_a, dtype=np.float64)
        pa_arr = np.array(phase_a, dtype=np.float64)
        fb_arr = np.array(freq_b, dtype=np.float64)
        pb_arr = np.array(phase_b, dtype=np.float64)
        
        # Execute JIT Math
        phase_differentials = parallel_calculate_phase_matching(fa_arr, pa_arr, fb_arr, pb_arr)
        
        tie_actions = []
        successful_ties = 0
        
        for i in range(len(tie_breaker_ids)):
            delta = phase_differentials[i]
            
            # Frequencies must also be perfectly matched (e.g., both exactly 60.00 Hz)
            freq_matched = abs(freq_a[i] - freq_b[i]) < 0.05
            
            if freq_matched and delta <= self.max_safe_tie_angle_deg:
                successful_ties += 1
                tie_actions.append({
                    "breaker_id": tie_breaker_ids[i],
                    "phase_delta_deg": round(delta, 2),
                    "action": "SYNCHRONIZATION_LOCK_CLOSE_HIGH_VOLTAGE_BREAKERS"
                })
            else:
                tie_actions.append({
                    "breaker_id": tie_breaker_ids[i],
                    "phase_delta_deg": round(delta, 2),
                    "action": "OUT_OF_PHASE_DO_NOT_CLOSE_BREAKER_EXPLOSION_RISK"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "ISLANDS_SYNCHRONIZED_GRID_RESTORING" if successful_ties > 0 else "BLACKSTART_PENDING_PHASE_ALIGNMENT"

        return {
            "recovery_status": status,
            "breakers_evaluated": len(tie_breaker_ids),
            "successful_island_merges": successful_ties,
            "synchronization_log": tie_actions,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    blackstart = GridBlackstartSynchronizer()
    # Mocking 3 massive tie-breakers connecting dead power islands. 
    # Breaker 3 is wildly out of phase (3.14 rad vs 0.1 rad); closing it would destroy the substations.
    print("TESTING GRID BLACKSTART CORE:\n", blackstart.evaluate_island_ties(
        ["TIE-PNW-CALIFORNIA", "TIE-TEXAS-EAST", "TIE-NY-QUEBEC"], 
        [60.01, 60.00, 60.05], 
        [0.15, 1.05, 3.14],  # Phases Rad A
        [60.01, 60.00, 60.05], 
        [0.12, 1.10, 0.10]   # Phases Rad B
    ))

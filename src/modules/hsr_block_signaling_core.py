# File Name: hsr_block_signaling_core.py
# Location: /src/modules/
# Subsystem: High-Speed Rail (HSR) Moving Block & Braking Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_hsr_stopping_distance(velocities_kmh: np.ndarray, deceleration_ms2: float) -> np.ndarray:
    """Calculates emergency stopping distances for high-speed trains using kinematic equations."""
    total_trains = velocities_kmh.shape[0]
    stopping_dist_m = np.zeros(total_trains, dtype=np.float64)
    
    for i in prange(total_trains):
        # Convert km/h to m/s
        v_ms = velocities_kmh[i] * (1000.0 / 3600.0)
        
        # d = v^2 / (2a)
        if deceleration_ms2 > 0:
            stopping_dist_m[i] = (v_ms**2) / (2.0 * deceleration_ms2)
            
    return stopping_dist_m

class HSRBlockSignalingCore:
    def __init__(self):
        # Typical emergency deceleration for high-speed rail (e.g., Shinkansen, TGV)
        self.emergency_decel_ms2 = 2.5 
        # Safety buffer added to calculated stopping distance
        self.safety_margin_m = 1000.0 

    def evaluate_line_spacing(self, train_ids: List[str], line_positions_km: List[float], velocities_kmh: List[float]) -> dict:
        print(f"\n[RAIL NETWORK] Evaluating HSR moving-block separation distances...")
        start_time = time.time()
        
        v_arr = np.array(velocities_kmh, dtype=np.float64)
        
        # Calculate how much track each train needs to stop dead
        stopping_distances_m = parallel_calculate_hsr_stopping_distance(v_arr, self.emergency_decel_ms2)
        
        interventions = []
        # Check distance between consecutive trains (assuming sorted by position, front to back)
        for i in range(1, len(train_ids)):
            lead_train_pos_m = line_positions_km[i-1] * 1000.0
            trailing_train_pos_m = line_positions_km[i] * 1000.0
            
            actual_separation_m = lead_train_pos_m - trailing_train_pos_m
            required_separation_m = stopping_distances_m[i] + self.safety_margin_m
            
            if actual_separation_m < required_separation_m:
                interventions.append({
                    "trailing_train": train_ids[i],
                    "lead_train": train_ids[i-1],
                    "actual_separation_m": round(actual_separation_m, 2),
                    "required_separation_m": round(required_separation_m, 2),
                    "action": "AUTOMATIC_TRAIN_PROTECTION_BRAKING_APPLIED"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "ATP_INTERVENTION_REQUIRED" if interventions else "LINE_SPACING_NOMINAL"

        return {
            "network_status": status,
            "trains_tracked": len(train_ids),
            "safety_interventions": interventions,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    rail = HSRBlockSignalingCore()
    # Mocking 3 trains on a line. T-02 is going 300km/h and is too close to T-01.
    print("TESTING HSR SIGNALING CORE:\n", rail.evaluate_line_spacing(
        ["EXP-01", "EXP-02", "EXP-03"], 
        [150.0, 147.0, 120.0], # Positions in KM down the line
        [280.0, 320.0, 250.0]  # Speeds in KM/H
    ))

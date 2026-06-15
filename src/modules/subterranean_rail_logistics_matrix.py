# File Name: subterranean_rail_logistics_matrix.py
# Location: /src/modules/
# Subsystem: Subterranean Rail Switch & Braking Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_train_braking(velocities_ms: np.ndarray, masses_kg: np.ndarray, braking_force_n: float) -> np.ndarray:
    """Calculates emergency dynamic braking distances for heavy rail logistics over multi-core processing."""
    total_trains = velocities_ms.shape[0]
    stopping_distances_m = np.zeros(total_trains, dtype=np.float64)
    
    for i in prange(total_trains):
        if masses_kg[i] <= 0:
            continue
            
        # Newton's second law: a = F/m
        deceleration = braking_force_n / masses_kg[i]
        
        # Kinematic equation: v^2 = u^2 + 2as -> d = u^2 / (2a)
        stopping_distances_m[i] = (velocities_ms[i]**2) / (2.0 * deceleration)
        
    return stopping_distances_m

class SubterraneanRailLogistics:
    def __init__(self):
        # Standard heavy rail dynamic braking force application (~2.5 million Newtons for heavy freight)
        self.max_dynamic_braking_newtons = 2500000.0 

    def evaluate_tunnel_traffic(self, train_ids: List[str], velocities_kmh: List[float], masses_tons: List[float], obstacles_ahead_m: List[float]) -> dict:
        print(f"\n[RAILWAYS] Processing subterranean collision avoidance networks...")
        start_time = time.time()
        
        # Convert inputs to standard scientific units (m/s and kg)
        v_arr = np.array(velocities_kmh, dtype=np.float64) * (1000.0 / 3600.0)
        m_arr = np.array(masses_tons, dtype=np.float64) * 1000.0
        
        stopping_distances = parallel_calculate_train_braking(v_arr, m_arr, self.max_dynamic_braking_newtons)
        
        emergency_brakes_triggered = []
        for i in range(len(train_ids)):
            safe_margin = obstacles_ahead_m[i] - stopping_distances[i]
            
            # If stopping distance exceeds 80% of the available track space, trip the mechanical brakes
            if stopping_distances[i] > (obstacles_ahead_m[i] * 0.8):
                emergency_brakes_triggered.append({
                    "train_id": train_ids[i],
                    "stopping_distance_required_m": round(stopping_distances[i], 2),
                    "track_available_m": obstacles_ahead_m[i],
                    "status": "COLLISION_IMMINENT_BRAKES_TRIPPED"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        grid_status = "CRITICAL_LOGISTICS_HALT" if emergency_brakes_triggered else "RAIL_TRAFFIC_NOMINAL"

        return {
            "network_status": grid_status,
            "trains_monitored": len(train_ids),
            "emergency_interventions": emergency_brakes_triggered,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    rail = SubterraneanRailLogistics()
    # Mocking 2 trains: Train 1 is 5000 tons moving at 60 km/h with a blocked switch 400m ahead.
    print("TESTING RAIL LOGISTICS MATRIX:\n", rail.evaluate_tunnel_traffic(["FREIGHT-A1", "COAL-B2"], [60.0, 25.0], [5000.0, 15000.0], [400.0, 1200.0]))

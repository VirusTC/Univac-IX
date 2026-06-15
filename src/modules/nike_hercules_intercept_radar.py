# File Name: nike_hercules_intercept_radar.py
# Location: /src/modules/
# Subsystem: Nike-Hercules Phased Array & Intercept Geometry Core
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_intercept_vectors(target_x_km: np.ndarray, target_y_km: np.ndarray, target_vx_kms: np.ndarray, target_vy_kms: np.ndarray, missile_speed_kms: float) -> np.ndarray:
    """Vectorizes complex radar geometries to find intercept times for incoming threats."""
    total_targets = target_x_km.shape[0]
    time_to_impact_sec = np.zeros(total_targets, dtype=np.float64)
    
    for i in prange(total_targets):
        # Current distance to target
        dist_km = math.sqrt(target_x_km[i]**2 + target_y_km[i]**2)
        
        # Velocity vector magnitude of target
        target_vel_mag = math.sqrt(target_vx_kms[i]**2 + target_vy_kms[i]**2)
        
        # Simplified closing velocity calculation (assuming direct pursuit for performance)
        closing_velocity = missile_speed_kms - target_vel_mag
        
        if closing_velocity > 0.0:
            time_to_impact_sec[i] = dist_km / closing_velocity
        else:
            time_to_impact_sec[i] = -1.0 # Target is outrunning the interceptor
            
    return time_to_impact_sec

class NikeHerculesRadarCore:
    def __init__(self):
        self.interceptor_speed_kms = 1.15 # Approx Mach 3.3 for a Nike-Hercules

    def process_radar_sweep(self, x_coords: List[float], y_coords: List[float], vx_coords: List[float], vy_coords: List[float]) -> dict:
        print(f"\n[AIR DEFENSE] Sweeping airspace for hostile supersonic signatures...")
        start_time = time.time()
        
        x_arr = np.array(x_coords, dtype=np.float64)
        y_arr = np.array(y_coords, dtype=np.float64)
        vx_arr = np.array(vx_coords, dtype=np.float64)
        vy_arr = np.array(vy_coords, dtype=np.float64)
        
        intercept_times = parallel_calculate_intercept_vectors(x_arr, y_arr, vx_arr, vy_arr, self.interceptor_speed_kms)
        
        threat_locks = []
        for i in range(len(intercept_times)):
            ttc = intercept_times[i]
            if ttc > 0.0 and ttc < 120.0: # If intercept is possible within 2 minutes
                threat_locks.append({
                    "bogie_index": i,
                    "distance_km": round(math.sqrt(x_arr[i]**2 + y_arr[i]**2), 2),
                    "time_to_intercept_sec": round(ttc, 2),
                    "status": "WEAPONS_FREE_AUTHORIZATION"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        defense_condition = "DEFCON_2_ENGAGING" if threat_locks else "DEFCON_4_STABLE"

        return {
            "airspace_status": defense_condition,
            "bogies_tracked": len(x_coords),
            "firing_solutions_generated": len(threat_locks),
            "active_engagements": threat_locks,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    radar = NikeHerculesRadarCore()
    # Mocking 2 targets: Target 0 is 80km out, approaching at 0.5 km/s. Target 1 is retreating.
    print("TESTING AIR DEFENSE RADAR:\n", radar.process_radar_sweep([80.0, -150.0], [45.0, 20.0], [-0.4, -0.9], [-0.3, -0.1]))

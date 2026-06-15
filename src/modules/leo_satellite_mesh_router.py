# File Name: leo_satellite_mesh_router.py
# Location: /src/modules/
# Subsystem: LEO Constellation Laser Mesh Router
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

EARTH_RADIUS_KM = 6371.0

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_laser_line_of_sight(altitudes_km: np.ndarray, angular_separations_rad: np.ndarray) -> np.ndarray:
    """Calculates if the Earth's curvature blocks the laser communication link between two LEO satellites."""
    total_links = altitudes_km.shape[0]
    link_possible = np.zeros(total_links, dtype=np.int32)
    
    for i in prange(total_links):
        r_sat = EARTH_RADIUS_KM + altitudes_km[i]
        
        # Calculate the distance from Earth's center to the closest point of the laser beam
        # using basic trigonometry (assuming circular orbits of same altitude for this proxy)
        closest_approach_km = r_sat * math.cos(angular_separations_rad[i] / 2.0)
        
        # If the closest approach of the laser beam is greater than Earth's radius (+ atmospheric drag buffer), link is open
        if closest_approach_km > (EARTH_RADIUS_KM + 100.0): # 100km atmosphere buffer
            link_possible[i] = 1
        else:
            link_possible[i] = 0
            
    return link_possible

class LEOMeshRouter:
    def __init__(self):
        self.max_laser_range_km = 5000.0

    def evaluate_constellation_links(self, link_ids: List[str], sat_altitudes_km: List[float], separation_angles_deg: List[float]) -> dict:
        print(f"\n[SPACE COMMAND] Evaluating orbital laser cross-links for LEO mesh network...")
        start_time = time.time()
        
        alt_arr = np.array(sat_altitudes_km, dtype=np.float64)
        rad_arr = np.array([math.radians(deg) for deg in separation_angles_deg], dtype=np.float64)
        
        # Execute JIT Math
        los_matrix = parallel_calculate_laser_line_of_sight(alt_arr, rad_arr)
        
        active_links = []
        severed_links = []
        
        for i in range(len(link_ids)):
            if los_matrix[i] == 1:
                active_links.append(link_ids[i])
            else:
                severed_links.append({
                    "link_id": link_ids[i],
                    "reason": "EARTH_CURVATURE_OCCLUSION",
                    "action": "REROUTE_PACKETS_TO_ADJACENT_NODE"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "MESH_INTEGRITY_NOMINAL" if not severed_links else "DYNAMIC_REROUTING_ENGAGED"

        return {
            "constellation_status": status,
            "links_evaluated": len(link_ids),
            "active_laser_links": len(active_links),
            "occluded_links": severed_links,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    router = LEOMeshRouter()
    # Mocking satellite pairs at 550km (Starlink altitude). 
    # Link 3 has a huge 45-degree separation, meaning the laser hits the Earth.
    print("TESTING LEO MESH ROUTER:\n", router.evaluate_constellation_links(
        ["SAT-101<->SAT-102", "SAT-102<->SAT-103", "SAT-101<->SAT-105"], 
        [550.0, 550.0, 550.0], 
        [5.0, 12.0, 45.0] 
    ))

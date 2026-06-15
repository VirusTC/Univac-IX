# File Name: atc_enroute_sector_matrix.py
# Location: /src/modules/
# Subsystem: En-Route Air Traffic Control (ATC) Separation Core
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

EARTH_RADIUS_NM = 3440.069

@njit(cache=True, fastmath=True)
def calculate_haversine_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the great-circle distance between two aircraft in nautical miles."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0)**2
    
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_NM * c

@njit(parallel=True, cache=True, fastmath=True)
def parallel_atc_separation_check(lats: np.ndarray, lons: np.ndarray, alts_ft: np.ndarray) -> np.ndarray:
    """
    Scans an en-route sector for separation minimums.
    Standard RVSM (Reduced Vertical Separation Minima): 1000ft vertical, 5nm horizontal.
    Returns 1 if a violation exists, 0 otherwise.
    """
    total_aircraft = lats.shape[0]
    violation_matrix = np.zeros((total_aircraft, total_aircraft), dtype=np.uint8)

    for i in prange(total_aircraft):
        for j in range(total_aircraft):
            if i == j:
                continue
                
            alt_diff = abs(alts_ft[i] - alts_ft[j])
            
            # If vertically separated, they are safe regardless of horizontal distance
            if alt_diff >= 1000.0:
                continue
                
            dist_nm = calculate_haversine_distance_nm(lats[i], lons[i], lats[j], lons[j])
            
            # If horizontally close AND vertically close -> Separation Violation
            if dist_nm < 5.0:
                violation_matrix[i, j] = 1

    return violation_matrix

class ATCEnrouteSectorMatrix:
    def __init__(self):
        self.sector_id = "ZSE_HIGH_01" # Seattle Center High Altitude

    def process_radar_targets(self, callsigns: List[str], lats: List[float], lons: List[float], alts_ft: List[float]) -> dict:
        print(f"\n[ATC SECTOR] Sweeping en-route sector {self.sector_id} for separation minimums...")
        start_time = time.time()
        
        np_lats = np.array(lats, dtype=np.float64)
        np_lons = np.array(lons, dtype=np.float64)
        np_alts = np.array(alts_ft, dtype=np.float64)
        
        # Execute JIT Math
        violations = parallel_atc_separation_check(np_lats, np_lons, np_alts)
        
        conflicts = []
        for i in range(len(callsigns)):
            for j in range(len(callsigns)):
                if violations[i, j] == 1:
                    conflicts.append({
                        "aircraft_1": callsigns[i],
                        "aircraft_2": callsigns[j],
                        "action": "ISSUE_IMMEDIATE_VECTOR_OR_ALTITUDE_CHANGE"
                    })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "SEPARATION_VIOLATION_DETECTED" if conflicts else "SECTOR_CLEAR"

        # Deduplicate conflicts (A vs B and B vs A are the same conflict)
        unique_conflicts = []
        seen = set()
        for conflict in conflicts:
            pair = tuple(sorted([conflict["aircraft_1"], conflict["aircraft_2"]]))
            if pair not in seen:
                seen.add(pair)
                unique_conflicts.append(conflict)

        return {
            "sector_status": status,
            "aircraft_tracked": len(callsigns),
            "active_conflicts": unique_conflicts,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    atc = ATCEnrouteSectorMatrix()
    # Mocking flights. UAL123 and DAL456 are dangerously close (same lat/lon, 500ft apart).
    print("TESTING ATC ENROUTE MATRIX:\n", atc.process_radar_targets(
        ["UAL123", "DAL456", "AAL789"], 
        [47.5, 47.5, 45.0], 
        [-122.0, -122.0, -120.0], 
        [35000.0, 35500.0, 32000.0]
    ))

# File Name: emergency_broadcast_interlock.py
# Location: /src/modules/
# Subsystem: CONELRAD & Emergency Alert System (EAS) Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_acoustic_coverage(siren_source_db: float, distances_meters: np.ndarray) -> np.ndarray:
    """Uses the inverse square law and atmospheric absorption to calculate siren volume across a city grid."""
    total_zones = distances_meters.shape[0]
    received_db = np.zeros(total_zones, dtype=np.float64)
    
    # Atmospheric absorption coefficient for ~500Hz siren tone (dB per meter)
    alpha = 0.005 
    
    for i in prange(total_zones):
        dist = distances_meters[i]
        if dist < 1.0:
            received_db[i] = siren_source_db
            continue
            
        # Attenuation due to spherical divergence: -20 * log10(r)
        divergence_loss = 20.0 * math.log10(dist)
        # Attenuation due to air absorption
        absorption_loss = alpha * dist
        
        final_db = siren_source_db - divergence_loss - absorption_loss
        received_db[i] = max(0.0, final_db)
        
    return received_db

class EmergencyBroadcastInterlock:
    def __init__(self):
        self.min_warning_threshold_db = 60.0 # Standard ambient city noise level (Sirens must be > 60dB to be heard)

    def trigger_civil_defense_alert(self, alert_code: str, target_zone_distances_m: List[float]) -> dict:
        print(f"\n[CIVIL DEFENSE] Activating EAS Overrides and Acoustic Warning Arrays...")
        start_time = time.time()
        
        # Standard Chrysler Bell Victory Siren outputs ~138 dB at 100 feet (approx 168 dB at source 1m)
        source_db = 168.0 
        
        dist_arr = np.array(target_zone_distances_m, dtype=np.float64)
        
        # Execute JIT Math
        zone_decibels = parallel_calculate_acoustic_coverage(source_db, dist_arr)
        
        zones_effectively_warned = 0
        for db in zone_decibels:
            if db >= self.min_warning_threshold_db:
                zones_effectively_warned += 1

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "eas_status": "BROADCAST_ACTIVE_ALL_BANDS_OVERRIDDEN",
            "alert_code_transmitted": alert_code,
            "acoustic_siren_array": {
                "zones_mapped": len(target_zone_distances_m),
                "zones_with_effective_coverage": zones_effectively_warned,
                "coverage_efficiency_pct": round((zones_effectively_warned / len(target_zone_distances_m)) * 100.0, 2)
            },
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    eas = EmergencyBroadcastInterlock()
    # Mocking distances of various city blocks from the central siren array
    print("TESTING EMERGENCY BROADCAST INTERLOCK:\n", eas.trigger_civil_defense_alert("EAM-NUCLEAR-LAUNCH-DETECTED", [500.0, 1500.0, 3000.0, 8000.0]))

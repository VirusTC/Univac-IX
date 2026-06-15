# File Name: sbirs_early_warning_matrix.py
# Location: /src/modules/
# Subsystem: Space-Based Infrared System (SBIRS) Early Warning Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_evaluate_thermal_blooms(sensor_temperatures_k: np.ndarray, background_temps_k: np.ndarray) -> np.ndarray:
    """Evaluates orbital infrared sensor telemetry to isolate extreme thermal gradients."""
    total_scans = sensor_temperatures_k.shape[0]
    threat_confidence = np.zeros(total_scans, dtype=np.float64)
    
    for i in prange(total_scans):
        temp_delta = sensor_temperatures_k[i] - background_temps_k[i]
        
        # Solid rocket boosters (ICBMs) burn at approx 2500K - 3500K
        # If the delta is extreme, confidence approaches 100%
        if temp_delta > 2000.0:
            threat_confidence[i] = min(100.0, (temp_delta / 3000.0) * 100.0)
        else:
            threat_confidence[i] = 0.0
            
    return threat_confidence

class SBIRSEarlyWarningMatrix:
    def __init__(self):
        self.launch_confidence_threshold = 85.0 # Minimum confidence % to trigger a DEFCON escalation

    def process_infrared_constellation(self, sector_ids: List[str], sensor_temps_k: List[float], background_k: List[float]) -> dict:
        print(f"\n[STRATEGIC COMMAND] Processing orbital infrared telemetry for launch plumes...")
        start_time = time.time()
        
        s_arr = np.array(sensor_temps_k, dtype=np.float64)
        b_arr = np.array(background_k, dtype=np.float64)
        
        # Execute JIT Math
        confidence_scores = parallel_evaluate_thermal_blooms(s_arr, b_arr)
        
        launches_detected = []
        for i in range(len(sector_ids)):
            if confidence_scores[i] >= self.launch_confidence_threshold:
                launches_detected.append({
                    "sector": sector_ids[i],
                    "peak_temperature_k": round(sensor_temps_k[i], 1),
                    "threat_confidence_pct": round(confidence_scores[i], 2),
                    "action": "FLASH_OVERRIDE_NORAD"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "STRATEGIC_LAUNCH_DETECTED" if launches_detected else "GLOBAL_THERMAL_BASELINE_STABLE"

        return {
            "orbital_defense_status": status,
            "sectors_scanned": len(sector_ids),
            "launch_events": launches_detected,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    sbirs = SBIRSEarlyWarningMatrix()
    # Mocking 3 global sectors. Sector 2 (e.g., Siberia) spikes to 3200 Kelvin against a 250K background.
    print("TESTING SBIRS EARLY WARNING MATRIX:\n", sbirs.process_infrared_constellation(
        ["SECTOR-US-EAST", "SECTOR-AS-NORTH", "SECTOR-EU-WEST"], 
        [295.0, 3200.0, 280.0], 
        [290.0, 250.0, 275.0]
    ))

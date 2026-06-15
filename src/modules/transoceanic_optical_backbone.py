# File Name: transoceanic_optical_backbone.py
# Location: /src/modules/
# Subsystem: Trans-Oceanic Submarine Cable & Optical Backbone Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_optical_attenuation(distances_km: np.ndarray, base_db_loss_per_km: float) -> np.ndarray:
    """Calculates signal degradation (dB) over vast stretches of single-mode fiber optic cables."""
    total_links = distances_km.shape[0]
    signal_loss_db = np.zeros(total_links, dtype=np.float64)
    
    for i in prange(total_links):
        signal_loss_db[i] = distances_km[i] * base_db_loss_per_km
        
    return signal_loss_db

class TransoceanicOpticalBackbone:
    def __init__(self):
        # Standard loss for 1550nm single-mode fiber is ~0.2 dB/km
        self.fiber_attenuation_db_km = 0.2
        # Max acceptable loss before the EDFA repeaters fail to amplify the signal cleanly
        self.max_link_budget_db = 45.0

    def evaluate_submarine_cables(self, cable_ids: List[str], link_distances_km: List[float], measured_loss_db: List[float]) -> dict:
        print(f"\n[TELECOM] Sweeping Trans-Oceanic optical backbones for structural integrity...")
        start_time = time.time()
        
        dist_arr = np.array(link_distances_km, dtype=np.float64)
        
        # Execute JIT Math
        expected_losses_db = parallel_calculate_optical_attenuation(dist_arr, self.fiber_attenuation_db_km)
        
        severed_lines = []
        tapped_lines = []
        
        for i in range(len(cable_ids)):
            actual = measured_loss_db[i]
            expected = expected_losses_db[i]
            
            # Massive sudden loss implies the cable was cut (anchor, submarine landslide, sabotage)
            if actual > self.max_link_budget_db or actual > (expected * 1.5):
                severed_lines.append(cable_ids[i])
            
            # Micro-bending or physical tapping inserts a small, unaccounted-for dB loss (espionage)
            elif actual > (expected + 1.5):
                tapped_lines.append({
                    "cable_id": cable_ids[i],
                    "unaccounted_loss_db": round(actual - expected, 2),
                    "status": "SUSPECTED_PHYSICAL_INTERCEPTION"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "BACKBONE_SECURE"
        if tapped_lines: status = "ESPIONAGE_WARNING_TAPPING_DETECTED"
        if severed_lines: status = "CRITICAL_CABLE_SEVERANCE_DETECTED"

        return {
            "network_status": status,
            "submarine_cables_monitored": len(cable_ids),
            "severed_cables": severed_lines,
            "security_alerts": tapped_lines,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    telecom = TransoceanicOpticalBackbone()
    # Mocking Trans-Atlantic/Pacific lines. Cable 2 has a massive cut. Cable 3 has a suspicious 2dB micro-bend.
    print("TESTING OPTICAL BACKBONE:\n", telecom.evaluate_submarine_cables(
        ["SEA-ME-WE-3", "FASTER-CABLE", "TAT-14"], 
        [150.0, 200.0, 100.0], # Distances between repeaters
        [30.0, 85.0, 22.5]     # Measured DB loss
    ))

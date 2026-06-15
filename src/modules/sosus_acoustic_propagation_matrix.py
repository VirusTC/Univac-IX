# File Name: sosus_acoustic_propagation_matrix.py
# Location: /src/modules/
# Subsystem: SOSUS Hydrophone Array & Acoustic Thermocline Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_sound_speed(temps_c: np.ndarray, salinities_ppt: np.ndarray, depths_m: np.ndarray) -> np.ndarray:
    """Uses a modified Mackenzie equation to calculate the speed of sound in seawater (m/s) across a massive hydrophone array."""
    total_nodes = temps_c.shape[0]
    sound_speeds = np.zeros(total_nodes, dtype=np.float64)
    
    for i in prange(total_nodes):
        T = temps_c[i]
        S = salinities_ppt[i]
        D = depths_m[i]
        
        # Mackenzie equation coefficients for underwater acoustics
        c = (1448.96 + 4.591 * T - 0.05304 * T**2 + 2.374e-4 * T**3 + 
             1.340 * (S - 35.0) + 0.0163 * D + 1.675e-7 * D**2 - 
             0.01025 * T * (S - 35.0) - 7.139e-13 * T * D**3)
        
        sound_speeds[i] = c
        
    return sound_speeds

class SOSUSAcousticMatrix:
    def __init__(self):
        self.anomaly_threshold_knots = 15.0 # Speed threshold for suspicious acoustic tracking

    def process_hydrophone_telemetry(self, array_id: str, temps_c: List[float], salinities_ppt: List[float], depths_m: List[float], acoustic_signatures_db: List[float]) -> dict:
        print(f"\n[SONAR] Processing SOSUS hydrophone array telemetry for {array_id}...")
        start_time = time.time()
        
        t_arr = np.array(temps_c, dtype=np.float64)
        s_arr = np.array(salinities_ppt, dtype=np.float64)
        d_arr = np.array(depths_m, dtype=np.float64)
        sig_arr = np.array(acoustic_signatures_db, dtype=np.float64)
        
        # Calculate local sound speed profiles to identify the Deep Sound Channel (SOFAR channel)
        sound_speeds = parallel_calculate_sound_speed(t_arr, s_arr, d_arr)
        
        anomalies_detected = []
        for i in range(len(sig_arr)):
            # If a high-decibel transient is detected where sound speed enables long-range propagation
            if sig_arr[i] > 110.0 and sound_speeds[i] < 1490.0:
                anomalies_detected.append({
                    "sensor_index": i,
                    "depth_m": d_arr[i],
                    "sound_speed_m_s": round(sound_speeds[i], 2),
                    "signature_db": sig_arr[i]
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "SUBMARINE_CAVITATION_DETECTED" if anomalies_detected else "OCEAN_BASIN_CLEAR"

        return {
            "status": status,
            "hydrophone_array_id": array_id,
            "nodes_processed": len(temps_c),
            "deep_sound_channel_anomalies": anomalies_detected,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    sosus = SOSUSAcousticMatrix()
    # Mocking a hydrophone array drop. Sensor 2 sits in the SOFAR channel with a loud acoustic signature.
    print("TESTING SOSUS ACOUSTIC MATRIX:\n", sosus.process_hydrophone_telemetry(
        "GIUK-GAP-ALPHA",
        [15.0, 10.0, 4.0, 2.0], 
        [35.0, 35.0, 35.0, 35.0], 
        [50.0, 200.0, 1000.0, 2500.0], 
        [60.0, 65.0, 115.5, 55.0]
    ))

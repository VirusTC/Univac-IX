# File Name: transcontinental_pipeline_core.py
# Location: /src/modules/
# Subsystem: Trans-Continental Pipeline Fluid Dynamics Core
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_pressure_drop(flow_velocity_ms: np.ndarray, lengths_m: np.ndarray, diameter_m: float, friction_factor: float, density_kg_m3: float) -> np.ndarray:
    """Uses the Darcy-Weisbach equation to calculate expected pressure loss (Pascals) across long pipe segments."""
    total_segments = flow_velocity_ms.shape[0]
    expected_pressure_drop_pa = np.zeros(total_segments, dtype=np.float64)
    
    for i in prange(total_segments):
        # Darcy-Weisbach: Delta_P = f * (L/D) * (rho * v^2 / 2)
        kinetic_pressure = 0.5 * density_kg_m3 * (flow_velocity_ms[i]**2)
        pipe_factor = lengths_m[i] / diameter_m
        
        expected_pressure_drop_pa[i] = friction_factor * pipe_factor * kinetic_pressure
        
    return expected_pressure_drop_pa

class TranscontinentalPipelineCore:
    def __init__(self):
        # Typical values for heavy crude oil in a 48-inch pipeline
        self.pipe_diameter_m = 1.22 
        self.fluid_density_kg_m3 = 870.0
        self.friction_factor = 0.015 # Approximated turbulent friction

    def evaluate_pipeline_integrity(self, segment_ids: List[str], lengths_km: List[float], flow_velocities_ms: List[float], measured_pressure_drop_mpa: List[float]) -> dict:
        print(f"\n[ENERGY ARTERIES] Sweeping trans-continental pipeline pressure differentials...")
        start_time = time.time()
        
        len_m_arr = np.array(lengths_km, dtype=np.float64) * 1000.0
        vel_arr = np.array(flow_velocities_ms, dtype=np.float64)
        
        # Execute JIT Math
        expected_drop_pa = parallel_calculate_pressure_drop(vel_arr, len_m_arr, self.pipe_diameter_m, self.friction_factor, self.fluid_density_kg_m3)
        
        ruptures = []
        for i in range(len(segment_ids)):
            expected_mpa = expected_drop_pa[i] / 1000000.0
            actual_mpa = measured_pressure_drop_mpa[i]
            
            # If actual pressure drop is significantly higher than theoretical friction, fluid is escaping
            differential = actual_mpa - expected_mpa
            if differential > 0.5: # 0.5 MPa unexpected loss (~72 PSI)
                ruptures.append({
                    "segment": segment_ids[i],
                    "expected_loss_mpa": round(expected_mpa, 3),
                    "actual_loss_mpa": round(actual_mpa, 3),
                    "action": "TRIP_EMERGENCY_ISOLATION_VALVES"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "PIPELINE_INTEGRITY_COMPROMISED" if ruptures else "FLOW_NOMINAL"

        return {
            "network_status": status,
            "segments_monitored": len(segment_ids),
            "rupture_events": ruptures,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    pipeline = TranscontinentalPipelineCore()
    # Mocking 3 segments. Segment 2 has a massive unexplained pressure drop indicating a leak/rupture.
    print("TESTING PIPELINE CORE:\n", pipeline.evaluate_pipeline_integrity(
        ["KEYSTONE-01", "KEYSTONE-02", "KEYSTONE-03"], 
        [50.0, 50.0, 50.0], 
        [2.5, 2.5, 2.5], 
        [0.45, 1.20, 0.46]
    ))

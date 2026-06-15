# File Name: transcontinental_vactrain_matrix.py
# Location: /src/modules/
# Subsystem: Trans-Continental Vactrain (Hyperloop) Diagnostics Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_vactrain_drag(velocities_kmh: np.ndarray, tube_pressures_pa: np.ndarray) -> np.ndarray:
    """Calculates instantaneous aerodynamic drag forces on Maglev pods within near-vacuum tubes."""
    total_pods = velocities_kmh.shape[0]
    drag_forces_n = np.zeros(total_pods, dtype=np.float64)
    
    # Specific gas constant for air (J/kg*K) and assumed tube temp (293K)
    R_air = 287.05
    temp_k = 293.15
    
    # Frontal area of the pod (m^2) and aerodynamic drag coefficient
    area_m2 = 4.5
    cd = 0.8
    
    for i in prange(total_pods):
        v_ms = velocities_kmh[i] * (1000.0 / 3600.0)
        
        # Calculate air density (rho = P / R*T) using the current tube pressure
        rho = tube_pressures_pa[i] / (R_air * temp_k)
        
        # Drag Equation: Fd = 0.5 * rho * v^2 * Cd * A
        drag_forces_n[i] = 0.5 * rho * (v_ms**2) * cd * area_m2
        
    return drag_forces_n

class TranscontinentalVactrainMatrix:
    def __init__(self):
        # Normal operating vacuum is ~100 Pascals (0.001 Atmospheres)
        # If drag force exceeds 50,000 Newtons, the magnetic levitation fails and the pod crashes
        self.critical_drag_force_n = 50000.0 

    def evaluate_vacuum_kinematics(self, pod_ids: List[str], speeds_kmh: List[float], section_pressures_pa: List[float]) -> dict:
        print(f"\n[TRANSIT NETWORK] Sweeping trans-continental vacuum tubes for micro-fractures...")
        start_time = time.time()
        
        v_arr = np.array(speeds_kmh, dtype=np.float64)
        p_arr = np.array(section_pressures_pa, dtype=np.float64)
        
        # Execute JIT Math
        drag_loads = parallel_calculate_vactrain_drag(v_arr, p_arr)
        
        emergency_brakes = []
        for i in range(len(pod_ids)):
            if drag_loads[i] > self.critical_drag_force_n:
                emergency_brakes.append({
                    "pod_id": pod_ids[i],
                    "aerodynamic_drag_newtons": round(drag_loads[i], 2),
                    "tube_pressure_pa": section_pressures_pa[i],
                    "action": "ATMOSPHERIC_BREACH_ENGAGE_EMERGENCY_MAGNETIC_BRAKING"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "CATASTROPHIC_DEPRESSURIZATION_DETECTED" if emergency_brakes else "VACUUM_SEAL_NOMINAL"

        return {
            "network_status": status,
            "pods_tracked": len(pod_ids),
            "interventions": emergency_brakes,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    vactrain = TranscontinentalVactrainMatrix()
    # Mocking pods traveling at Mach 1.5 (~1800 km/h). 
    # Pod 2 enters a tube section with a micro-fracture (pressure spiked to 5000 Pascals).
    print("TESTING VACTRAIN MATRIX:\n", vactrain.evaluate_vacuum_kinematics(
        ["POD-NY-LA-01", "POD-NY-LA-02", "POD-CHI-MIA-03"], 
        [1850.0, 1850.0, 1200.0], 
        [100.0, 5000.0, 120.0]
    ))

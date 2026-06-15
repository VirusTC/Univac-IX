# File Name: tokamak_plasma_containment_core.py
# Location: /src/modules/
# Subsystem: Tokamak Fusion Reactor & Magnetic Confinement Core
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_plasma_beta(temps_kev: np.ndarray, densities_m3: np.ndarray, b_fields_tesla: np.ndarray) -> np.ndarray:
    """Calculates Plasma Beta (β) across multiple sectors of a Tokamak magnetic bottle."""
    total_sectors = temps_kev.shape[0]
    beta_values = np.zeros(total_sectors, dtype=np.float64)
    
    # Constants
    mu_0 = 1.25663706e-6 # Magnetic permeability of free space (T*m/A)
    ev_to_joules = 1.60218e-16 # Conversion for KeV (kilo-electron volts) to Joules
    
    for i in prange(total_sectors):
        # 1. Calculate Kinetic Plasma Pressure (p = n * k_B * T)
        # Using KeV directly simplifies k_B out of the equation
        plasma_pressure_pa = densities_m3[i] * (temps_kev[i] * 1000.0 * ev_to_joules)
        
        # 2. Calculate Magnetic Pressure (p_mag = B^2 / 2*mu_0)
        magnetic_pressure_pa = (b_fields_tesla[i] ** 2) / (2.0 * mu_0)
        
        # 3. Plasma Beta = Plasma Pressure / Magnetic Pressure
        if magnetic_pressure_pa > 0:
            beta_values[i] = plasma_pressure_pa / magnetic_pressure_pa
        else:
            beta_values[i] = 1.0 # Instant breach if magnetic field drops to 0
            
    return beta_values

class TokamakContainmentCore:
    def __init__(self):
        # The Troyon Limit: If Beta exceeds ~5%, plasma instabilities cause a containment breach
        self.troyon_beta_limit = 0.05 

    def evaluate_magnetic_bottle(self, sector_ids: List[str], temperatures_kev: List[float], plasma_densities: List[float], magnetic_fields_t: List[float]) -> dict:
        print(f"\n[FUSION CORE] Evaluating magnetic containment and Plasma Beta limits...")
        start_time = time.time()
        
        t_arr = np.array(temperatures_kev, dtype=np.float64)
        n_arr = np.array(plasma_densities, dtype=np.float64)
        b_arr = np.array(magnetic_fields_t, dtype=np.float64)
        
        # Execute JIT Math
        betas = parallel_calculate_plasma_beta(t_arr, n_arr, b_arr)
        
        breaches = []
        for i in range(len(sector_ids)):
            if betas[i] >= self.troyon_beta_limit:
                breaches.append({
                    "reactor_sector": sector_ids[i],
                    "plasma_beta": round(betas[i], 4),
                    "action": "MAGNETIC_BOTTLE_RUPTURE_INITIATE_PLASMA_DUMP"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "CONTAINMENT_FAILED_THERMAL_BREACH" if breaches else "FUSION_IGNITION_STABLE"

        return {
            "reactor_status": status,
            "sectors_monitored": len(sector_ids),
            "average_plasma_beta": round(np.mean(betas), 4),
            "containment_warnings": breaches,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    tokamak = TokamakContainmentCore()
    # Mocking an ITER-class reactor. Sector 3 experiences a dangerous dip in magnetic field (from 5.3T to 2.1T).
    print("TESTING TOKAMAK FUSION CORE:\n", tokamak.evaluate_magnetic_bottle(
        ["TORUS-SEC-1", "TORUS-SEC-2", "TORUS-SEC-3"], 
        [15.0, 15.0, 15.0],        # Temp in KeV (~150 Million Degrees C)
        [1.0e20, 1.0e20, 1.5e20],  # Plasma density (particles/m^3)
        [5.3, 5.3, 2.1]            # Magnetic Field in Tesla
    ))

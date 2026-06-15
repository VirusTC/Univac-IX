# File Name: strategic_desalination_governor.py
# Location: /src/modules/
# Subsystem: Strategic Desalination & Reverse Osmosis Governor
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_osmotic_pressure(salinities_molar: np.ndarray, temps_k: np.ndarray) -> np.ndarray:
    """Calculates the osmotic pressure (Atmospheres) required to separate fresh water from brine."""
    total_arrays = salinities_molar.shape[0]
    osmotic_pressures_atm = np.zeros(total_arrays, dtype=np.float64)
    
    # Ideal Gas Constant (L·atm / K·mol)
    R = 0.0821 
    # Van 't Hoff factor for NaCl (approx 2 ions: Na+ and Cl-)
    i_factor = 2.0 
    
    for i in prange(total_arrays):
        # Osmotic Pressure Formula: Π = i * M * R * T
        pressure = i_factor * salinities_molar[i] * R * temps_k[i]
        osmotic_pressures_atm[i] = pressure
        
    return osmotic_pressures_atm

class StrategicDesalinationGovernor:
    def __init__(self):
        # Max safe operating pressure for standard spiral-wound RO membranes (~1200 psi / 81 atm)
        self.membrane_rupture_limit_atm = 81.0

    def evaluate_ro_plant_telemetry(self, array_ids: List[str], salinities_mol_L: List[float], inlet_temps_c: List[float], applied_pressures_atm: List[float]) -> dict:
        print(f"\n[HYDROLOGY] Sweeping municipal desalination arrays and osmotic pressures...")
        start_time = time.time()
        
        # Convert C to Kelvin
        temps_k_arr = np.array(inlet_temps_c, dtype=np.float64) + 273.15
        salinity_arr = np.array(salinities_mol_L, dtype=np.float64)
        
        # Execute JIT Math
        theoretical_osmotic_pressures = parallel_calculate_osmotic_pressure(salinity_arr, temps_k_arr)
        
        rupture_warnings = []
        low_yield_warnings = []
        total_freshwater_yield_m3 = 0.0
        
        for i in range(len(array_ids)):
            required_pressure = theoretical_osmotic_pressures[i]
            applied = applied_pressures_atm[i]
            
            # If applied pressure is lower than osmotic pressure, reverse osmosis halts (no fresh water)
            if applied <= required_pressure:
                low_yield_warnings.append(array_ids[i])
            else:
                # Simplified yield estimation based on excess pressure driving the flow
                net_driving_pressure = applied - required_pressure
                total_freshwater_yield_m3 += (net_driving_pressure * 150.0) # Arbitrary plant multiplier
                
            # Check for membrane safety
            if applied > (self.membrane_rupture_limit_atm * 0.95):
                rupture_warnings.append(array_ids[i])

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "DESALINATION_STABLE"
        if low_yield_warnings: status = "FRESHWATER_YIELD_COMPROMISED"
        if rupture_warnings: status = "CRITICAL_MEMBRANE_OVERPRESSURE"

        return {
            "facility_status": status,
            "arrays_monitored": len(array_ids),
            "total_freshwater_yield_m3_hr": round(total_freshwater_yield_m3, 2),
            "rupture_warnings": rupture_warnings,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    water_plant = StrategicDesalinationGovernor()
    # Mocking standard seawater (approx 0.6 Molar NaCl) at 25C. Requires ~29.3 atm to overcome osmosis.
    print("TESTING DESALINATION GOVERNOR:\n", water_plant.evaluate_ro_plant_telemetry(
        ["RO-TRAIN-ALPHA", "RO-TRAIN-BRAVO"], 
        [0.6, 0.62], 
        [25.0, 26.0], 
        [65.0, 80.0] # Bravo is dangerously close to 81 atm rupture limit
    ))

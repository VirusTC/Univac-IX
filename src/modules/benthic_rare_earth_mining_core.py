# File Name: benthic_rare_earth_mining_core.py
# Location: /src/modules/
# Subsystem: Deep-Sea Polymetallic Nodule Harvesting & Lift Hydraulics
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_hydraulic_lift_pressure(depths_m: np.ndarray, nodule_mass_flow_kg_s: np.ndarray, pipe_diameter_m: float) -> np.ndarray:
    """Calculates the massive pump head pressure (MPa) required to lift rare-earth metals 4km to the surface."""
    total_crawlers = depths_m.shape[0]
    required_pressures_mpa = np.zeros(total_crawlers, dtype=np.float64)
    
    # Constants
    gravity = 9.81
    seawater_density = 1025.0 # kg/m^3
    nodule_density = 2000.0 # kg/m^3 (approximate for manganese/cobalt nodules)
    
    for i in prange(total_crawlers):
        # Calculate volume fraction of solids in the pipe based on mass flow
        pipe_area = math.pi * ((pipe_diameter_m / 2.0) ** 2)
        # Simplified slurry density proxy
        slurry_density = seawater_density + (nodule_mass_flow_kg_s[i] / (pipe_area * 5.0)) # Assuming 5m/s lift velocity
        
        # Hydrostatic head pressure of the slurry column
        static_pressure_pa = slurry_density * gravity * depths_m[i]
        
        # Add a 20% friction and dynamic loss penalty for vertical two-phase flow
        total_pressure_pa = static_pressure_pa * 1.20
        
        # Convert Pascals to Megapascals
        required_pressures_mpa[i] = total_pressure_pa / 1000000.0
        
    return required_pressures_mpa

class BenthicMiningOrchestrator:
    def __init__(self):
        # Maximum allowed sediment plume radius to comply with international seabed treaties
        self.max_legal_turbidity_radius_m = 1500.0 
        self.standard_lift_pipe_diameter_m = 0.4 # 40cm riser pipe

    def evaluate_abyssal_harvest(self, crawler_ids: List[str], operating_depths_m: List[float], harvest_rates_kg_s: List[float], plume_radii_m: List[float]) -> dict:
        print(f"\n[RESOURCE COMMAND] Orchestrating Abyssal Benthic Crawlers and Lift Hydraulics...")
        start_time = time.time()
        
        depths_arr = np.array(operating_depths_m, dtype=np.float64)
        flow_arr = np.array(harvest_rates_kg_s, dtype=np.float64)
        
        # Execute JIT Math
        lift_pressures_mpa = parallel_calculate_hydraulic_lift_pressure(depths_arr, flow_arr, self.standard_lift_pipe_diameter_m)
        
        interventions = []
        total_harvest_kg_s = 0.0
        
        for i in range(len(crawler_ids)):
            if plume_radii_m[i] > self.max_legal_turbidity_radius_m:
                interventions.append({
                    "crawler_id": crawler_ids[i],
                    "sediment_plume_radius_m": plume_radii_m[i],
                    "action": "ECOLOGICAL_VIOLATION_HALT_TRACK_MOTORS"
                })
            elif lift_pressures_mpa[i] > 60.0: # If pressure exceeds 60 MPa (~8700 PSI), pumps might cavitate
                interventions.append({
                    "crawler_id": crawler_ids[i],
                    "lift_pressure_mpa": round(lift_pressures_mpa[i], 2),
                    "action": "THROTTLE_NODULE_INTAKE_TO_PREVENT_PUMP_STALL"
                })
            else:
                total_harvest_kg_s += harvest_rates_kg_s[i]

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "ABYSSAL_HARVEST_NOMINAL" if not interventions else "CRAWLER_INTERVENTION_ACTIVE"

        return {
            "fleet_status": status,
            "crawlers_active": len(crawler_ids),
            "total_yield_tons_per_hour": round((total_harvest_kg_s * 3600.0) / 1000.0, 2),
            "fleet_interventions": interventions,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    mining = BenthicMiningOrchestrator()
    # Mocking Clarion-Clipperton Zone operations. Crawler 2 is kicking up a massive 2km sediment cloud.
    print("TESTING BENTHIC MINING CORE:\n", mining.evaluate_abyssal_harvest(
        ["CRAWLER-ALPHA", "CRAWLER-BRAVO", "CRAWLER-CHARLIE"], 
        [4200.0, 4150.0, 4300.0], 
        [25.0, 30.0, 22.0],  # Nodule yield in kg/s
        [800.0, 2100.0, 500.0] # Turbidity plume radius in meters
    ))

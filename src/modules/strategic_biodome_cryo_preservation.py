# File Name: strategic_biodome_cryo_preservation.py
# Location: /src/modules/
# Subsystem: Global Seed Vault Cryogenic Preservation Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_thermal_ingress(ambient_temps_c: np.ndarray, vault_temps_c: np.ndarray, rock_depth_m: float) -> np.ndarray:
    """Calculates thermal heat transfer (Watts) through permafrost into the subterranean vaults."""
    total_vaults = ambient_temps_c.shape[0]
    heat_ingress_watts = np.zeros(total_vaults, dtype=np.float64)
    
    # Thermal conductivity of frozen sandstone/permafrost (W/m*K)
    k_rock = 2.5 
    # Assumed vault surface area exposed to rock (m^2)
    area_m2 = 1500.0 
    
    for i in prange(total_vaults):
        delta_t = ambient_temps_c[i] - vault_temps_c[i]
        if delta_t > 0:
            # Fourier's Law of Thermal Conduction: Q = (k * A * Delta_T) / d
            heat_ingress_watts[i] = (k_rock * area_m2 * delta_t) / rock_depth_m
        else:
            heat_ingress_watts[i] = 0.0
            
    return heat_ingress_watts

class StrategicCryoPreservationCore:
    def __init__(self):
        # Target temperature for indefinite seed viability
        self.target_vault_temp_c = -18.0 
        # Latent heat of vaporization of Liquid Nitrogen (kJ/kg)
        self.ln2_latent_heat_kj_kg = 199.0 

    def evaluate_vault_thermodynamics(self, vault_ids: List[str], ambient_surface_c: List[float], current_vault_c: List[float], permafrost_depth_m: float) -> dict:
        print(f"\n[BIODIVERSITY] Evaluating Global Seed Vault thermodynamic integrity...")
        start_time = time.time()
        
        amb_arr = np.array(ambient_surface_c, dtype=np.float64)
        vlt_arr = np.array(current_vault_c, dtype=np.float64)
        
        # Execute JIT Math
        heat_loads_w = parallel_calculate_thermal_ingress(amb_arr, vlt_arr, permafrost_depth_m)
        
        cooling_actions = []
        total_ln2_required_kg_h = 0.0
        
        for i in range(len(vault_ids)):
            # If the vault is warming above -18C, calculate Liquid Nitrogen required to offset the heat
            if current_vault_c[i] > self.target_vault_temp_c:
                # Watts (J/s) to kJ/h
                heat_load_kj_h = (heat_loads_w[i] * 3600.0) / 1000.0
                
                # kg of LN2 required per hour to negate the heat ingress
                ln2_kg_h = heat_load_kj_h / self.ln2_latent_heat_kj_kg
                total_ln2_required_kg_h += ln2_kg_h
                
                cooling_actions.append({
                    "vault_id": vault_ids[i],
                    "temp_deviation_c": round(current_vault_c[i] - self.target_vault_temp_c, 2),
                    "ln2_injection_rate_kg_h": round(ln2_kg_h, 2),
                    "action": "INITIATE_CRYOGENIC_FLOODING"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "VAULT_WARMING_ACTIVE_COOLING_ENGAGED" if cooling_actions else "CRYO_STASIS_NOMINAL"

        return {
            "facility_status": status,
            "vaults_monitored": len(vault_ids),
            "total_ln2_consumption_kg_h": round(total_ln2_required_kg_h, 2),
            "thermodynamic_interventions": cooling_actions,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    vault = StrategicCryoPreservationCore()
    # Mocking Svalbard vaults at 120m depth. Global warming causes surface temps to hit 10C. Vault 2 begins thawing.
    print("TESTING CRYO-PRESERVATION CORE:\n", vault.evaluate_vault_thermodynamics(
        ["VAULT-ALPHA", "VAULT-BRAVO", "VAULT-CHARLIE"], 
        [10.0, 10.0, 10.0], 
        [-18.5, -16.0, -18.1], # Vault Bravo is warming
        120.0
    ))

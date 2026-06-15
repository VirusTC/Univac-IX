# File Name: orbital_solar_microwave_array.py
# Location: /src/modules/
# Subsystem: Orbital Solar Power Microwave Beaming Matrix
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_beam_divergence(orbital_altitudes_km: np.ndarray, transmission_angles_rad: np.ndarray, beam_frequency_hz: float, transmitter_radius_m: float) -> np.ndarray:
    """Calculates the footprint radius of a microwave beam arriving on Earth from Geostationary Orbit."""
    total_sats = orbital_altitudes_km.shape[0]
    ground_footprint_radii_m = np.zeros(total_sats, dtype=np.float64)
    
    c_speed = 299792458.0
    wavelength_m = c_speed / beam_frequency_hz
    
    for i in prange(total_sats):
        distance_m = orbital_altitudes_km[i] * 1000.0
        
        # Diffraction-limited beam spread (theta = 1.22 * lambda / D)
        # Using simplified Gaussian optics for the beam waist at distance
        beam_divergence_angle = 1.22 * (wavelength_m / (2.0 * transmitter_radius_m))
        
        # Calculate the radius of the beam when it hits the ground
        beam_radius_on_ground_m = distance_m * math.tan(beam_divergence_angle)
        
        # Account for satellite aiming drift (offset from dead center)
        offset_m = distance_m * math.tan(transmission_angles_rad[i])
        
        # Total effective hazard radius
        ground_footprint_radii_m[i] = beam_radius_on_ground_m + offset_m
        
    return ground_footprint_radii_m

class OrbitalSolarMicrowaveArray:
    def __init__(self):
        # The terrestrial receiving antenna (Rectenna) radius in meters
        self.rectenna_radius_m = 5000.0 

    def evaluate_orbital_transmission(self, sat_ids: List[str], altitudes_km: List[float], aiming_errors_deg: List[float], power_gw: List[float]) -> dict:
        print(f"\n[ORBITAL ENERGY] Synchronizing GEO Solar Microwave Transmission Arrays...")
        start_time = time.time()
        
        alt_arr = np.array(altitudes_km, dtype=np.float64)
        rad_err_arr = np.array([math.radians(deg) for deg in aiming_errors_deg], dtype=np.float64)
        
        # 5.8 GHz ISM band microwave transmission, 1000m orbital transmitter dish
        beam_radii_m = parallel_calculate_beam_divergence(alt_arr, rad_err_arr, 5.8e9, 1000.0)
        
        scram_events = []
        total_delivered_gw = 0.0
        
        for i in range(len(sat_ids)):
            # If the beam footprint drifts outside the physical boundaries of the safe rectenna zone
            if beam_radii_m[i] > self.rectenna_radius_m:
                scram_events.append({
                    "satellite_id": sat_ids[i],
                    "beam_footprint_radius_m": round(beam_radii_m[i], 2),
                    "action": "CRITICAL_MISALIGNMENT_SCRAM_MICROWAVE_EMITTERS"
                })
            else:
                # 85% rectenna conversion efficiency
                total_delivered_gw += power_gw[i] * 0.85

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "BEAM_CONTAINMENT_FAILED_SCRAM_ENGAGED" if scram_events else "ORBITAL_TRANSMISSION_LOCKED"

        return {
            "constellation_status": status,
            "satellites_active": len(sat_ids),
            "total_grid_yield_gw": round(total_delivered_gw, 2),
            "safety_interventions": scram_events,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    array = OrbitalSolarMicrowaveArray()
    # Mocking GEO satellites at ~35,786 km. Sat 2 drifts by 0.01 degrees, putting a gigawatt beam into a civilian zone.
    print("TESTING ORBITAL SOLAR ARRAY:\n", array.evaluate_orbital_transmission(
        ["SOLAR-GEO-01", "SOLAR-GEO-02", "SOLAR-GEO-03"], 
        [35786.0, 35786.0, 35786.0], 
        [0.0001, 0.0150, 0.0002], # Aiming error in degrees
        [2.5, 2.5, 2.5]           # Gigawatts beamed
    ))

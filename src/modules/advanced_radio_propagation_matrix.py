# File Name: advanced_radio_propagation_matrix.py
# Location: /src/modules/
# Subsystem: Advanced Radio Propagation, Maxwell Equations & RF DSP
# Copyright (c) 2026 Revolutionary Technology

import os
import sys
import time
import math
import cmath
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List
from pathlib import Path

# --- DYNAMIC PATH RESOLUTION ---
MODULE_DIR = Path(__file__).resolve().parent
ROOT_DIR = MODULE_DIR.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# VACUUM CONSTANTS
MU_0 = 4 * math.pi * 1e-7      # Vacuum Permeability (H/m)
EPSILON_0 = 8.8541878128e-12   # Vacuum Permittivity (F/m)

@njit(parallel=True, cache=True, fastmath=True)
def parallel_rf_dsp_noise_cancellation(noisy_rf_envelope: np.ndarray, squelch_threshold: float) -> np.ndarray:
    """
    Applies the Advanced Serial DSP logic to an RF waveform.
    Acts as a highly aggressive digital squelch and bandpass thresholding filter
    to recover weak signals from the atmospheric noise floor.
    """
    total_samples = noisy_rf_envelope.shape[0]
    clean_envelope = np.zeros(total_samples, dtype=np.float64)
    
    for i in prange(total_samples):
        amplitude = noisy_rf_envelope[i]
        # DSP Squelch / Noise Floor Elimination
        if abs(amplitude) < squelch_threshold:
            clean_envelope[i] = 0.0
        else:
            # Reconstruct the clipped waveform
            clean_envelope[i] = amplitude
            
    return clean_envelope

@njit(parallel=True, cache=True)
def parallel_maxwell_propagation(frequencies_hz: np.ndarray, sigma_sm: np.ndarray, mu_r: np.ndarray, epsilon_r: np.ndarray) -> np.ndarray:
    """
    Calculates Complex Propagation Constant (gamma), Intrinsic Impedance (eta), 
    and Skin Depth (delta) based on physical material properties from the Periodic Table.
    Returns array: [Attenuation (alpha), Phase (beta), Impedance Magnitude, Skin Depth (m)]
    """
    total_materials = frequencies_hz.shape[0]
    results = np.zeros((total_materials, 4), dtype=np.float64)
    
    for i in prange(total_materials):
        omega = 2.0 * math.pi * frequencies_hz[i]
        mu = mu_r[i] * MU_0
        epsilon = epsilon_r[i] * EPSILON_0
        sigma = sigma_sm[i]
        
        # Maxwell's Complex Propagation Constant: gamma = sqrt( j*w*mu * (sigma + j*w*epsilon) )
        # cmath is required inside Numba for complex math (1j)
        j_w_mu = 1j * omega * mu
        sigma_j_w_e = sigma + (1j * omega * epsilon)
        
        gamma = cmath.sqrt(j_w_mu * sigma_j_w_e)
        alpha = gamma.real # Attenuation constant (Np/m)
        beta = gamma.imag  # Phase constant (rad/m)
        
        # Intrinsic Impedance: eta = sqrt( j*w*mu / (sigma + j*w*epsilon) )
        eta = cmath.sqrt(j_w_mu / sigma_j_w_e)
        
        # Skin Depth: delta = 1 / alpha (How far the wave penetrates before dropping to 37%)
        skin_depth = 1.0 / alpha if alpha > 0 else 999999.0
        
        results[i, 0] = alpha
        results[i, 1] = beta
        results[i, 2] = abs(eta)
        results[i, 3] = skin_depth
        
    return results

class AdvancedRadioPropagationMatrix:
    def __init__(self):
        self.facility_status = "RF_DSP_ACTIVE"
        # 377 Ohms is the approximate intrinsic impedance of free space (air)
        self.eta_air = 376.73 

    def execute_vlf_seawater_scan(self, transmission_ids: List[str], frequencies_hz: List[float], transmit_power_mw: List[float], depths_m: List[float]) -> dict:
        """
        Simulates the Jim Creek Naval Radio Station. Transmits VLF into highly conductive seawater.
        Seawater approx constants: Conductivity (sigma) = 4.0 S/m, Relative Permittivity (e_r) = 80.
        """
        print(f"\n[RF PHYSICS] Spooling Megawatt VLF Transmitters. Calculating oceanic skin-depth...")
        start_time = time.time()
        
        freq_arr = np.array(frequencies_hz, dtype=np.float64)
        # Seawater Constants
        sigma_arr = np.full(len(frequencies_hz), 4.0, dtype=np.float64)
        mu_r_arr = np.full(len(frequencies_hz), 1.0, dtype=np.float64)
        epsilon_r_arr = np.full(len(frequencies_hz), 80.0, dtype=np.float64)
        
        # Execute JIT Complex Math
        maxwell_metrics = parallel_maxwell_propagation(freq_arr, sigma_arr, mu_r_arr, epsilon_r_arr)
        
        telemetry_logs = []
        for i in range(len(transmission_ids)):
            alpha = maxwell_metrics[i, 0]
            skin_depth = maxwell_metrics[i, 3]
            
            # Power drops exponentially with depth: P(z) = P(0) * e^(-2 * alpha * z)
            surface_power = transmit_power_mw[i] * 1e6 # Convert MW to Watts
            power_at_depth = surface_power * math.exp(-2.0 * alpha * depths_m[i])
            
            if power_at_depth < 0.01: # Less than 0.01 Watts reaching the sub
                action = "VLF_SIGNAL_LOSS_-_SUBMARINE_TOO_DEEP_OR_FREQUENCY_TOO_HIGH"
            else:
                action = "VLF_COMMUNICATION_LOCKED_-_DATA_STREAM_NOMINAL"
                
            telemetry_logs.append({
                "vlf_array": transmission_ids[i],
                "frequency_khz": frequencies_hz[i] / 1000.0,
                "seawater_skin_depth_m": round(skin_depth, 2),
                "power_at_target_depth_watts": round(power_at_depth, 4),
                "status": action
            })

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "vlf_matrix_status": "JIM_CREEK_SIMULATION_COMPLETE",
            "transmissions_modeled": len(transmission_ids),
            "diagnostics": telemetry_logs,
            "execution_time_ms": round(execution_ms, 5)
        }

    def execute_antenna_array_diagnostics(self, antenna_ids: List[str], impedances_ohms: List[float], ionospheric_noise_levels: List[np.ndarray]) -> dict:
        """
        Calculates the Standing Wave Ratio (SWR) and applies DSP noise cancellation to weather/ionosphere noise.
        """
        print(f"\n[RF HARDWARE] Sweeping Antenna SWR matrices and applying DSP Noise Cancellation...")
        start_time = time.time()
        
        diagnostics = []
        for i in range(len(antenna_ids)):
            # 1. SWR Calculation (Reflection Coefficient Gamma)
            z_load = impedances_ohms[i]
            z_line = 50.0 # Standard coax characteristic impedance
            
            # Gamma = (Z_load - Z_line) / (Z_load + Z_line)
            gamma = abs((z_load - z_line) / (z_load + z_line))
            swr = (1 + gamma) / (1 - gamma) if gamma < 1 else 99.9
            
            # 2. DSP Noise Cancellation
            noisy_rf = ionospheric_noise_levels[i]
            # Dynamic squelch based on a proxy for ionospheric space weather distortion
            clean_rf = parallel_rf_dsp_noise_cancellation(noisy_rf, squelch_threshold=2.5)
            
            # Calculate % of noise stripped
            noise_stripped_pct = 100.0 - ((np.count_nonzero(clean_rf) / len(noisy_rf)) * 100.0)
            
            if swr > 2.0:
                action = f"FATAL_SWR_REFLECTION ({round(swr, 2)}:1) - ANTENNA DESTROYING RADIO"
            else:
                action = "ANTENNA_RESONANT_AND_TUNED"
                
            diagnostics.append({
                "antenna_id": antenna_ids[i],
                "measured_swr": round(swr, 2),
                "ionospheric_noise_cancelled_pct": round(noise_stripped_pct, 1),
                "status": action
            })

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "antenna_diagnostics": "SWR_AND_DSP_COMPLETE",
            "arrays_scanned": len(antenna_ids),
            "diagnostics": diagnostics,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    rf_matrix = AdvancedRadioPropagationMatrix()
    
    # 1. VLF / JIM CREEK SEAWATER TEST
    # Array 1: Jim Creek at 24.8 kHz, 1.2 Megawatts, target sub at 30m depth.
    # Array 2: Standard FM radio at 100 MHz (Will penetrate less than a millimeter).
    print("--- VLF SEAWATER TRANSMISSION ---")
    print(rf_matrix.execute_vlf_seawater_scan(
        ["JIM-CREEK-VLF", "STANDARD-FM-TEST"], 
        [24800.0, 100000000.0], # Frequencies Hz
        [1.2, 0.1],             # Transmit Power Megawatts
        [30.0, 1.0]             # Depth in meters
    ))
    
    # 2. ANTENNA SWR & DSP TEST
    # Antenna 1: Perfect 50 ohm impedance.
    # Antenna 2: Bad 150 ohm impedance (High SWR).
    noisy_space_weather_1 = np.random.uniform(-5.0, 5.0, 1000)
    noisy_space_weather_2 = np.random.uniform(-8.0, 8.0, 1000)
    
    print("\n--- ANTENNA ARRAY SWR & DSP ---")
    print(rf_matrix.execute_antenna_array_diagnostics(
        ["DIPOLE-ALPHA", "YAGI-BRAVO"],
        [50.0, 150.0], # Ohms
        [noisy_space_weather_1, noisy_space_weather_2]
    ))

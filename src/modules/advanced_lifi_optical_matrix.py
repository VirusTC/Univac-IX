# File Name: advanced_lifi_optical_matrix.py
# Location: /src/modules/
# Subsystem: Enterprise LiFi (IEEE 802.11bb), Optical DSP, and Thermal IR
# Copyright (c) 2026 Revolutionary Technology

import os
import sys
import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List
from pathlib import Path

# --- DYNAMIC PATH RESOLUTION ---
MODULE_DIR = Path(__file__).resolve().parent
ROOT_DIR = MODULE_DIR.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# UNIVERSAL CONSTANTS
STEFAN_BOLTZMANN = 5.670374419e-8  # W/(m^2 * K^4)
WIEN_B_CONSTANT = 2.897771955e-3   # m * K
SPEED_OF_LIGHT = 299792458.0       # m/s

@njit(parallel=True, cache=True, fastmath=True)
def parallel_isi_equalization(received_signal_power: np.ndarray, multipath_delay_spread_ns: np.ndarray) -> np.ndarray:
    """
    Simulates a high-speed Digital Signal Processor (DSP) running adaptive equalization.
    It mathematically subtracts blurred, bounced room reflections (Multipath) to recover the 
    direct Line-of-Sight gigabit stream.
    """
    total = received_signal_power.shape[0]
    clean_signals = np.zeros(total, dtype=np.float64)
    
    for i in prange(total):
        # If the multipath delay spread exceeds 30 nanoseconds, the symbols blur too heavily 
        # (Inter-Symbol Interference) for standard equalization to fully recover at gigabit speeds.
        if multipath_delay_spread_ns[i] > 30.0: 
            # DSP struggles, heavy signal degradation
            clean_signals[i] = received_signal_power[i] * 0.45 
        else:
            # DSP successfully filters out the multipath bounces (99% recovery)
            clean_signals[i] = received_signal_power[i] * 0.99 
            
    return clean_signals

@njit(parallel=True, cache=True, fastmath=True)
def parallel_ofdm_gigabit_capacity(bandwidths_hz: np.ndarray, snr_db: np.ndarray) -> np.ndarray:
    """
    Calculates the theoretical maximum optical data rate using the Shannon-Hartley Theorem.
    C = B * log2(1 + SNR)
    """
    total = bandwidths_hz.shape[0]
    capacity_gbps = np.zeros(total, dtype=np.float64)
    
    for i in prange(total):
        # Convert dB to linear Signal-to-Noise Ratio
        snr_linear = 10.0 ** (snr_db[i] / 10.0)
        
        # Calculate raw bits per second
        c_bps = bandwidths_hz[i] * math.log2(1.0 + snr_linear)
        
        # Convert to Gigabits per second
        capacity_gbps[i] = c_bps / 1e9
        
    return capacity_gbps

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_thermal_radiance(temps_k: np.ndarray, emissivity: np.ndarray, areas_m2: np.ndarray) -> np.ndarray:
    """
    Applies the Stefan-Boltzmann Law and Wien's Displacement Law.
    Returns Array: [Total_Radiant_Power_Watts, Peak_Wavelength_um]
    """
    total = temps_k.shape[0]
    results = np.zeros((total, 2), dtype=np.float64)
    
    for i in prange(total):
        t = temps_k[i]
        if t > 0:
            # 1. Total Thermal Energy Blasted: P = e * sigma * A * T^4
            results[i, 0] = emissivity[i] * STEFAN_BOLTZMANN * areas_m2[i] * (t ** 4)
            
            # 2. Peak Infrared Wavelength: lambda = b / T
            # Multiply by 1e6 to convert meters to micrometers (um)
            results[i, 1] = (WIEN_B_CONSTANT / t) * 1e6 
            
    return results

class AdvancedLiFiOpticalMatrix:
    def __init__(self):
        self.facility_status = "OPTICAL_OWC_ACTIVE"
        # Minimum NETD (Noise Equivalent Temp Difference) for high-end military IR
        self.netd_threshold_mk = 20.0 

    def execute_enterprise_lifi_network(self, ap_ids: List[str], client_types: List[str], bandwidths_hz: List[float], 
                                        raw_snr_db: List[float], multipath_delay_ns: List[float]) -> dict:
        """
        Simulates an enterprise IEEE 802.11bb LiFi deployment. 
        Evaluates Micro-LED/VCSEL transceivers, APD receivers, and OFDM gigabit capacity.
        """
        print(f"\n[OPTICAL NETWORK] Modulating VCSEL laser arrays. Executing OFDM Adaptive Equalization...")
        start_time = time.time()
        
        # Arrays for JIT
        bw_arr = np.array(bandwidths_hz, dtype=np.float64)
        snr_arr = np.array(raw_snr_db, dtype=np.float64)
        delay_arr = np.array(multipath_delay_ns, dtype=np.float64)
        
        # 1. Filter out bouncing light (ISI Mitigation)
        clean_snr = parallel_isi_equalization(snr_arr, delay_arr)
        
        # 2. Calculate Gigabit Throughput
        capacities = parallel_ofdm_gigabit_capacity(bw_arr, clean_snr)
        
        diagnostics = []
        for i in range(len(ap_ids)):
            gbps = capacities[i]
            delay = multipath_delay_ns[i]
            
            if delay > 30.0:
                action = f"INTER-SYMBOL_INTERFERENCE_CRITICAL - LIGHT BOUNCING OVER {delay}ns. THROTTLING QAM."
            elif gbps > 1.0:
                action = "MULTIGIGABIT_OFDM_LINK_LOCKED_-_AVALANCHE_PHOTODIODE_NOMINAL"
            else:
                action = "CONNECTION_STABLE_-_STANDARD_THROUGHPUT"
                
            diagnostics.append({
                "access_point": ap_ids[i],
                "client_receiver": client_types[i],
                "multipath_delay_spread_ns": delay,
                "effective_snr_db": round(clean_snr[i], 2),
                "ofdm_throughput_gbps": round(gbps, 3),
                "status": action
            })

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "protocol": "IEEE_802.11bb_LIFI",
            "nodes_orchestrated": len(ap_ids),
            "adaptive_equalization": "ACTIVE",
            "diagnostics": diagnostics,
            "execution_time_ms": round(execution_ms, 5)
        }

    def execute_thermal_surveillance_sweep(self, target_ids: List[str], temperatures_k: List[float], 
                                           emissivity_vals: List[float], areas_m2: List[float]) -> dict:
        """
        Applies Stefan-Boltzmann and Wien's Displacement physics to detect thermal anomalies,
        classifying them into SWIR, MWIR, or LWIR bands.
        """
        print(f"\n[THERMAL SURVEILLANCE] Sweeping Absolute Zero baselines. Calculating target radiant flux...")
        start_time = time.time()
        
        t_arr = np.array(temperatures_k, dtype=np.float64)
        e_arr = np.array(emissivity_vals, dtype=np.float64)
        a_arr = np.array(areas_m2, dtype=np.float64)
        
        thermal_matrix = parallel_calculate_thermal_radiance(t_arr, e_arr, a_arr)
        
        diagnostics = []
        for i in range(len(target_ids)):
            p_watts = thermal_matrix[i, 0]
            peak_um = thermal_matrix[i, 1]
            
            # Determine IR Band Classification
            if peak_um < 3.0:
                band = "SWIR (Short-Wave IR) - High-Temp/Reflective"
            elif peak_um < 8.0:
                band = "MWIR (Mid-Wave IR) - Mechanical/Exhaust"
            else:
                band = "LWIR (Long-Wave IR) - Biological/Ambient"
                
            diagnostics.append({
                "target_signature": target_ids[i],
                "temperature_kelvin": temperatures_k[i],
                "total_radiant_power_watts": f"{p_watts:.2E}",
                "peak_wavelength_um": round(peak_um, 2),
                "optical_band": band
            })

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "surveillance_status": "INFRARED_SCATTER_MAPPED",
            "targets_scanned": len(target_ids),
            "netd_resolution": f"<{self.netd_threshold_mk} mK",
            "diagnostics": diagnostics,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    lifi_matrix = AdvancedLiFiOpticalMatrix()
    
    # 1. ENTERPRISE LIFI TEST (IEEE 802.11bb)
    # AP 1: Perfect line of sight to a laptop dongle.
    # AP 2: FWA (Fixed Wireless Access) shooting through a window.
    # AP 3: Heavy multipath interference (light bouncing around a highly reflective room).
    print("--- LIFI GIGABIT ETHERNET ORCHESTRATOR ---")
    print(lifi_matrix.execute_enterprise_lifi_network(
        ["LIFI_AP_OFFICE", "LIFI_FWA_BRIDGE", "LIFI_AP_WAREHOUSE"],
        ["USB_APD_DONGLE", "EXTERIOR_WINDOW_RECEIVER", "ROBOTIC_FORKLIFT_RX"],
        [200e6, 800e6, 200e6], # Bandwidths (200 MHz to 800 MHz)
        [40.0, 50.0, 35.0],    # Raw SNR (dB)
        [5.0, 2.0, 45.0]       # Multipath delay spread in nanoseconds (Warehouse is bouncing everywhere)
    ))
    
    # 2. THERMAL INFRARED PHYSICS TEST
    # Target 1: Human Body (approx 310K, high emissivity)
    # Target 2: Fighter Jet Engine Exhaust (approx 900K, metal emissivity)
    # Target 3: Drone casing at ambient night temp (approx 280K)
    print("\n--- THERMAL INFRARED SURVEILLANCE ---")
    print(lifi_matrix.execute_thermal_surveillance_sweep(
        ["BIOLOGICAL_ENTITY", "TURBINE_EXHAUST", "AMBIENT_UAV_FRAME"],
        [310.0, 900.0, 280.0], # Temperatures (Kelvin)
        [0.98, 0.40, 0.90],    # Emissivity (Human skin is highly emissive, bare metal is reflective)
        [1.8, 0.5, 0.2]        # Surface Area (m^2)
    ))

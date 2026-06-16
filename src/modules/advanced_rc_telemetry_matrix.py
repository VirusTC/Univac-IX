# File Name: advanced_rc_telemetry_matrix.py
# Location: /src/modules/
# Subsystem: Advanced Radio Control (RC), FSPL, and Actuation Telemetry
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
C_SPEED = 299792458.0          # Speed of Light (m/s)
K_B = 1.380649e-23             # Boltzmann's Constant (J/K)

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_fspl_and_margin(distances_m: np.ndarray, frequencies_hz: np.ndarray, 
                                       transmit_power_dbm: np.ndarray, antenna_gains_db: np.ndarray, 
                                       rx_sensitivity_dbm: np.ndarray) -> np.ndarray:
    """
    Calculates Free-Space Path Loss (FSPL) and the resulting Link Margin.
    FSPL (dB) = 20*log10(d) + 20*log10(f) + 20*log10(4pi/c)
    Returns Array: [FSPL_dB, Received_Power_dBm, Link_Margin_dB]
    """
    total_devices = distances_m.shape[0]
    results = np.zeros((total_devices, 3), dtype=np.float64)
    
    # 20 * log10(4 * pi / c) is a constant factor in the FSPL equation
    fspl_constant = 20.0 * math.log10((4.0 * math.pi) / C_SPEED)
    
    for i in prange(total_devices):
        d = distances_m[i]
        f = frequencies_hz[i]
        
        if d > 0 and f > 0:
            # 1. Calculate Space Loss
            fspl = (20.0 * math.log10(d)) + (20.0 * math.log10(f)) + fspl_constant
            
            # 2. Calculate Received Power (Tx Power + Gains - Path Loss)
            # Assuming antenna_gains_db combines both G_t and G_r
            p_received = transmit_power_dbm[i] + antenna_gains_db[i] - fspl
            
            # 3. Calculate Link Margin (Safety buffer before signal drop)
            link_margin = p_received - rx_sensitivity_dbm[i]
            
            results[i, 0] = fspl
            results[i, 1] = p_received
            results[i, 2] = link_margin
            
    return results

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_thermal_noise(temperatures_k: np.ndarray, bandwidths_hz: np.ndarray) -> np.ndarray:
    """
    Calculates Thermal Noise Power floor. P_N = k_B * T * B.
    Returns Noise Power in dBm.
    """
    total_devices = temperatures_k.shape[0]
    noise_dbm = np.zeros(total_devices, dtype=np.float64)
    
    for i in prange(total_devices):
        # P_N in Watts
        p_n_watts = K_B * temperatures_k[i] * bandwidths_hz[i]
        if p_n_watts > 0:
            # Convert Watts to dBm: 10 * log10(Watts) + 30
            noise_dbm[i] = (10.0 * math.log10(p_n_watts)) + 30.0
            
    return noise_dbm

class TacticalRCMeshTelemetry:
    def __init__(self):
        self.facility_status = "RC_ORCHESTRATOR_ACTIVE"

    def execute_hardware_mapping(self, device_ids: List[str], device_types: List[str], 
                                 distances_m: List[float], frequencies_hz: List[float], 
                                 bandwidths_hz: List[float], temps_k: List[float], 
                                 tx_power_dbm: List[float], rx_sens_dbm: List[float]) -> dict:
        """
        Maps physical RC hardware (PLCs, Servos, Pistons) and calculates if the radio link
        can successfully actuate them based on deep-space/tactical math.
        """
        print(f"\n[RC TELEMETRY] Sweeping FHSS bands. Mapping remote actuation hardware...")
        start_time = time.time()
        
        # Convert to JIT-compatible arrays
        dist_arr = np.array(distances_m, dtype=np.float64)
        freq_arr = np.array(frequencies_hz, dtype=np.float64)
        bw_arr = np.array(bandwidths_hz, dtype=np.float64)
        temp_arr = np.array(temps_k, dtype=np.float64)
        tx_pwr_arr = np.array(tx_power_dbm, dtype=np.float64)
        rx_sens_arr = np.array(rx_sens_dbm, dtype=np.float64)
        
        # Assume a standard baseline gain of +5 dBi for local gear, and massive +120 dBi for deep space
        gains_arr = np.where(dist_arr > 1000000.0, 120.0, 5.0) 

        # Execute Math Arrays
        link_metrics = parallel_calculate_fspl_and_margin(dist_arr, freq_arr, tx_pwr_arr, gains_arr, rx_sens_arr)
        noise_metrics = parallel_calculate_thermal_noise(temp_arr, bw_arr)
        
        diagnostics = []
        for i in range(len(device_ids)):
            fspl = link_metrics[i, 0]
            link_margin = link_metrics[i, 2]
            noise_floor_dbm = noise_metrics[i]
            rx_power = link_metrics[i, 1]
            
            # Check Duty Cycle Proxy for Latency (Assume short 1ms pulses for low latency)
            duty_cycle_pct = (0.001 / (1.0 / bandwidths_hz[i])) * 100.0 if bandwidths_hz[i] > 1000 else 100.0
            
            # Fault Detection Logic
            if link_margin < 0:
                status = f"LINK_DEAD - SIGNAL {-round(link_margin, 1)}dB BELOW SENSITIVITY"
            elif rx_power < noise_floor_dbm:
                status = f"NOISE_FLOOR_COLLISION - SIGNAL DROWNED IN THERMAL/COSMIC NOISE"
            else:
                status = "ACTUATOR_LOCKED - LOW_LATENCY_CONTROL_NOMINAL"
                
            diagnostics.append({
                "hardware_id": device_ids[i],
                "actuator_type": device_types[i],
                "path_loss_db": round(fspl, 2),
                "thermal_noise_floor_dbm": round(noise_floor_dbm, 2),
                "link_margin_db": round(link_margin, 2),
                "status": status
            })

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "orchestrator_status": "DEVICE_MAP_COMPILED",
            "actuators_monitored": len(device_ids),
            "diagnostics": diagnostics,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    rc_matrix = TacticalRCMeshTelemetry()
    
    # MOCK HARDWARE MAPPING TEST
    # 1. Industrial PLC driving a conveyor belt in a local factory (50 meters, 2.4 GHz WiFi band)
    # 2. High-speed Drone Swarm Motor Control (1,000 meters, 900 MHz ExpressLRS band)
    # 3. Mars Rover sample drill piston (54.6 Billion meters, 8 GHz X-Band, Cryogenic 4 Kelvin receiver)
    
    print(rc_matrix.execute_hardware_mapping(
        device_ids=["FACTORY_CONVEYOR_PLC", "DRONE_SWARM_ROTOR_7", "ARES_ROVER_DRILL_PISTON"],
        device_types=["OMRON_PLC_ROUTER", "BRUSHLESS_DC_ESC", "PNEUMATIC_SERVO"],
        distances_m=[50.0, 1000.0, 54600000000.0],
        frequencies_hz=[2.4e9, 900e6, 8e9],
        bandwidths_hz=[200000.0, 500.0, 100.0],  # Deep space requires tiny bandwidths
        temps_k=[295.0, 290.0, 4.0],             # Space receiver cooled to near absolute zero
        tx_power_dbm=[20.0, 30.0, 60.0],         # 100mW local vs 1000W Deep Space
        rx_sens_dbm=[-90.0, -112.0, -140.0]      # Receiver sensitivities
    ))

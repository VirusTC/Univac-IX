# File Name: advanced_bluetooth_spatial_tracker.py
# Location: /src/modules/
# Subsystem: BLE Spatial Tracking & RSSI Multilateration Matrix
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

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_rssi_distance(rssi_values: np.ndarray, tx_power: float, env_factor: float) -> np.ndarray:
    """
    Calculates physical distance in meters from raw Bluetooth RSSI telemetry.
    Equation: d = 10 ^ ((TxPower - RSSI) / (10 * n))
    Where 'n' is the environmental attenuation factor (2.0 for free space, 3.0-4.0 for indoor/walls).
    """
    total_devices = rssi_values.shape[0]
    distances_m = np.zeros(total_devices, dtype=np.float64)
    
    for i in prange(total_devices):
        if rssi_values[i] == 0:
            distances_m[i] = -1.0 # Invalid/Dropped signal
        else:
            # Standard logarithmic distance decay
            distances_m[i] = 10.0 ** ((tx_power - rssi_values[i]) / (10.0 * env_factor))
            
    return distances_m

class UnivacIXSpatialTracker:
    def __init__(self):
        self.facility_status = "BLE_TRACKER_ACTIVE"
        # Standard BLE Tx Power at 1 meter is typically -59 dBm
        self.measured_tx_power_1m = -59.0 
        # Environmental Path Loss Exponent (n) -> 3.0 simulates a busy industrial factory floor
        self.path_loss_exponent = 3.0 

    def execute_spatial_multilateration(self, device_macs: List[str], device_types: List[str], raw_rssi_dbm: List[float]) -> dict:
        """
        Ingests raw BLE telemetry, calculates spatial boundaries, and flags assets that 
        breach physical geofenced perimeters.
        """
        print(f"\n[SPATIAL TRACKER] Sweeping 2.4 GHz ISM Band. Multilaterating Bluetooth low-energy vectors...")
        start_time = time.time()
        
        rssi_arr = np.array(raw_rssi_dbm, dtype=np.float64)
        
        # Execute JIT Math
        distances = parallel_calculate_rssi_distance(rssi_arr, self.measured_tx_power_1m, self.path_loss_exponent)
        
        diagnostics = []
        for i in range(len(device_macs)):
            mac = device_macs[i]
            d_meters = distances[i]
            
            if d_meters < 0:
                action = "SIGNAL_LOST_-_ASSET_TRACKING_FAILED"
            elif d_meters > 50.0:
                action = f"ASSET_BREACH_DETECTED_({round(d_meters, 1)}m)_-_OUTSIDE_GEOFENCE"
            else:
                action = "ASSET_SECURE_-_WITHIN_OPERATIONAL_PERIMETER"
                
            diagnostics.append({
                "hardware_mac": mac,
                "asset_type": device_types[i],
                "raw_rssi_dbm": raw_rssi_dbm[i],
                "calculated_distance_m": round(d_meters, 2),
                "status": action
            })

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "orchestrator_status": "SPATIAL_VECTORS_MAPPED",
            "active_protocol": "BLUETOOTH_5_LE",
            "assets_tracked": len(device_macs),
            "diagnostics": diagnostics,
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    tracker = UnivacIXSpatialTracker()
    
    # MOCK BLUETOOTH ASSET TRACKING
    print(tracker.execute_spatial_multilateration(
        device_macs=["BLE:AA:BB:CC:01", "BLE:AA:BB:CC:02", "BLE:AA:BB:CC:03"],
        device_types=["BIOMETRIC_ID_BADGE", "FORKLIFT_TELEMETRY", "SECURE_TABLET"],
        raw_rssi_dbm=[-65.0, -82.0, -95.0] # -95 dBm is very weak (far away)
    ))

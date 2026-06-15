# File Name: adsb_air_traffic_deconfliction.py
# Location: /src/modules/
# Subsystem: ADS-B Mode-S Air Traffic Deconfliction & TCAS Matrix UPDATED
# Copyright (c) 2026 Revolutionary Technology

import time
import math
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

# Earth parameters for highly accurate aviation physics
EARTH_RADIUS_NM = 3440.069  # Nautical miles
MIN_HORIZONTAL_SEPARATION_NM = 3.0  # 3 Nautical Miles
MIN_VERTICAL_SEPARATION_FT = 1000.0 # 1000 Feet

@njit(cache=True, fastmath=True)
def calculate_haversine_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the great-circle distance between two aircraft in nautical miles."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0)**2
    
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_NM * c

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_collision_matrix(lats: np.ndarray, lons: np.ndarray, alts_ft: np.ndarray) -> np.ndarray:
    """
    Scans a massive array of airborne assets concurrently to find immediate collision threats.
    Returns an NxN matrix of threat levels (0 = Safe, 1 = Proximity Alert, 2 = TCAS Resolution Required).
    """
    total_aircraft = lats.shape[0]
    threat_matrix = np.zeros((total_aircraft, total_aircraft), dtype=np.uint8)

    for i in prange(total_aircraft):
        for j in range(total_aircraft):
            if i == j:
                continue
                
            # Vertical Separation Check (Fastest to compute, eliminates targets quickly)
            alt_diff = abs(alts_ft[i] - alts_ft[j])
            if alt_diff > MIN_VERTICAL_SEPARATION_FT:
                continue
                
            # Horizontal Separation Check (Heavy Math)
            dist_nm = calculate_haversine_distance_nm(lats[i], lons[i], lats[j], lons[j])
            
            if dist_nm < MIN_HORIZONTAL_SEPARATION_NM:
                if alt_diff < (MIN_VERTICAL_SEPARATION_FT * 0.5):
                    threat_matrix[i, j] = 2  # CRITICAL TCAS OVERRIDE REQUIRED
                else:
                    threat_matrix[i, j] = 1  # PROXIMITY ALERT (Traffic Advisory)

    return threat_matrix

class ADSBDeconflictionEngine:
    def __init__(self):
        self.active_airspace_ledger = {}

    def decode_raw_squitter_payload(self, hex_payload: str) -> dict:
        """
        Simulates the extraction of data from a raw 112-bit ADS-B hexadecimal packet.
        In a live environment, this decrypts the CPR formats into floats.
        """
        # Simulated extraction based on standard payload mapping
        icao_hex = hex_payload[2:8].upper()
        # Mocking values dynamically based on the hex string to simulate live decoding
        seed_val = int(icao_hex, 16)
        
        return {
            "icao_address": icao_hex,
            "latitude": 47.0 + ((seed_val % 1000) / 1000.0),   # Bounding near Seattle for testing
            "longitude": -122.0 - ((seed_val % 1000) / 1000.0),
            "altitude_ft": 30000.0 + (seed_val % 5000),
            "velocity_kts": 450.0 + (seed_val % 100)
        }

    def process_airspace_frame(self, raw_adsb_packets: List[str]) -> dict:
        """Ingests raw airspace data, identifies aircraft, and runs the autonomic TCAS matrix."""
        print(f"\n[AEROSPACE] Ingesting {len(raw_adsb_packets)} raw Mode-S Extended Squitters...")
        start_time = time.time()
        
        # 1. Decode all raw payloads
        decoded_assets = []
        for packet in raw_adsb_packets:
            asset = self.decode_raw_squitter_payload(packet)
            decoded_assets.append(asset)
            self.active_airspace_ledger[asset["icao_address"]] = asset
            
        # Extract into Numba arrays
        lats = np.array([a["latitude"] for a in decoded_assets], dtype=np.float64)
        lons = np.array([a["longitude"] for a in decoded_assets], dtype=np.float64)
        alts = np.array([a["altitude_ft"] for a in decoded_assets], dtype=np.float64)
        
        # 2. Execute JIT Compiled 3D Collision Matrix
        threat_matrix = parallel_cpu_collision_matrix(lats, lons, alts)
        
        # 3. Resolve Threats
        tcas_advisories = []
        for i in range(len(decoded_assets)):
            for j in range(len(decoded_assets)):
                if threat_matrix[i, j] == 2:
                    target_a = decoded_assets[i]
                    target_b = decoded_assets[j]
                    
                    # Deterministic TCAS Resolution: Higher altitude climbs, lower altitude descends
                    action_a = "CLIMB" if target_a["altitude_ft"] >= target_b["altitude_ft"] else "DESCEND"
                    
                    tcas_advisories.append({
                        "asset": target_a["icao_address"],
                        "conflict_with": target_b["icao_address"],
                        "advisory": action_a,
                        "separation_alt_ft": abs(target_a["altitude_ft"] - target_b["altitude_ft"])
                    })
                    
        execution_ms = (time.time() - start_time) * 1000.0
        
        return {
            "status": "AIRSPACE_SCANNED",
            "assets_tracked": len(decoded_assets),
            "tcas_resolutions_issued": len(tcas_advisories),
            "advisories": tcas_advisories,
            "execution_time_ms": round(execution_ms, 4)
        }

if __name__ == "__main__":
    engine = ADSBDeconflictionEngine()
    
    # Mocking a batch of raw ADS-B Packets (112-bit hex)
    # The first two are mathematically coerced by the mock decoder to be on a collision course
    mock_packets = [
        "8D40621D58C382D690C8AC2863A7", # Asset 1
        "8D40621D58C382D690C8AC2863A8", # Asset 2 (Nearly identical hex = nearly identical coordinates)
        "8DA05F219B06B6AF189400CBC33F", # Asset 3
        "8DAB47119B06B6AF189400CBC33F"  # Asset 4
    ]
    
    print("======================================================================")
    print("UNIVAC-IX AIR TRAFFIC DECONFLICTION // TCAS RESOLUTION OVERRIDE")
    print("======================================================================")
    
    results = engine.process_airspace_frame(mock_packets)
    
    print(f"\n[RADAR SWEEP] Assets Tracked: {results['assets_tracked']} | Execution Time: {results['execution_time_ms']} ms")
    
    if results['tcas_resolutions_issued'] > 0:
        print("\n !!! TCAS RESOLUTION ADVISORIES GENERATED !!!")
        for adv in results['advisories']:
            print(f" -> ASSET {adv['asset']}: {adv['advisory']} (Conflict: {adv['conflict_with']} | Alt Diff: {adv['separation_alt_ft']} ft)")
    else:
        print("\n -> [NOMINAL] Airspace clear. No separation breaches detected.")

# File Name: industrial_cip_router.py
# Location: /src/modules/
# Subsystem: Comprehensive CIP Router (AB / GE / GM)
# Copyright (c) 2026 Revolutionary Technology

import time
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(cache=True, fastmath=True)
def calculate_crc32_industrial(data_array: np.ndarray) -> int:
    """Calculates a hard deterministic CRC-32 checksum for validating EtherNet/IP CIP packets."""
    crc = 0xFFFFFFFF
    for i in range(data_array.shape[0]):
        crc ^= data_array[i]
        for _ in range(8):
            mask = -(crc & 1)
            crc = (crc >> 1) ^ (0xEDB88320 & mask)
    return ~crc & 0xFFFFFFFF

class IndustrialCIPRouter:
    def __init__(self):
        # Supported industrial architectures and their specific routing nuances
        self.vendors = {
            "ALLEN_BRADLEY": {"header": [0x6F, 0x00], "safe_mode_payload": [0x00, 0x00, 0x00, 0x00]},
            "GENERAL_ELECTRIC": {"header": [0x70, 0x00], "safe_mode_payload": [0xFF, 0xFF, 0xFF, 0xFF]},
            "GENERAL_MOTORS_LAN": {"header": [0x6B, 0x00], "safe_mode_payload": [0x00, 0x00, 0xFF, 0xFF]}
        }
        
        # Standard CIP encapsulation header (Session Handle, Status, Sender Context, Options)
        self.base_cip_encapsulation = [0x14, 0x00, 0x01, 0x02, 0x03, 0x04, 0x00, 0x00, 0x00, 0x00]

    def _build_payload_bytes(self, payload_value: int, byte_length: int = 4) -> List[int]:
        """Dynamically constructs the byte array for a payload based on required length."""
        payload_bytes = []
        for i in range(byte_length - 1, -1, -1):
            payload_bytes.append((payload_value >> (i * 8)) & 0xFF)
        return payload_bytes

    def construct_override_packet(self, vendor: str, register_hex: str, payload_value: int, payload_length_bytes: int = 4) -> dict:
        """Constructs a targeted CIP packet to overwrite a specific PLC memory register."""
        target_vendor = vendor.strip().upper()
        if target_vendor not in self.vendors:
            return {"status": "FAULT", "error": f"Vendor {target_vendor} not supported."}

        vendor_profile = self.vendors[target_vendor]
        
        # Assemble Packet
        reg_int = int(register_hex, 16)
        register_bytes = [(reg_int >> 8) & 0xFF, reg_int & 0xFF]
        payload_bytes = self._build_payload_bytes(payload_value, payload_length_bytes)
        
        full_packet = np.array(
            vendor_profile["header"] + self.base_cip_encapsulation + register_bytes + payload_bytes, 
            dtype=np.uint8
        )
        
        checksum = calculate_crc32_industrial(full_packet)
        packet_hex = "".join([f"{b:02X}" for b in full_packet])

        return {
            "status": "CIP_PACKET_READY",
            "operation": "DIRECT_REGISTER_OVERWRITE",
            "vendor_target": target_vendor,
            "target_register": register_hex,
            "packet_hex_stream": packet_hex,
            "crc32_checksum": hex(checksum),
            "timestamp": time.time()
        }

    def construct_safe_mode_broadcast(self, vendor: str) -> dict:
        """Generates a specialized CIP packet designed to force an entire PLC rack into safe mode."""
        target_vendor = vendor.strip().upper()
        if target_vendor not in self.vendors:
            return {"status": "FAULT", "error": f"Vendor {target_vendor} not supported."}
            
        vendor_profile = self.vendors[target_vendor]
        
        # 0xFFFF is the universal 'Broadcast/All-Registers' target for these CIP implementations
        register_bytes = [0xFF, 0xFF] 
        payload_bytes = vendor_profile["safe_mode_payload"]
        
        full_packet = np.array(
            vendor_profile["header"] + self.base_cip_encapsulation + register_bytes + payload_bytes, 
            dtype=np.uint8
        )
        
        checksum = calculate_crc32_industrial(full_packet)
        packet_hex = "".join([f"{b:02X}" for b in full_packet])
        
        return {
            "status": "CIP_PACKET_READY",
            "operation": "BROADCAST_SAFE_MODE_LOCK",
            "vendor_target": target_vendor,
            "target_register": "0xFFFF (BROADCAST)",
            "packet_hex_stream": packet_hex,
            "crc32_checksum": hex(checksum),
            "timestamp": time.time()
        }

if __name__ == "__main__":
    router = IndustrialCIPRouter()
    
    print("TESTING INDUSTRIAL CIP ROUTER (COMPREHENSIVE):\n")
    
    # Test 1: Direct Register Overwrite
    print("1. Direct Overwrite (Allen-Bradley):")
    overwrite_res = router.construct_override_packet("ALLEN_BRADLEY", "0x4A2C", 9999)
    for k, v in overwrite_res.items():
        print(f"  {k}: {v}")
        
    print("\n2. Safe Mode Broadcast (General Electric):")
    # Test 2: Safe Mode Broadcast
    safe_mode_res = router.construct_safe_mode_broadcast("GENERAL_ELECTRIC")
    for k, v in safe_mode_res.items():
        print(f"  {k}: {v}")

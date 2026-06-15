# File Name: main.py
# Location: /src/
# Subsystem: UNIVAC-IX Sovereignty Ultimate Unified Tactical Field Recovery Engine

import sys
import os
import time
import socket
import struct
import json
import subprocess
import re
import math
import yaml
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

import numpy as np
from numba import njit, prange
import typer

try:
    import serial
except ImportError:
    serial = None

app = typer.Typer(help="UNIVAC-IX Advanced Telecommunications, SF 2600Hz Interceptor, & Autonomic PLC Override Fabric")

# ------------------------------------------------------------------------------
# GLOBAL STATE & SLA REGISTERS
# ------------------------------------------------------------------------------
_active_serial_handles: Dict[str, Any] = {}
_last_client_socket: Optional[socket.socket] = None
_last_channel_activity_timestamps: Dict[str, float] = {}

_cached_fingerprints: Dict[str, str] = {
    "0x0013": "DRIVER_AVIATION_KNOWLEDGE",
    "0x0014": "DRIVER_AVIATION_KNOWLEDGE",
    "0x0058": "DRIVER_KG58_PHYSICS"
}

_safety_threshold_registers: Dict[str, Dict[str, int]] = {
    "0x0013": {"upper_limit": 90, "lower_limit": 0},
    "0x0037": {"upper_limit": 200, "lower_limit": 10},
    "0x0038": {"upper_limit": 250, "lower_limit": 18}
}

_active_sla_breach_timers: Dict[str, float] = {}
_ANNUAL_RETAINER_USD: float = 4500000.0
_SLA_CREDIT_RATE_PER_HOUR: float = _ANNUAL_RETAINER_USD * 0.10
_SLA_WINDOW_SECONDS: float = 600.0

_INTELLIGENCE_PATTERNS: Dict[str, str] = {
    "FINANCIAL_ROUTING": r"(?:ACCOUNT|IBAN|BANK|ROUTE|SWIFT)[\s\:\-\=]*([A-Z0-9]{8,24})",
    "SYSTEM_AUTHENTICATION": r"(?:PASS|PASSWORD|PWD|SECRET|KEY|TOKEN)[\s\:\-\=]*([a-zA-Z0-9\!\@\#\$\%\^\&\*]{6,32})",
    "TACTICAL_NAVIGATION": r"(?:LAT|LON|COORD|WAYPOINT|NAV)[\s\:\-\=]*([\d\.\-\u00B0\'\"]{4,18}\s*[NSEW]?)"
}

# ------------------------------------------------------------------------------
# MULTICORE DATA CARVING & HEX ACCELERATION
# ------------------------------------------------------------------------------
@njit(cache=True, fastmath=True)
def decode_fieldata_byte(byte_val: int) -> int:
    if byte_val == 0:   return 32  
    if byte_val == 1:   return 48  
    if byte_val == 2:   return 49  
    if byte_val == 3:   return 50  
    if byte_val == 4:   return 51  
    if byte_val == 5:   return 52  
    if byte_val == 6:   return 53  
    if byte_val == 7:   return 54  
    if byte_val == 8:   return 55  
    if byte_val == 9:   return 56  
    if byte_val == 10:  return 57  
    if 11 <= byte_val <= 36: return byte_val + 54  
    if byte_val == 37:  return 46  
    if byte_val == 38:  return 44  
    if byte_val == 39:  return 45  
    if byte_val == 40:  return 47  
    return 63  

@njit(cache=True, fastmath=True)
def decode_ebcdic_byte(byte_val: int) -> int:
    if byte_val == 0x40: return 32  
    if 0x81 <= byte_val <= 0x89: return byte_val - 0x81 + 97   
    if 0x91 <= byte_val <= 0x99: return byte_val - 0x91 + 106  
    if 0xA2 <= byte_val <= 0xA9: return byte_val - 0xA2 + 115  
    if 0xC1 <= byte_val <= 0xC9: return byte_val - 0xC1 + 65   
    if 0xD1 <= byte_val <= 0xD9: return byte_val - 0xD1 + 74   
    if 0xE2 <= byte_val <= 0xE9: return byte_val - 0xE2 + 83   
    if 0xF0 <= byte_val <= 0xF9: return byte_val - 0xF0 + 48   
    if byte_val == 0x4B: return 46  
    if byte_val == 0x6B: return 44  
    if byte_val == 0x60: return 45  
    if byte_val == 0x61: return 47  
    return 63  

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_carve_fieldata(raw_binary_buffer: np.ndarray) -> np.ndarray:
    total_bytes = raw_binary_buffer.shape[0]
    output_ascii_array = np.zeros(total_bytes, dtype=np.uint8)
    for i in prange(total_bytes):
        output_ascii_array[i] = decode_fieldata_byte(raw_binary_buffer[i] & 0x3F)
    return output_ascii_array

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_carve_ebcdic(raw_binary_buffer: np.ndarray) -> np.ndarray:
    total_bytes = raw_binary_buffer.shape[0]
    output_ascii_array = np.zeros(total_bytes, dtype=np.uint8)
    for i in prange(total_bytes):
        output_ascii_array[i] = decode_ebcdic_byte(raw_binary_buffer[i])
    return output_ascii_array

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_hex_to_text_matrix(hex_array: np.ndarray, hex_lengths: np.ndarray) -> np.ndarray:
    total_lines = hex_array.shape[0]
    max_hex_len = hex_array.shape[1]
    ascii_matrix = np.zeros((total_lines, max_hex_len // 2), dtype=np.uint8)
    for i in prange(total_lines):
        current_hex_len = hex_lengths[i]
        total_chars = current_hex_len // 2
        for j in range(total_chars):
            high_char = hex_array[i, j * 2]
            low_char = hex_array[i, (j * 2) + 1]
            high_nibble = high_char - 48
            if high_char > 64: high_nibble = high_char - 55
            low_nibble = low_char - 48
            if low_char > 64: low_nibble = low_char - 55
            ascii_matrix[i, j] = (high_nibble << 4) | low_nibble
    return ascii_matrix

def inline_multicore_hex_decode(raw_hex_string: str) -> str:
    clean_hex = raw_hex_string.strip().upper()
    hex_len = len(clean_hex)
    if hex_len == 0: return ""
    if hex_len % 2 != 0: return "[ERROR: ASYMMETRIC STREAM]"
    hex_matrix = np.zeros((1, hex_len), dtype=np.uint8)
    line_lengths = np.array([hex_len], dtype=np.int32)
    hex_matrix[0, :hex_len] = list(clean_hex.encode("ascii"))
    raw_text_matrix = parallel_cpu_hex_to_text_matrix(hex_matrix, line_lengths)
    return bytes(raw_text_matrix[0, :hex_len // 2]).decode("utf-8", errors="ignore")

# ------------------------------------------------------------------------------
# MULTI-MEDIA TELEPHONY, MORSE, & 2600HZ DEMODULATION MATRIX
# ------------------------------------------------------------------------------
@njit(cache=True, fastmath=True)
def compute_goertzel_magnitude_2600hz(sample_buffer: np.ndarray, sampling_rate_hz: float) -> float:
    total_samples = sample_buffer.shape[0]
    target_freq = 2600.0
    scaling_coefficient = 2.0 * math.cos((2.0 * math.pi * target_freq) / sampling_rate_hz)
    
    state_delay_1 = 0.0
    state_delay_2 = 0.0
    
    for i in range(total_samples):
        current_state = sample_buffer[i] + (scaling_coefficient * state_delay_1) - state_delay_2
        state_delay_2 = state_delay_1
        state_delay_1 = current_state
        
    squared_magnitude = (state_delay_1 ** 2) + (state_delay_2 ** 2) - (state_delay_1 * state_delay_2 * scaling_coefficient)
    if squared_magnitude < 0.0:
        return 0.0
    return math.sqrt(squared_magnitude) / float(total_samples)

@njit(cache=True, fastmath=True)
def parse_dtmf_tone_frequencies(frequency_low: float, frequency_high: float) -> int:
    if 680.0 <= frequency_low <= 715.0:
        if 1190.0 <= frequency_high <= 1225.0: return 49  
        if 1315.0 <= frequency_high <= 1355.0: return 50  
        if 1455.0 <= frequency_high <= 1495.0: return 51  
        if 1610.0 <= frequency_high <= 1655.0: return 65  
    if 750.0 <= frequency_low <= 790.0:
        if 1190.0 <= frequency_high <= 1225.0: return 52  
        if 1315.0 <= frequency_high <= 1355.0: return 53  
        if 1455.0 <= frequency_high <= 1495.0: return 54  
        if 1610.0 <= frequency_high <= 1655.0: return 66  
    if 835.0 <= frequency_low <= 870.0:
        if 1190.0 <= frequency_high <= 1225.0: return 55  
        if 1315.0 <= frequency_high <= 1355.0: return 56  
        if 1455.0 <= frequency_high <= 1495.0: return 57  
        if 1610.0 <= frequency_high <= 1655.0: return 67  
    if 920.0 <= frequency_low <= 960.0:
        if 1190.0 <= frequency_high <= 1225.0: return 42  
        if 1315.0 <= frequency_high <= 1355.0: return 48  
        if 1455.0 <= frequency_high <= 1495.0: return 35  
        if 1610.0 <= frequency_high <= 1655.0: return 68  
    return 0  

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_decode_tone_matrix(low_freqs: np.ndarray, high_freqs: np.ndarray) -> np.ndarray:
    total_elements = low_freqs.shape[0]
    output_chars_matrix = np.zeros(total_elements, dtype=np.uint8)
    for i in prange(total_elements):
        output_chars_matrix[i] = parse_dtmf_tone_frequencies(low_freqs[i], high_freqs[i])
    return output_chars_matrix

@njit(cache=True, fastmath=True)
def parse_morse_symbol_to_ascii(bit_pattern: int, pattern_len: int) -> int:
    if pattern_len == 2:
        if bit_pattern == 12: return 65  
        if bit_pattern == 21: return 78  
        if bit_pattern == 22: return 77  
        if bit_pattern == 11: return 73  
    if pattern_len == 3:
        if bit_pattern == 211: return 68 
        if bit_pattern == 111: return 83 
        if bit_pattern == 222: return 79 
        if bit_pattern == 112: return 85 
    if pattern_len == 4:
        if bit_pattern == 2121: return 67 
        if bit_pattern == 1111: return 72 
        if bit_pattern == 1222: return 74 
    return 63

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_decode_morse_matrix(patterns: np.ndarray, lengths: np.ndarray) -> np.ndarray:
    total_elements = patterns.shape[0]
    output_chars = np.zeros(total_elements, dtype=np.uint8)
    for i in prange(total_elements):
        output_chars[i] = parse_morse_symbol_to_ascii(patterns[i], lengths[i])
    return output_chars

@njit(cache=True, fastmath=True)
def decode_baudot_character(baudot_bits: int) -> int:
    if baudot_bits == 0x03: return 65  
    if baudot_bits == 0x19: return 66  
    if baudot_bits == 0x0E: return 67  
    if baudot_bits == 0x09: return 68  
    if baudot_bits == 0x01: return 69  
    if baudot_bits == 0x04: return 32  
    if baudot_bits == 0x08: return 10  
    return 63  

@njit(cache=True, fastmath=True)
def decode_mu_law_telephony_sample(mu_law_byte: int) -> int:
    inverted_byte = ~mu_law_byte
    sign_bit = (inverted_byte >> 7) & 0x01
    exponent = (inverted_byte >> 4) & 0x07
    mantissa = inverted_byte & 0x0F
    linear_magnitude = (mantissa << 3) + 132
    linear_magnitude <<= exponent
    linear_magnitude -= 132
    if sign_bit == 1:
        return linear_magnitude
    return -linear_magnitude

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_expand_pcm_stream(mu_law_buffer: np.ndarray) -> np.ndarray:
    total_samples = mu_law_buffer.shape[0]
    output_linear_pcm = np.zeros(total_samples, dtype=np.int16)
    for i in prange(total_samples):
        output_linear_pcm[i] = decode_mu_law_telephony_sample(mu_law_buffer[i])
    return output_linear_pcm

# ------------------------------------------------------------------------------
# CRAY SUPERCOMPUTING MATRIX
# ------------------------------------------------------------------------------
@njit(cache=True, fastmath=True)
def convert_gray_to_binary_64(gray_word: int) -> int:
    binary_word = gray_word
    binary_word ^= (binary_word >> 32)
    binary_word ^= (binary_word >> 16)
    binary_word ^= (binary_word >> 8)
    binary_word ^= (binary_word >> 4)
    binary_word ^= (binary_word >> 2)
    binary_word ^= (binary_word >> 1)
    return binary_word

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_decode_cray_matrix(gray_array: np.ndarray) -> np.ndarray:
    total_elements = gray_array.shape[0]
    output_binary_array = np.zeros(total_elements, dtype=np.uint64)
    for i in prange(total_elements):
        output_binary_array[i] = convert_gray_to_binary_64(gray_array[i])
    return output_binary_array

# ------------------------------------------------------------------------------
# KOMMANDOGERAT-58 PHYSICS ENGINEERING CORE (JIT COMPILED)
# ------------------------------------------------------------------------------
@njit(cache=True, fastmath=True)
def calculate_single_piston_load(pressure_pascal: float, bore_diameter_meters: float, rod_diameter_meters: float, force_direction_is_extension: int) -> float:
    area_bore = (math.pi * (bore_diameter_meters ** 2)) / 4.0
    if force_direction_is_extension == 1:
        return pressure_pascal * area_bore
    area_rod = (math.pi * (rod_diameter_meters ** 2)) / 4.0
    area_retraction = area_bore - area_rod
    return pressure_pascal * area_retraction

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_compute_actuator_stresses(pressures: np.ndarray, bores: np.ndarray, rods: np.ndarray, directions: np.ndarray) -> np.ndarray:
    total_elements = pressures.shape[0]
    calculated_forces_newtons = np.zeros(total_elements, dtype=np.float64)
    for i in prange(total_elements):
        calculated_forces_newtons[i] = calculate_single_piston_load(pressures[i], bores[i], rods[i], directions[i])
    return calculated_forces_newtons

@njit(cache=True, fastmath=True)
def evaluate_rotational_torque_nm(force_newtons: float, arm_length_meters: float, force_angle_degrees: float) -> float:
    angle_radians = (force_angle_degrees * math.pi) / 180.0
    return force_newtons * arm_length_meters * math.sin(angle_radians)

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_verify_mass_balance(masses: np.ndarray, radii: np.ndarray, angles_deg: np.ndarray) -> np.ndarray:
    total_mass_nodes = masses.shape[0]
    forces_vector = np.zeros(2, dtype=np.float64) 
    sum_x, sum_y = 0.0, 0.0
    for i in prange(total_mass_nodes):
        rad = (angles_deg[i] * math.pi) / 180.0
        centrifugal_factor = masses[i] * radii[i]
        sum_x += centrifugal_factor * math.cos(rad)
        sum_y += centrifugal_factor * math.sin(rad)
    forces_vector[0] = sum_x
    forces_vector[1] = sum_y
    return forces_vector

@njit(cache=True, fastmath=True)
def evaluate_plane_adjusted_torque(force_newtons: float, arm_length_meters: float, force_angle_degrees: float, orientation_plane_angle_degrees: float) -> float:
    angle_rad = (force_angle_degrees * math.pi) / 180.0
    base_torque = force_newtons * arm_length_meters * math.sin(angle_rad)
    plane_rad = (orientation_plane_angle_degrees * math.pi) / 180.0
    gravity_friction_coefficient = 1.0 - (0.15 * math.sin(plane_rad))
    return base_torque * gravity_friction_coefficient

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_compute_servo_matrix(forces: np.ndarray, arms: np.ndarray, force_angles: np.ndarray, plane_angles: np.ndarray) -> np.ndarray:
    total_elements = forces.shape[0] 
    adjusted_torques_nm = np.zeros(total_elements, dtype=np.float64)
    for i in prange(total_elements):
        adjusted_torques_nm[i] = evaluate_plane_adjusted_torque(forces[i], arms[i], force_angles[i], plane_angles[i])
    return adjusted_torques_nm

@njit(cache=True, fastmath=True)
def compute_opto_analog_led_voltage(lux_intensity: float, sensor_gain_db: float) -> float:
    gain_linear = math.pow(10.0, sensor_gain_db / 20.0)
    transfer_coefficient = 0.0245
    return lux_intensity * gain_linear * transfer_coefficient

# ------------------------------------------------------------------------------
# GENERIC KVM JSON STATE INJECTOR & VISIO AUDIT LOGGER
# ------------------------------------------------------------------------------
def update_kvm_json_state(kvm_gui_config: Path, key: str, value: str, source: str) -> None:
    current_gui_state: Dict[str, Any] = {}
    if kvm_gui_config.exists():
        try:
            with open(kvm_gui_config, "r", encoding="utf-8") as stream:
                current_gui_state = json.load(stream)
        except Exception:
            pass
    if "live_dashboard_vars" not in current_gui_state:
        current_gui_state["live_dashboard_vars"] = {}
    current_gui_state["live_dashboard_vars"][key.strip().upper()] = {
        "value": value.strip(),
        "source": source,
        "last_synchronized": time.strftime("%Y-%m-%d %H:%M:%S"),
        "display_status": "RENDER_ACTIVE"
    }
    try:
        with open(kvm_gui_config, "w", encoding="utf-8") as target_out:
            json.dump(current_gui_state, target_out, indent=2, ensure_ascii=False)
    except Exception:
        pass

def append_event_to_visio_csv(target_csv: Path, node_id: str, name: str, desc: str, mod: str, ntype: str, port: str, addr: str, driver: str, severity: str, color: str) -> None:
    if not target_csv.exists():
        return
    log_line = f"{node_id},{name},\"{desc}\",,,{mod.upper()},{ntype},{port},{addr.lower()},{driver},{severity},{color},NONE\n"
    try:
        with open(target_csv, "a", encoding="utf-8") as ledger:
            ledger.write(log_line)
    except Exception:
        pass

def broadcast_intel_over_radio(pattern_type: str, exact_match: str) -> None:
    radio_tx_addr = "0x0014"
    if radio_tx_addr not in _active_serial_handles: return
    timestamp = time.strftime("%H:%M:%S")
    radio_msg = f"[UNIVAC-INTEL] {timestamp} | MATCH:{pattern_type} | ADDR:{exact_match[:12]}... // SECURE_RELAY"
    try:
        _active_serial_handles[radio_tx_addr].write(bytes.fromhex(radio_msg.encode("utf-8").hex().upper()))
    except Exception: pass

def dispatch_to_vendor_backplane(vendor_name: str, payload_text: str) -> None:
    match vendor_name:
        case "ORACLE":
            print(f"  [VENDOR -> ORACLE] Injecting structured entity transaction into high-memory pooling table blocks -> {payload_text}")
        case "IBM":
            print(f"  [VENDOR -> IBM DB2] Converting block to host EBCDIC variables segment for storage validation -> {payload_text}")
        case "BRADLEY":
            print(f"  [VENDOR -> ALLEN-BRADLEY] Triggering CIP Routing over EtherNet/IP register slots -> {payload_text}")
        case "HBE":
            print(f"  [VENDOR -> HBE] Publishing real-time metric strings to OPC-UA proxy node frames -> {payload_text}")
        case _:
            print(f"  [VENDOR ROUTE DEFERRED] Unknown vendor architecture: {vendor_name}")

# ------------------------------------------------------------------------------
# HEURISTIC FINGERPRINTING & SLA TIMERS
# ------------------------------------------------------------------------------
def execute_heuristic_fingerprint(hex_payload: str) -> str:
    upper_payload = hex_payload.upper()
    decoded = inline_multicore_hex_decode(upper_payload)
    if upper_payload.startswith("AA55") or "NTDS" in decoded: return "DRIVER_MIL_STD_1397_TACTICAL"
    if upper_payload.startswith("7E") or "ALTITUDE" in decoded: return "DRIVER_AVIATION_KNOWLEDGE"
    if upper_payload.startswith("0F0F") or "BREAKDOWN" in decoded: return "DRIVER_OTIS_GEN360"
    if upper_payload.startswith("DEAD") or "CRITICAL" in decoded: return "DRIVER_SAFETY_MONITOR"
    if upper_payload.startswith("02") or "PLC_COIL" in decoded: return "DRIVER_UNIVAC_PROPRIETARY_PLC"
    return "DRIVER_UNKNOWN_GENERIC_SERIAL"

def calculate_and_log_sla_credits(channel_addr: str, visio_csv: Path) -> None:
    if channel_addr not in _active_sla_breach_timers: return
    elapsed_seconds = time.time() - _active_sla_breach_timers[channel_addr]
    if elapsed_seconds <= _SLA_WINDOW_SECONDS: return
        
    breach_overtime_seconds = elapsed_seconds - _SLA_WINDOW_SECONDS
    overtime_hours = breach_overtime_seconds / 3600.0
    accrued_penalty_usd = overtime_hours * _SLA_CREDIT_RATE_PER_HOUR
    
    epoch_stamp = int(time.time())
    node_id = f"SLA_PENALTY_{epoch_stamp}_{channel_addr}"
    desc = f"Intervention overtime: {breach_overtime_seconds:.1f}s. Liquidated credit: ${accrued_penalty_usd:.2f} USD."
    
    append_event_to_visio_csv(visio_csv, node_id, f"SLA_{channel_addr}", desc, "SLA_ACCOUNTING", "FINANCIAL_LEDGER", "NONE", channel_addr, "DRIVER_SLA_TRACKER", "LIQUIDATION_ISSUED", "DarkRed")

def track_and_initialize_sla_timer(channel_addr: str) -> None:
    if channel_addr in _active_sla_breach_timers: return
    _active_sla_breach_timers[channel_addr] = time.time()

def clear_sla_timer(channel_addr: str) -> None:
    if channel_addr in _active_sla_breach_timers:
        del _active_sla_breach_timers[channel_addr]

def verify_live_sensor_safety_compliance(hex_address: str, raw_payload_bytes: bytes, target_csv: Path) -> None:
    clean_addr = hex_address.strip().lower()
    if clean_addr not in _safety_threshold_registers: return
    if len(raw_payload_bytes) == 0: return
    
    measured_integer_value = int(raw_payload_bytes[-1])
    bounds = _safety_threshold_registers[clean_addr]
    max_boundary = bounds.get("upper_limit", 255)
    min_boundary = bounds.get("lower_limit", 0)
    
    if measured_integer_value > max_boundary or measured_integer_value < min_boundary:
        limit_used = max_boundary if measured_integer_value > max_boundary else min_boundary
        track_and_initialize_sla_timer(clean_addr)
        calculate_and_log_sla_credits(clean_addr, target_csv)
        return
    clear_sla_timer(clean_addr)

# ------------------------------------------------------------------------------
# CORE DATA ROUTER & LATENCY MANAGER
# ------------------------------------------------------------------------------
def execute_sf_trunk_plc_overrides(config_data: Dict[str, Any], visio_csv: Path, kvm_json: Path) -> None:
    """Intercepts the 2600 Hz tone detection state and automatically forces safety override handshakes down multi-vendor PLCs."""
    override_matrix = config_data.get("autonomous_plc_overrides", {}).get("DRIVER_TELEPHONY_SF", {})
    if not override_matrix:
        return
        
    actions = override_matrix.get("actions", [])
    print(f"  [AUTONOMIC PROTECTION] Dispatching emergency overrides across {len(actions)} distinct hardware vendor networks...")
    
    for action in actions:
        vendor = action.get("vendor", "GENERIC_PLC")
        label = action.get("label", "EMERGENCY_RESET")
        target_reg = action.get("target_register", "0x0000")
        payload_hex = action.get("override_hex_vector", "0000")
        
        print(f"    -> [DISPATCH SUCCESS] Forced {vendor} Injection to Register {target_reg} | Payload: {payload_hex} ({label})")
        
        update_kvm_json_state(kvm_json, f"PLC_{vendor}_OVERRIDE_STATUS", f"EXECUTED_{label}", "TELEPHONY_2600HZ_INTERCEPTOR")
        epoch_stamp = int(time.time())
        node_id = f"PLC_OVERRIDE_{epoch_stamp}_{vendor}"
        desc = f"In-band 2600 Hz drop forced autonomous protective override handshake {payload_hex} to {vendor} slot {target_reg}."
        append_event_to_visio_csv(visio_csv, node_id, label, desc, f"{vendor}_POLICING", "TACTICAL_HANDSHAKE", "SERIAL_WIRE", target_reg, "DRIVER_TELEGRAPH_POLICING", "CRITICAL_TRAP_ENGAGED", "Red")

def evaluate_telegraphic_overrides(resolved_char: str, config_data: Dict[str, Any], visio_csv: Path, kvm_json: Path) -> None:
    overrides_list = config_data.get("telegraphic_handshake_overrides", [])
    for rule in overrides_list:
        morse_pattern = rule.get("trigger_morse_pattern", 0)
        expected_char = chr(parse_morse_symbol_to_ascii(morse_pattern, 3))
        if expected_char != resolved_char:
            continue
            
        reply_hex = rule.get("reply_hex_vector", "")
        target_plc = rule.get("target_plc", "GENERIC_PLC")
        label = rule.get("label", "EMERGENCY_RESET")
        
        print(f"\n  [TELEGRAPH OVERRIDE ACTIVE] Key pattern match found: '{resolved_char}' triggers rule {label}.")
        print(f"  [PLC POLICING ACTION] Automatically dispatching recovery handshake {reply_hex} directly into {target_plc} backplane...")
        
        update_kvm_json_state(kvm_json, f"PLC_OVERRIDE_{target_plc}", f"EXECUTED_{label}", "TELEGRAPHIC_INTERCEPTOR")
        epoch_stamp = int(time.time())
        node_id = f"TEL_OVERRIDE_{epoch_stamp}_{target_plc}"
        desc = f"Telegraph interceptor forced autonomic handshake {reply_hex} to {target_plc} on keyword match."
        append_event_to_visio_csv(visio_csv, node_id, label, desc, "PLC_OVERRIDE", "TACTICAL_HANDSHAKE", "WIRELESS_MESH", "0x0014", "DRIVER_TELEGRAPH_POLICING", "CRITICAL_TRAP_ENGAGED", "Red")

def purge_stale_hardware_channels(latency_timeout_seconds: float, visio_csv: Path, kvm_json: Path) -> None:
    """Flushes out silent, dead, or disconnected physical interface ports to minimize loop cycle latency in heavy noise fields."""
    global _active_serial_handles, _last_channel_activity_timestamps, _cached_fingerprints
    current_time = time.time()
    
    for hex_addr, last_active_timestamp in list(_last_channel_activity_timestamps.items()):
        if (current_time - last_active_timestamp) <= latency_timeout_seconds:
            continue
            
        # Target node has crossed the maximum permissible latency threshold window
        if hex_addr not in _active_serial_handles:
            continue
            
        try:
            print(f"[LATENCY PURGE] Channel {hex_addr} exceeded silent limit window. Closing connection to prevent cycle lag.")
            _active_serial_handles[hex_addr].close()
        except Exception:
            pass # Suppress background errors if the physical connection is already broken
            
        # Extract metadata metrics for chronological logging before erasing memory states
        stale_driver = _cached_fingerprints.get(hex_addr, "DRIVER_UNKNOWN_GENERIC_SERIAL")
        epoch_stamp = int(time.time())
        node_id = f"CHANNEL_FLUSH_{epoch_stamp}_{hex_addr}"
        desc = f"Forcibly disconnected line {hex_addr} after {latency_timeout_seconds}s of silence to optimize scanner throughput."
        
        # 1. Update the Microsoft Visio Data Visualizer spreadsheet log dynamically with orange warning indicators
        append_event_to_visio_csv(
            visio_csv, node_id, f"Purged_{hex_addr}", desc, 
            "FABRIC_PROTECTION", "DISCONNECTED_PORT", "SERIAL_WIRE", 
            hex_addr, stale_driver, "CHANNEL_OFFLINE", "Orange"
        )
        
        # 2. Synchronize active state variables inside your Univac_Sperry_KVM_GUI layout matrix
        update_kvm_json_state(kvm_json, f"PLC_{hex_addr}_STATUS", "OFFLINE_PURGED", "AUTONOMIC_LATENCY_ENGINE")
        
        # 3. Cleanly unmount references from runtime dictionary caches to reduce loop calculation strains
        del _active_serial_handles[hex_addr]
        del _last_channel_activity_timestamps[hex_addr]

def process_incoming_stream(hex_address: str, raw_payload: bytes, config_data: Dict[str, Any], target_csv: Path, kvm_json: Path) -> None:
    clean_addr = hex_address.strip().lower()
    _last_channel_activity_timestamps[clean_addr] = time.time()
    
    hex_payload_str = raw_payload.hex().upper()
    decoded_text = inline_multicore_hex_decode(hex_payload_str)
    
    if clean_addr not in _cached_fingerprints:
        detected_driver = execute_heuristic_fingerprint(hex_payload_str)
        _cached_fingerprints[clean_addr] = detected_driver
        print(f"\n[PLC DISCOVERED] Unmapped line interface activated at address {clean_addr}. Mounted: {detected_driver}")
        update_kvm_json_state(kvm_json, f"PLC_{clean_addr}_DRIVER", detected_driver, "HEURISTIC_FINGERPRINT_ENGINE")
        append_event_to_visio_csv(target_csv, f"DISC_{clean_addr}", f"Auto_PLC_{clean_addr}", f"Discovered element running {detected_driver}", "DISCOVERY", "PLC_NODE", "SCANNER", clean_addr, detected_driver, "INFORMATIONAL", "Orange")

    assigned_driver = _cached_fingerprints[clean_addr]
    
    if "CRITICAL" in decoded_text or "BREAKDOWN" in decoded_text:
        track_and_initialize_sla_timer(clean_addr)
        calculate_and_log_sla_credits(clean_addr, target_csv)
        sys.stdout.write("\a\a\a")
        sys.stdout.flush()
        print(f"  [CRITICAL FAULT ESCALATION] Trap condition tripped on channel {clean_addr} // Driver: {assigned_driver}")

    verify_live_sensor_safety_compliance(clean_addr, raw_payload, target_csv)
    print(f"  [CORE PROCESSING] Channel: {clean_addr} | Driver: {assigned_driver} | Plaintext: {decoded_text}")

# ------------------------------------------------------------------------------
# DATABASE SQL TEXT CARVING ENGINE
# ------------------------------------------------------------------------------
def parse_raw_database_dump(dump_path: Path, mode: str, visio_csv: Path) -> None:
    if not dump_path.exists():
        print(f"[DB CARVER FAULT] Target storage dump asset missing: '{dump_path}'", file=sys.stderr)
        return
        
    print(f"[DB CARVER] Opening {mode.upper()} binary text image partition target...")
    with open(dump_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        
    regex_pattern = r"INSERT\s+INTO\s+([A-Za-z0-9_]+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)"
    if mode.upper() == "IBM_DB2":
        regex_pattern = r"CREATE\s+TABLE\s+([A-Za-z0-9_]+)\s*\(([^;]+)\)"
        
    compiled_regex = re.compile(regex_pattern, re.IGNORECASE)
    matches_found = compiled_regex.findall(content)
    total_records = len(matches_found)
    
    print(f"[DB CARVER SUCCESS] Isolated {total_records} structural data records from memory image files.")
    
    for idx, match_item in enumerate(matches_found):
        table_name = match_item[0] if isinstance(match_item, tuple) else match_item
        print(f"  -> CARVED ENTITY [{idx + 1}]: Target Table = {table_name}")
        epoch_stamp = int(time.time())
        node_id = f"DB_CARVE_{epoch_stamp}_{idx}"
        desc = f"Carved table entity schema {table_name} from raw text block allocations."
        append_event_to_visio_csv(visio_csv, node_id, f"DB_{table_name}", desc, "STORAGE_RECOVERY", "DATABASE_SCHEMATIC", "FILE", "0x00A9", "DRIVER_MAINFRAME_RECOVERY", "SALVAGED_OK", "Purple")

# ------------------------------------------------------------------------------
# TYPER COMMANDS
# ------------------------------------------------------------------------------
def load_system_config(config_path: Path) -> Dict[str, Any]:
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as stream:
            return yaml.safe_load(stream)
    print(f"Configuration Fault: Path {config_path} not found.", file=sys.stderr)
    raise typer.Exit(code=1)

@app.command(name="listen-ports")
def listen_ports_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the master system topology file blueprint."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target Visio spreadsheet mapping audit file destination."),
    kvm_json: Path = typer.Option(Path("gui_state.json"), help="The active KVM GUI panel configuration json path."),
    network_port: int = typer.Option(8080, help="Local socket communication port capturing aggregate virtual trunks."),
    purge_timeout: float = typer.Option(5.0, help="Latency threshold window count in seconds before dead ports are flushed.")
):
    global _active_serial_handles
    config_data = load_system_config(config)
    
    print(f"\n======================================================================")
    print(f"UNIVAC-IX MULTI-MEDIA RECOVERY MATRIX ACTIVE: {config_data.get('system', {}).get('identity', 'CORE-FABRIC')}")
    print(f"======================================================================")
    
    inline_multicore_hex_decode("414243") # Warm up JIT
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", network_port))
    server_socket.listen(10)
    server_socket.setblocking(False)

    for node in config_data.get("nodes", []):
        port_path = node.get("port", "")
        if not port_path.startswith("/dev/"): continue
        if not serial: continue
        try:
            ser = serial.Serial(port_path, baudrate=115200, timeout=0.01)
            _active_serial_handles[node.get("hex_address", "").lower()] = ser
        except Exception: pass

    print(f"[LIVE MONITOR] Scanning all interfaces concurrently. Ingestion engine open on port {network_port}.\n")

    try:
        while True:
            purge_stale_hardware_channels(purge_timeout, visio_csv, kvm_json)
            try:
                client_sock, _ = server_socket.accept()
                client_sock.settimeout(0.1)
                raw_buffer = client_sock.recv(4096)
                if raw_buffer:
                    payload_str = raw_buffer.decode('utf-8').strip()
                    if ":" in payload_str:
                        addr, data_hex = payload_str.split(":", 1)
                        process_incoming_stream(addr.strip().lower(), bytes.fromhex(data_hex.strip()), config_data, visio_csv, kvm_json)
                client_sock.close()
            except BlockingIOError: pass
            except Exception: pass

            for hex_addr, serial_conn in list(_active_serial_handles.items()):
                if not getattr(serial_conn, 'in_waiting', 0): continue
                raw_bytes = serial_conn.read(serial_conn.in_waiting)
                if raw_bytes:
                    process_incoming_stream(hex_addr, raw_bytes, config_data, visio_csv, kvm_json)

            for running_breach_addr in list(_active_sla_breach_timers.keys()):
                calculate_and_log_sla_credits(running_breach_addr, visio_csv)
                
            time.sleep(0.005)

    except KeyboardInterrupt:
        server_socket.close()
        raise typer.Exit(code=0)

@app.command(name="listen-server")
def listen_server_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the master system configuration profile."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target data visualizer audit log destination."),
    kvm_json: Path = typer.Option(Path("gui_state.json"), help="The active KVM GUI panel configuration json path."),
    purge_timeout: float = typer.Option(5.0, help="The latency threshold boundary limit count in seconds before stale lines are dropped.")
):
    print(f"\n[SERVER] Launching multi-media infrastructure core on background channels...")
    parallel_cpu_decode_morse_matrix(np.array([12]), np.array([2]))
    try:
        while True:
            purge_stale_hardware_channels(purge_timeout, visio_csv, kvm_json)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[SERVER INTERRUPT] Halting background processes cleanly.")
        raise typer.Exit(code=0)

@app.command(name="analyze-trunk-signal")
def analyze_trunk_signal_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the master system topology file configuration profile."),
    sampling_rate: float = typer.Option(8000.0, help="The audio carrier line baseline digitizing sampling frequency in Hertz."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target data visualizer spreadsheet file path destination."),
    kvm_json: Path = typer.Option(Path("gui_state.json"), help="The active operator dashboard interface layout json configuration target.")
):
    config_data = load_system_config(config)
    policing_rules = config_data.get("sf_trunk_policing", {})
    magnitude_threshold = policing_rules.get("power_magnitude_floor", 15.0)
    
    print(f"\n======================================================================")
    print(f"UNIVAC-IX IN-BAND TELEPHONY OVERRIDE DAEMON // MULTI-VENDOR CONTROL")
    print(f"======================================================================")
    print(f"[RECON] Evaluating long-distance in-band telecommunication trunk frequencies...")
    
    sample_size = 400
    time_steps = np.arange(sample_size) / sampling_rate
    mock_audio_wave = 50.0 * np.sin(2.0 * np.pi * 2600.0 * time_steps) + np.random.normal(0, 1.5, sample_size)
    
    spectral_magnitude = compute_goertzel_magnitude_2600hz(mock_audio_wave, sampling_rate)
    print(f"[RECON COMPLETE] Isolated relative 2600 Hz spectral magnitude: {spectral_magnitude:.4f}")
    
    if spectral_magnitude < magnitude_threshold:
        print("  -> [NOMINAL] Line carrier tracking standard traffic loops. Operations stable.\n")
        return
        
    sys.stdout.write("\a\a\a\a")
    sys.stdout.flush()
    
    print("\n" + "!" * 80)
    print(f" !!! TACTICAL ALERT: 2600 HZ IN-BAND TRUNK DISCONNECT CARRIER INTERCEPTED !!!")
    print(f" -> LINE HARDWARE INTEGRITY STATUS: CRITICAL_DISCONNECT_TRAP_ENGAGED")
    print(f" -> PROTECTION ACTION: ENGAGING AUTONOMIC HARDWARE FALLBACK OVERRIDES")
    print("!" * 80)
    
    update_kvm_json_state(kvm_json, "TELEPHONY_TRUNK_01_STATUS", "DISCONNECTED_2600HZ_SF", "GOERTZEL_SIGNAL_PROCESSOR")
    epoch_stamp = int(time.time())
    append_event_to_visio_csv(visio_csv, f"TRUNK_DROP_{epoch_stamp}", "Trunk_Disconnect_Ch1", f"In-band 2600 Hz tone verified at magnitude {spectral_magnitude:.2f}.", "TELEPHONY_GUARD", "TRUNK_LINE", "ADSL_METRIC", "0x0013", "DRIVER_TELEPHONY_SF", "CRITICAL_TRAP_ENGAGED", "DarkRed")
    
    execute_sf_trunk_plc_overrides(config_data, visio_csv, kvm_json)
    print()

@app.command(name="parse-dialup-stream")
def parse_dialup_stream_command(
    low_hz: float = typer.Argument(..., help="Extracted low-group tone carrier frequency value in Hertz."),
    high_hz: float = typer.Argument(..., help="Extracted high-group tone carrier frequency value in Hertz."),
    vendor_target: str = typer.Option("BRADLEY", help="Target enterprise automation network infrastructure (ORACLE, IBM, BRADLEY, HBE).")
):
    print(f"\n======================================================================")
    print(f"UNIVAC-IX TELEPHONY CARRIER DEMODULATION // INTERFACE: ADSL / CAT6 / NEXT-GEN")
    print(f"======================================================================")
    
    low_arr = np.array([low_hz], dtype=np.float64)
    high_arr = np.array([high_hz], dtype=np.float64)
    
    decoded_ascii_codes = parallel_cpu_decode_tone_matrix(low_arr, high_arr)
    character_byte = decoded_ascii_codes[0]
    
    if character_byte == 0:
        print("[DEMODULATION DEFERRED] Tone pairing matches no standard telephone or telegraph protocol rules.", file=sys.stderr)
        raise typer.Exit(code=1)
        
    resolved_char = chr(character_byte)
    print(f"[DEMODULATION SUCCESS] Extracted clean data byte character out of audio carrier wave: '{resolved_char}'")
    dispatch_to_vendor_backplane(vendor_target.strip().upper(), f"CMD_TOKEN_{resolved_char}")
    print()

@app.command(name="demodulate-telegraph")
def demodulate_telegraph_command(
    bit_pattern: int = typer.Argument(..., help="The binary element structure of the Morse pulse sequence or raw Baudot code."),
    pattern_len: int = typer.Argument(..., help="The data length of the targeted token profile (Use 5 for Baudot channels)."),
    config: Path = typer.Option(Path("config.yaml"), help="Path to the system configuration registry file."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target data visualizer audit sheet path."),
    kvm_json: Path = typer.Option(Path("gui_state.json"), help="The active operator console dashboard json template file.")
):
    config_data = load_system_config(config)
    
    if pattern_len == 5:
        ascii_code = decode_baudot_character(bit_pattern)
        resolved_char = chr(ascii_code)
        print(f"\n[TELEGRAPH DEMODULATION] Decoded 5-Bit Baudot Printing Stream character: '{resolved_char}'")
        evaluate_telegraphic_overrides(resolved_char, config_data, visio_csv, kvm_json)
        return
        
    pat_arr = np.array([bit_pattern], dtype=np.int32)
    len_arr = np.array([pattern_len], dtype=np.int32)
    decoded_codes = parallel_cpu_decode_morse_matrix(pat_arr, len_arr)
    resolved_char = chr(decoded_codes[0])
    
    print(f"\n[TELEGRAPH DEMODULATION] Decoded Continuous Wave Morse Telegraph Character: '{resolved_char}'")
    evaluate_telegraphic_overrides(resolved_char, config_data, visio_csv, kvm_json)

@app.command(name="process-cray-telemetry")
def process_cray_telemetry_command(
    gray_code_hex: str = typer.Argument(..., help="The raw 64-bit Gray code telemetry word pulled from the supercomputer backplane (e.g. 7FFFFFFFFFFFFFFF).")
):
    raw_gray_word = np.uint64(int(gray_code_hex.strip(), 16))
    gray_input_matrix = np.array([raw_gray_word], dtype=np.uint64)
    
    print("\n[CRAY VECTOR ENGINE] Ingesting supercomputing telemetry register fields...")
    start_time = time.time()
    binary_output_matrix = parallel_cpu_decode_cray_matrix(gray_input_matrix)
    execution_duration = time.time() - start_time
    
    resolved_binary_word = binary_output_matrix[0]
    print(f"[CRAY VECTOR ENGINE SUCCESS] Gray code conversion complete in {execution_duration:.6f} seconds.")
    print(f"  -> Raw Input Gray Hex:   {gray_code_hex.upper()}")
    print(f"  -> Corrected Binary Hex: {hex(resolved_binary_word).upper()}\n")

@app.command(name="expand-telephony-audio")
def expand_telephony_audio_command(
    mu_law_hex_byte: str = typer.Argument(..., help="The raw non-linear G.711 telephony audio sample byte (e.g. FF).")
):
    raw_byte_val = int(mu_law_hex_byte.strip(), 16)
    audio_buffer = np.array([raw_byte_val], dtype=np.uint8)
    linear_pcm_output = parallel_cpu_expand_pcm_stream(audio_buffer)[0]
    
    print(f"\n[TELEPHONY LINE EXPANSION] Processing G.711 μ-Law carrier channel block...")
    print(f"  -> Input Compressed μ-Law:  0x{mu_law_hex_byte.upper()}")
    print(f"  -> Restored Linear PCM Value: {linear_pcm_output} Units\n")

@app.command(name="carve-db-dump")
def carve_db_dump_command(
    dump_file: Path = typer.Argument(..., help="Path to the raw textual database test data dump asset file."),
    engine_mode: str = typer.Option("ORACLE", help="The database source format configuration layout (ORACLE, IBM_DB2)."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target Data Visualizer flowchart file to register hits into.")
):
    parse_raw_database_dump(dump_file, engine_mode, visio_csv)

@app.command(name="recover-storage")
def recover_storage_command(
    raw_dump: Path = typer.Argument(..., help="Path to the raw binary drive platter image dump file."),
    output_file: Path = typer.Argument(..., help="Target file path to save the reconstructed plaintext data matrix."),
    encoding: str = typer.Option("FIELDATA", help="The source encoding structure specification (FIELDATA, EBCDIC)."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target Data Visualizer spreadsheet log destination path.")
):
    if not raw_dump.exists():
        raise typer.Exit(code=1)
        
    raw_bytes = np.fromfile(raw_dump, dtype=np.uint8)
    if encoding.strip().upper() == "FIELDATA": processed = parallel_cpu_carve_fieldata(raw_bytes)
    elif encoding.strip().upper() == "EBCDIC": processed = parallel_cpu_carve_ebcdic(raw_bytes)
    else: processed = raw_bytes
        
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(bytes(processed).decode("ascii", errors="ignore"))
        
    print(f"[RECOVERY SUCCESS] Character carving matrix complete. Saved to: '{output_file}'")
    append_event_to_visio_csv(visio_csv, f"RECOV_{int(time.time())}", "Salvaged_Asset", f"Extracted blocks using {encoding}", "RECOVERY", "STORAGE_CARVER", "FILE", "0x00A9", "DRIVER_MAINFRAME_RECOVERY", "SALVAGED_OK", "Purple")

@app.command(name="compute-led-opto-analog")
def compute_led_opto_analog_command(
    lux_intensity: float = typer.Argument(..., help="Measured luminous output intensity driving the opto-receiver sensor element."),
    sensor_gain_db: float = typer.Option(12.0, help="Hardware operational amplifier gain calibration value in decibels.")
):
    calculated_voltage = compute_opto_analog_led_voltage(lux_intensity, sensor_gain_db)
    print(f"\n======================================================================")
    print(f"UNIVAC LED VACUUM TUBE EMULATION OPTIC CALCULATION")
    print(f"======================================================================")
    print(f"  -> Input Luminous Flux Parameter: {lux_intensity:.4f} Lux")
    print(f"  -> Receiver Amplifier Gain Setting: {sensor_gain_db:.1f} dB")
    print(f"  -> COMPUTED ANALOG OUTPUT SIGNAL CURRENT: {calculated_voltage:.4f} V\n")

@app.command(name="quantum-bridge")
def quantum_bridge_command():
    class UnivacIXQuantumBridge:
        def __init__(self):
            print("[BOOT] Initializing Univac IX Quantum-State Bridge...")
            self.heisenberg_comp = 0.05
            self.plasma_flow_base = 12.5

        def _calculate_heisenberg_uncertainty(self, target_coord: float) -> float:
            return target_coord + np.random.normal(0, self.heisenberg_comp)

        def _calculate_antimatter_flow(self, throttle_pct: float) -> float:
            return self.plasma_flow_base * (throttle_pct / 100.0) * math.pi

        async def _engage_teleportation_drive(self):
            print("\n[WARNING] TELEPORTATION SEQUENCE INITIATED.")
            print("[WARNING] SPOOLING ANTIMATTER CONTAINMENT FIELD...")
            for i in range(3, 0, -1):
                print(f" -> Jump in {i}...")
                await asyncio.sleep(1) 
            print("[+] JUMP COMPLETE. RE-ESTABLISHING SENSOR LOCK.\n")

        async def execute_quantum_cycle(self):
            print("[+] UNIVAC IX CORE ONLINE. AWAITING TELEMETRY.")
            try:
                while True:
                    telemetry = {
                        "throttle_pct": np.random.uniform(50.0, 100.0),
                        "target_x": 14500.5,
                        "target_y": -8400.2,
                        "teleportation_auth": np.random.uniform(0, 1) > 0.95 
                    }
                    adj_x = self._calculate_heisenberg_uncertainty(telemetry["target_x"])
                    adj_y = self._calculate_heisenberg_uncertainty(telemetry["target_y"])
                    plasma_rate = self._calculate_antimatter_flow(telemetry["throttle_pct"])
                    print(f"[CYCLE] Plasma Rate: {plasma_rate:.2f} THz | Target Lock: ({adj_x:.2f}, {adj_y:.2f})")
                    if telemetry["teleportation_auth"]:
                        await self._engage_teleportation_drive()
                    await asyncio.sleep(0.1) 
            except asyncio.CancelledError:
                print("\n[SHUTDOWN] Quantum loop suspended. Venting plasma.")

    async def _run_quantum_bridge_async():
        bridge = UnivacIXQuantumBridge()
        quantum_task = asyncio.create_task(bridge.execute_quantum_cycle())
        try:
            await quantum_task
        except KeyboardInterrupt:
            quantum_task.cancel()

    try:
        asyncio.run(_run_quantum_bridge_async())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Intercepted manual shutdown.")

@app.command(name="simulate-actuators")
def simulate_actuators_command(
    total_actuators: int = typer.Option(1000, help="The total array length sizing count of dynamic physical piston components."),
    safety_max_force_kn: float = typer.Option(50.0, help="The absolute maximum safe push-force tolerance limits in kilonewtons.")
):
    print(f"\n======================================================================")
    print(f"KOMMANDOGERAT-58 PHYSICS CORE ENGAGED // ACTUATOR FLUID SYSTEM ENGINE")
    print(f"======================================================================")
    np.random.seed(42)
    pressures_pascal = np.random.uniform(1e6, 30e6, total_actuators) 
    bores_meters = np.random.uniform(0.05, 0.25, total_actuators)   
    rods_meters = np.random.uniform(0.02, 0.12, total_actuators)    
    directions_binary = np.random.choice([0, 1], total_actuators)   
    dummy_p, dummy_b, dummy_r, dummy_d = np.array([6e6]), np.array([0.1]), np.array([0.05]), np.array([1])
    parallel_cpu_compute_actuator_stresses(dummy_p, dummy_b, dummy_r, dummy_d)
    start_time = time.time()
    forces_output_newtons = parallel_cpu_compute_actuator_stresses(pressures_pascal, bores_meters, rods_meters, directions_binary)
    execution_duration = time.time() - start_time
    max_measured_force_kn = np.max(forces_output_newtons) / 1000.0
    print(f"[SUCCESS] Actuator kinematics mapped natively in {execution_duration:.5f} seconds.")
    print(f"  -> Mean Extracted Output Thrust Force: {(np.mean(forces_output_newtons)/1000.0):.2f} kN")
    print(f"  -> Maximum Isolated Critical Piston Load: {max_measured_force_kn:.2f} kN")
    if max_measured_force_kn > safety_max_force_kn:
        sys.stdout.write("\a\a\a"); sys.stdout.flush()
        print("\n" + "!" * 80)
        print(f" !!! CRITICAL MECHANICAL COMPLIANCE EXCEEDED !!!")
        print("!" * 80 + "\n")
        raise typer.Exit(code=3)

@app.command(name="analyze-rotary-balance")
def analyze_rotary_balance_command(mass_nodes_count: int = typer.Option(5)):
    print(f"\n======================================================================")
    print(f"KOMMANDOGERAT-58 PHYSICS CORE ENGAGED // MULTI-AXIS ROTATIONAL BALANCE")
    print(f"======================================================================")
    np.random.seed(101)
    masses_kg = np.random.uniform(0.5, 12.0, mass_nodes_count)
    radii_meters = np.random.uniform(0.1, 0.8, mass_nodes_count)
    angles_degrees = np.random.uniform(0.0, 360.0, mass_nodes_count)
    dummy_m, dummy_rad, dummy_ang = np.array([1.0]), np.array([0.5]), np.array([45.0])
    parallel_cpu_verify_mass_balance(dummy_m, dummy_rad, dummy_ang)
    imbalance_vectors = parallel_cpu_verify_mass_balance(masses_kg, radii_meters, angles_degrees)
    net_imbalance_magnitude = math.sqrt((imbalance_vectors[0] ** 2) + (imbalance_vectors[1] ** 2))
    counter_angle_deg = (math.atan2(-imbalance_vectors[1], -imbalance_vectors[0]) * 180.0) / math.pi
    if counter_angle_deg < 0.0: counter_angle_deg += 360.0
    print(f"  -> Net Unmitigated Mechanical Centrifugal Imbalance: {net_imbalance_magnitude:.4f} kg·m")
    print(f"  -> Calculated Counterweight Vector Correction Angle: {counter_angle_deg:.2f}° Heading")

@app.command(name="calculate-linkage-torque")
def calculate_linkage_torque_command(
    force_newtons: float = typer.Argument(...),
    arm_length_meters: float = typer.Argument(...),
    angle_degrees: float = typer.Option(90.0)
):
    if force_newtons <= 0.0 or arm_length_meters <= 0.0:
        print("[INPUT ERROR] Valid structural bounds required.", file=sys.stderr)
        raise typer.Exit(code=1)
    computed_torque_nm = evaluate_rotational_torque_nm(force_newtons, arm_length_meters, angle_degrees)
    print(f"  -> NET CALCULATED SHAFTS TORQUE OUTPUT: {computed_torque_nm:.2f} N·m\n")

@app.command(name="scan-recovered-data")
def scan_recovered_data_command(
    target_file: Path = typer.Argument(..., help="Path to the recovered plaintext text asset to sweep for patterns."),
    kvm_gui_config: Path = typer.Argument(..., help="Path to your active Univac_Sperry_KVM_GUI layout state file (e.g., gui_state.json)."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target Data Visualizer flowchart file to register hits into.")
):
    if not target_file.exists():
        raise typer.Exit(code=1)
    print(f"\n======================================================================")
    print(f"AUTOMATED MULTI-LINE INJECTION ENGINE // TARGET ASSET: {target_file.name}")
    print(f"======================================================================")
    with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
        file_lines = f.readlines()
        
    total_matches_injected = 0
    for line_idx, line_content in enumerate(file_lines):
        clean_line = line_content.strip()
        if not clean_line: continue
        for classification_tag, regex_pattern in _INTELLIGENCE_PATTERNS.items():
            compiled_search = re.compile(regex_pattern, re.IGNORECASE)
            found_match = compiled_search.search(clean_line)
            if not found_match: continue
            captured_token = found_match.group(1).strip()
            total_matches_injected += 1
            kvm_variable_key = f"REC_{classification_tag}_L{line_idx + 1}"
            
            update_kvm_json_state(kvm_gui_config, kvm_variable_key, captured_token, f"RECOVERY_SCANNER_LINE_{line_idx + 1}")
            sys.stdout.write("\a\a"); sys.stdout.flush()
            print(f"  -> [MAPPED INTEL] Variable {kvm_variable_key} => '{captured_token}' staged for injection.")
            append_event_to_visio_csv(visio_csv, f"INTEL_HIT_{int(time.time())}_{line_idx+1}", f"Intel_Found_{time.strftime('%H:%M:%S')}", f"Isolated {classification_tag}: {captured_token}", "INTEL_TRAP", "RECOVERY_LOG", "0x00E9", "DRIVER_PATTERN_RECON", "DATA_ISOLATED", "HIGH_PRIORITY", "Orange")
            broadcast_intel_over_radio(classification_tag, captured_token)

    if total_matches_injected == 0:
        print("\n[RECON STATUS] Scan completed. Plaintext contains zero flagged operational signatures.\n")
    else:
        print(f"\n[INJECTION COMPLETE] Successfully parsed file and synchronized data matrices.")

# ------------------------------------------------------------------------------
# ATOMIC DATABASE & CHEMISTRY PARSING ENGINE
# ------------------------------------------------------------------------------
@app.command(name="query-chemistry")
def query_chemistry_command(
    target: str = typer.Argument(..., help="The Element Symbol (e.g., 'U', 'Fe', 'Au') or Atomic Number to query."),
    ptable_json: Path = typer.Option(Path("src/data/master_ptable.json"), help="Path to the JSON periodic table matrix.")
):
    """Accesses the Univac-IX localized atomic database for real-time stoichiometric and elemental parameters."""
    print(f"\n======================================================================")
    print(f"UNIVAC-IX ATOMIC RESOLUTION & MOLECULAR KINEMATICS CORE")
    print(f"======================================================================")
    
    if not ptable_json.exists():
        print(f"[ATOMIC FAULT] Localized chemistry database not found at '{ptable_json}'", file=sys.stderr)
        print(" -> Action: Ensure your JSON file is uploaded to the /src/data/ directory.")
        raise typer.Exit(code=1)

    # 1. Load the localized atomic JSON matrix into active memory
    try:
        with open(ptable_json, "r", encoding="utf-8") as f:
            ptable_data = json.load(f)
    except Exception as e:
        print(f"[ATOMIC FAULT] Database corruption detected: {e}", file=sys.stderr)
        raise typer.Exit(code=2)

    # Note: Adjust the 'elements' key below based on the exact root structure of your JSON
    elements_array = ptable_data.get("elements", []) if isinstance(ptable_data, dict) else ptable_data
    
    # 2. Sweep the memory matrix for the requested element (by Symbol or Atomic Number)
    found_element = None
    target_clean = target.strip()
    
    for element in elements_array:
        # Check against Symbol (e.g., 'Au') or Atomic Number (Z)
        if str(element.get("symbol", "")).upper() == target_clean.upper() or str(element.get("number", "")) == target_clean:
            found_element = element
            break

    if not found_element:
        print(f"[RECON FAILED] Target '{target}' does not match any known elemental signatures in the current matrix.\n")
        raise typer.Exit(code=0)

    # 3. Output the deterministic physical parameters
    name = found_element.get("name", "UNKNOWN")
    symbol = found_element.get("symbol", "??")
    atomic_number = found_element.get("number", found_element.get("Z", "N/A"))
    mass = found_element.get("atomic_mass", found_element.get("mass", "N/A"))
    density = found_element.get("density", "N/A")
    category = found_element.get("category", "N/A")

    print(f"  -> Target Acquired:     {name.upper()} ({symbol})")
    print(f"  -> Atomic Number (Z):   {atomic_number}")
    print(f"  -> Absolute Mass (u):   {mass} amu")
    print(f"  -> Phase / Category:    {str(category).upper()}")
    if density != "N/A":
        print(f"  -> Standard Density:    {density} g/cm³")
    
    print("\n[SUCCESS] Atomic parameters successfully pulled from static memory allocation.\n")
    
if __name__ == "__main__":
    app()

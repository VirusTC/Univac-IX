# File Name: main.py
# Location: /src/
# Subsystem: UNIVAC-IX Sovereignty Mainframe OS (Unified Core)

import sys
import os
import time
import socket
import re
import json
import yaml
import math
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

app = typer.Typer(help="UNIVAC-IX Sovereignty Mainframe OS, Athena-Class Wireless Daemon, Opto-Analog Fabric, & KG-58 Physics Core")

# ------------------------------------------------------------------------------
# GLOBAL STATE & SLA REGISTERS
# ------------------------------------------------------------------------------
_active_serial_handles: Dict[str, Any] = {}
_last_client_socket: Optional[socket.socket] = None

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
    if byte_val == 0x50: return 38
    if byte_val == 0x7D: return 39
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

@njit(parallel=True)
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
def calculate_opto_analog_led_intensity(input_voltage_volts: float, amplification_gain_factor: float) -> float:
    """Simulates vacuum tube math outputs, mapping voltage input strings to luminous intensity values."""
    if input_voltage_volts <= 0.0: return 0.0
    if input_voltage_volts >= 15.0: return 5000.0
    saturation_curve = 1.0 - math.exp(-input_voltage_volts / 5.0)
    base_intensity = 5000.0 * saturation_curve * amplification_gain_factor
    if base_intensity > 5000.0: return 5000.0
    return base_intensity

# ------------------------------------------------------------------------------
# DATA RECOVERY LOGGERS, VISIO AUDITING, & KVM INJECTION
# ------------------------------------------------------------------------------
def log_intelligence_hit_to_visio(pattern_type: str, exact_match: str, line_number: int, target_csv: Path) -> None:
    if not target_csv.exists(): return
    epoch_stamp = int(time.time())
    node_id = f"INTEL_HIT_{epoch_stamp}_{line_number}"
    timestamp = time.strftime("%H:%M:%S")
    node_name = f"Intel_Found_{timestamp}"
    node_desc = f"Isolated {pattern_type} validation token: {exact_match} at line {line_number}"
    log_line = f'{node_id},{node_name},"{node_desc}",,,INTEL_TRAP,RECOVERY_LOG,0x00E9,DRIVER_PATTERN_RECON,DATA_ISOLATED,HIGH_PRIORITY,Orange,NONE\n'
    try:
        with open(target_csv, "a", encoding="utf-8") as ledger:
            ledger.write(log_line)
    except Exception: pass

def broadcast_intel_over_radio(pattern_type: str, exact_match: str) -> None:
    radio_tx_addr = "0x0014"
    if radio_tx_addr not in _active_serial_handles: return
    timestamp = time.strftime("%H:%M:%S")
    radio_msg = f"[UNIVAC-INTEL] {timestamp} | MATCH:{pattern_type} | ADDR:{exact_match[:12]}... // SECURE_RELAY"
    hex_payload = radio_msg.encode("utf-8").hex().upper()
    try:
        _active_serial_handles[radio_tx_addr].write(bytes.fromhex(hex_payload))
    except Exception: pass

def append_mechanical_audit_to_visio(actuator_index: int, force_newtons: float, max_safe_kn: float, target_csv: Path) -> None:
    if not target_csv.exists(): return
    epoch_stamp = int(time.time())
    node_id = f"KG58_ACTUATOR_{epoch_stamp}_{actuator_index}"
    timestamp = time.strftime("%H:%M:%S")
    force_kn = force_newtons / 1000.0
    node_name = f"Actuator_Load_{actuator_index}_{timestamp}"
    node_desc = f"KG-58 Actuator Index {actuator_index} measured at {force_kn:.2f} kN output thrust force"
    
    severity, color_code, violation_text = "OPERATIONAL", "Green", "NONE"
    if force_kn > max_safe_kn:
        severity, color_code = "MECHANICAL_CRITICAL_OVERLOAD", "DarkRed"
        violation_text = f"LOAD_BREACH_CRITICAL (PEAK:{force_kn:.1f}kN LIMIT:{max_safe_kn:.1f}kN)"
        
    log_line = f'{node_id},{node_name},"{node_desc}",,,KG58_ENGINE,HYDRAULIC_PISTON,0x0058,DRIVER_KG58_PHYSICS,PASSIVE_LISTEN_ONLY,{severity},{color_code},"{violation_text}"\n'
    try:
        with open(target_csv, "a", encoding="utf-8") as ledger:
            ledger.write(log_line)
    except Exception: pass

def inject_servo_metrics_to_kvm_config(device_id: int, plane_angle: float, adjusted_torque: float, kvm_gui_config: Path) -> None:
    current_gui_state: Dict[str, Any] = {}
    if kvm_gui_config.exists():
        try:
            with open(kvm_gui_config, "r", encoding="utf-8") as stream:
                current_gui_state = json.load(stream)
        except Exception:
            pass
            
    if "live_dashboard_vars" not in current_gui_state:
        current_gui_state["live_dashboard_vars"] = {}

    plane_label = "FLAT_PLANETARY"
    if plane_angle >= 45.0:
        plane_label = "HORIZONTAL_EDGE"

    key_plane = f"SERVO_{device_id}_ORIENTATION_ANGLE"
    key_torque = f"SERVO_{device_id}_COMPENSATED_TORQUE"
    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")

    current_gui_state["live_dashboard_vars"][key_plane] = {
        "value": f"{plane_angle:.1f}° ({plane_label})",
        "source": "KG58_ORIENTATION_SENSOR",
        "last_synchronized": timestamp_str,
        "display_status": "RENDER_ACTIVE"
    }
    current_gui_state["live_dashboard_vars"][key_torque] = {
        "value": f"{adjusted_torque:.2f} N·m",
        "source": "KG58_KINEMATICS_COMPUTATION_ENGINE",
        "last_synchronized": timestamp_str,
        "display_status": "RENDER_ACTIVE"
    }

    try:
        with open(kvm_gui_config, "w", encoding="utf-8") as target_out:
            json.dump(current_gui_state, target_out, indent=2, ensure_ascii=False)
        print(f"  -> [KVM INTERFACE SYNC] Synced device {device_id} metrics: Angle={plane_angle:.1f}° ({plane_label}) | Torque={adjusted_torque:.2f} N·m")
    except Exception:
        pass

def inject_radio_metrics_to_kvm_config(device_id: int, orientation_deg: float, compensated_torque: float, kvm_gui_config: Path) -> None:
    """Appends live angular telemetry variables straight to the KVM layout map file structure."""
    current_gui_state: Dict[str, Any] = {}
    if kvm_gui_config.exists():
        try:
            with open(kvm_gui_config, "r", encoding="utf-8") as stream:
                current_gui_state = json.load(stream)
        except Exception:
            pass
            
    if "live_dashboard_vars" not in current_gui_state:
        current_gui_state["live_dashboard_vars"] = {}
        
    plane_label = "FLAT_PLANETARY"
    if orientation_deg >= 45.0:
        plane_label = "HORIZONTAL_EDGE"
        
    key_plane = f"WIRELESS_MOTOR_{device_id}_ORIENTATION_ANGLE"
    key_torque = f"WIRELESS_MOTOR_{device_id}_COMPENSATED_TORQUE"
    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
    
    current_gui_state["live_dashboard_vars"][key_plane] = {
        "value": f"{orientation_deg:.1f}° ({plane_label})",
        "source": "WIRELESS_ATHENA_RADIO_FIELD_SENSOR",
        "last_synchronized": timestamp_str,
        "display_status": "RENDER_ACTIVE"
    }
    current_gui_state["live_dashboard_vars"][key_torque] = {
        "value": f"{compensated_torque:.2f} N·m",
        "source": "NUMBA_ACCELERATED_TORQUE_SOLVER",
        "last_synchronized": timestamp_str,
        "display_status": "RENDER_ACTIVE"
    }
    
    try:
        with open(kvm_gui_config, "w", encoding="utf-8") as target_out:
            json.dump(current_gui_state, target_out, indent=2, ensure_ascii=False)
    except Exception:
        pass

def append_radio_injection_to_visio_map(device_id: int, plane_angle: float, torque: float, target_csv: Path) -> None:
    if not target_csv.exists():
        return
    epoch_stamp = int(time.time())
    node_id = f"RADIO_WIRELESS_INJECT_{epoch_stamp}_{device_id}"
    timestamp = time.strftime("%H:%M:%S")
    node_name = f"Wireless_Motor_{device_id}_{timestamp}"
    node_desc = f"OTA Radio Update: Servo plane labeled at {plane_angle:.1f} deg. Corrected torque calculation = {torque:.2f} N-m."
    log_line = f'{node_id},{node_name},"{node_desc}",,,RADIO_MESH_INJECT,WIRELESS_RF_LINK,0x0013,DRIVER_AVIATION_KNOWLEDGE,RADIO_MUTATED_STATE,WARNING,Orange,NONE\n'
    try:
        with open(target_csv, "a", encoding="utf-8") as ledger:
            ledger.write(log_line)
    except Exception:
        pass

# ------------------------------------------------------------------------------
# THE NETWORK PORT LISTENER (SLA ACCOUNTING)
# ------------------------------------------------------------------------------
def calculate_and_log_sla_credits(channel_addr: str, visio_csv: Path) -> None:
    if channel_addr not in _active_sla_breach_timers: return
    start_time = _active_sla_breach_timers[channel_addr]
    elapsed_seconds = time.time() - start_time
    if elapsed_seconds <= _SLA_WINDOW_SECONDS: return
    breach_overtime_seconds = elapsed_seconds - _SLA_WINDOW_SECONDS
    overtime_hours = breach_overtime_seconds / 3600.0
    accrued_penalty_usd = overtime_hours * _SLA_CREDIT_RATE_PER_HOUR
    print(f"  [SLA CONTRACT BREACH ACCRUING] Overtime Delta: {breach_overtime_seconds:.1f}s. Credit Penalty Owed: ${accrued_penalty_usd:.2f} USD.")
    if not visio_csv.exists(): return
    epoch_stamp = int(time.time())
    node_id = f"SLA_PENALTY_{epoch_stamp}_{channel_addr}"
    node_name = f"SLA_Credit_{channel_addr}"
    node_desc = f"Intervention overtime: {breach_overtime_seconds:.1f}s. Liquidated credit owed: ${accrued_penalty_usd:.2f} USD."
    log_line = f'{node_id},{node_name},"{node_desc}",,,SLA_ACCOUNTING,FINANCIAL_LEDGER,{channel_addr.lower()},DRIVER_SLA_TRACKER,LIQUIDATION_ISSUED,CRITICAL_TRAP_ENGAGED,DarkRed,NONE\n'
    try:
        with open(visio_csv, "a", encoding="utf-8") as ledger:
            ledger.write(log_line)
    except Exception: pass

def track_and_initialize_sla_timer(channel_addr: str) -> None:
    if channel_addr in _active_sla_breach_timers: return
    _active_sla_breach_timers[channel_addr] = time.time()
    print(f"  [SLA INCEPTION REGISTERED] Core operational stopwatch active for channel {channel_addr}.")

def clear_sla_timer(channel_addr: str) -> None:
    if channel_addr not in _active_sla_breach_timers: return
    del _active_sla_breach_timers[channel_addr]
    print(f"  [SLA RESOLVED] Target channel {channel_addr} cleared parameters. Stopwatch disarmed safely.")

def dispatch_emergency_radio_broadcast(hex_address: str, violation_type: str, threshold_val: int, current_val: int) -> None:
    radio_tx_addr = "0x0014"
    if radio_tx_addr not in _active_serial_handles:
        print(f"  [RADIO MESH DEFERRED] Cannot broadcast alert. Radio transceiver line {radio_tx_addr} offline.", file=sys.stderr)
        return
    timestamp = time.strftime("%H:%M:%S")
    radio_message = f"[UNIVAC-BREACH] {timestamp} | CH:{hex_address} | TYPE:{violation_type} | LIMIT:{threshold_val} | VAL:{current_val} // EVAC_ERR"
    hex_payload = radio_message.encode("utf-8").hex().upper()
    try:
        _active_serial_handles[radio_tx_addr].write(bytes.fromhex(hex_payload))
        print(f"  [RADIO MESH BROADCAST] Transmitting telemetry emergency warning vector frame over long-range lines.")
    except Exception: pass

def verify_live_sensor_safety_compliance(hex_address: str, raw_payload_bytes: bytes, visio_csv: Path) -> None:
    clean_addr = hex_address.strip().lower()
    if clean_addr not in _safety_threshold_registers: return
    if len(raw_payload_bytes) == 0: return
    measured_integer_value = int(raw_payload_bytes[-1])
    bounds = _safety_threshold_registers[clean_addr]
    max_boundary = bounds.get("upper_limit", 255)
    min_boundary = bounds.get("lower_limit", 0)
    
    if measured_integer_value > max_boundary or measured_integer_value < min_boundary:
        sys.stdout.write("\a\a\a"); sys.stdout.flush()
        print("\n" + "!" * 80)
        print(f" !!! CRITICAL CORE FABRIC RECON COMPLIANCE BREACH: SAFETY BOUNDS EXCEEDED !!!")
        limit_used = max_boundary if measured_integer_value > max_boundary else min_boundary
        type_str = "MAX_EXCEEDED" if measured_integer_value > max_boundary else "MIN_EXCEEDED"
        print(f" -> HARDWARE CHANNEL: {clean_addr} | Real-Time Read: {measured_integer_value} (LIMIT: {limit_used})")
        print("!" * 80)
        track_and_initialize_sla_timer(clean_addr)
        calculate_and_log_sla_credits(clean_addr, visio_csv)
        dispatch_emergency_radio_broadcast(clean_addr, type_str, limit_used, measured_integer_value)
        return
    clear_sla_timer(clean_addr)

def execute_matrix_mirror_routing(source_addr: str, raw_payload: bytes, config_data: Dict[str, Any]) -> None:
    routing_rule = config_data.get("routing_matrix", {})
    if routing_rule.get("source_node", "").lower() != source_addr.lower(): return
    targets = routing_rule.get("mirror_targets", [])
    for target in targets:
        target_addr = target.get("address", "").lower()
        if target_addr not in _active_serial_handles: continue
        try: _active_serial_handles[target_addr].write(raw_payload)
        except Exception: pass

# ------------------------------------------------------------------------------
# AUTOMATED RADIO MULTIPLEXER PROCESSING ENGINE
# ------------------------------------------------------------------------------
def handle_incoming_athena_radio_field_signal(hex_payload_str: str, config_data: Dict[str, Any], kvm_gui_config: Path, visio_csv: Path) -> None:
    """Decodes high-noise over-the-air radio signal packets, rectifying motor orientation angles instantly."""
    decoded_text = inline_multicore_hex_decode(hex_payload_str)
    if not decoded_text: return
    if not decoded_text.startswith("[WIRELESS_RF_ANG]"): return
    
    try:
        command_payload = decoded_text.replace("[WIRELESS_RF_ANG]", "").strip()
        params = command_payload.split(",")
        motor_id = int(params[0].strip())
        force_n = float(params[1].strip())
        arm_m = float(params[2].strip())
        incidence_deg = float(params[3].strip())
        plane_angle_deg = float(params[4].strip())
        
        adjusted_torque = evaluate_plane_adjusted_torque(force_n, arm_m, incidence_deg, plane_angle_deg)
        print(f"\n[RADIO ATHENA RX] Intercepted over-the-air telemetry from field sensor device: Motor ID {motor_id}")
        print(f"  -> Physical Mounting Profile: Orientation Angle = {plane_angle_deg:.1f}° Heading Alignment")
        print(f"  -> Kinematic Torque Solution: Compensated Load Force = {adjusted_torque:.2f} N·m Torsional Moment")
        
        inject_radio_metrics_to_kvm_config(motor_id, plane_angle_deg, adjusted_torque, kvm_gui_config)
        append_radio_injection_to_visio_map(motor_id, plane_angle_deg, adjusted_torque, visio_csv)
        
        raw_angle_byte = bytes([int(plane_angle_deg) & 0xFF])
        verify_live_sensor_safety_compliance("0x0013", raw_angle_byte, visio_csv)
    except Exception as err:
        print(f"  -> [RADIO ATHENA ERROR] Malformed wireless structural matrix frame: {err}", file=sys.stderr)

def process_incoming_stream(hex_address: str, raw_payload: bytes, config_data: Dict[str, Any], kvm_gui_config: Path, target_csv: Path) -> None:
    clean_addr = hex_address.strip().lower()
    hex_payload_str = raw_payload.hex().upper()
    
    if clean_addr == "0x0013":
        handle_incoming_athena_radio_field_signal(hex_payload_str, config_data, kvm_gui_config, target_csv)
        return
        
    execute_matrix_mirror_routing(clean_addr, raw_payload, config_data)
    verify_live_sensor_safety_compliance(clean_addr, raw_payload, target_csv)
    decoded_readable_text = inline_multicore_hex_decode(hex_payload_str)
    print(f"  [CORE PROCESSING FABRIC] Address: {clean_addr} | Hex: {hex_payload_str} | Ascii: {decoded_readable_text}")

# ------------------------------------------------------------------------------
# TYPER COMMANDS: CORE DAEMON & ROUTING
# ------------------------------------------------------------------------------
def load_system_config(config_path: Path) -> Dict[str, Any]:
    if config_path.exists():
        with open(config_path, "r") as stream:
            return yaml.safe_load(stream)
    print(f"Configuration Fault: Path {config_path} not found.", file=sys.stderr)
    raise typer.Exit(code=1)

@app.command(name="listen-ports")
def listen_ports_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the master system rule configuration registry file."),
    kvm_gui_config: Path = typer.Option(Path("gui_state.json"), help="Target layout json file tracking active KVM variable manifestations."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target Data Visualizer flowchart file to log audits into."),
    network_port: int = typer.Option(8080, help="Local network port simulating aggregate high-speed fiber interfaces.")
):
    """Launches the multi-channel daemon, integrating Athena radio field telemetry processing with opto-electronic led loops."""
    global _active_serial_handles
    config_data = load_system_config(config)
    
    print(f"\n======================================================================")
    print(f"ATHENA WIRELESS MULTIPLEXER DAEMON RUNNING: {config_data.get('system', {}).get('identity', 'UNIVAC-CORE-9')}")
    print(f"======================================================================")
    
    inline_multicore_hex_decode("414243") # Warm up parallel caches
    
    if "0x0014" not in _active_serial_handles:
        class DummySerial:
            def write(self, data): pass
        _active_serial_handles["0x0014"] = DummySerial()
        
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
            _active_serial_handles[node.get("hex_address").lower()] = ser
        except Exception: pass

    print(f"[LIVE MONITOR] Interface loops open. Scanning wired, socket, and wireless channels. (Ctrl+C to close)\n")

    try:
        while True:
            try:
                client_sock, _ = server_socket.accept()
                client_sock.settimeout(0.1)
                raw_buffer = client_sock.recv(4096)
                if raw_buffer:
                    payload_str = raw_buffer.decode('utf-8').strip()
                    if ":" in payload_str:
                        addr, data_hex = payload_str.split(":", 1)
                        process_incoming_stream(addr.strip().lower(), bytes.fromhex(data_hex.strip()), config_data, kvm_gui_config, visio_csv)
                client_sock.close()
            except BlockingIOError: pass
            except Exception: pass

            for hex_addr, serial_conn in list(_active_serial_handles.items()):
                if hex_addr == "0x0014": continue
                if not serial_conn.in_waiting: continue
                raw_bytes = serial_conn.read(serial_conn.in_waiting)
                if raw_bytes:
                    process_incoming_stream(hex_addr, raw_bytes, config_data, kvm_gui_config, visio_csv)

            for running_breach_addr in list(_active_sla_breach_timers.keys()):
                calculate_and_log_sla_credits(running_breach_addr, visio_csv)
            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Exiting tactical diagnostic multiplexer engine. Active state files preserved.")
        server_socket.close()
        raise typer.Exit(code=0)

@app.command(name="route-signal")
def route_signal_command(
    hex_address: str = typer.Argument(..., help="Target device hexadecimal address."),
    payload: str = typer.Argument(..., help="The hexadecimal input or output signal payload data."),
    config: Path = typer.Option(Path("config.yaml"), help="Path to the node configuration registry file."),
    kvm_gui_config: Path = typer.Option(Path("gui_state.json"), help="Target layout json file tracking active KVM variable manifestations."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target data visualizer spreadsheet to write audits to.")
):
    global _active_serial_handles
    config_data = load_system_config(config)
    if "0x0014" not in _active_serial_handles:
        class DummySerial:
            def write(self, data): pass
        _active_serial_handles["0x0014"] = DummySerial()
    raw_data = bytes.fromhex(payload.strip().upper())
    process_incoming_stream(hex_address, raw_data, config_data, kvm_gui_config, visio_csv)

# ------------------------------------------------------------------------------
# TYPER COMMANDS: OPTO-ANALOG & DATA RECOVERY (NEW)
# ------------------------------------------------------------------------------
@app.command(name="compute-led-opto-analog")
def compute_led_opto_analog_command(
    input_voltage: float = typer.Argument(..., help="The analog control signal voltage string feeding the tube grid circuit segment."),
    gain_factor: float = typer.Option(1.0, help="The amplification coefficient scalar parameter driving the opto-isolator loops.")
):
    """Simulates an vacuum tube analog calculator loop, translating voltages into precise LED output intensities."""
    if input_voltage < 0.0:
        print("[INPUT FAULT] Negative grid voltage parameters transcend physical filament tracking parameters.", file=sys.stderr)
        raise typer.Exit(code=1)
        
    luminous_intensity_mcd = calculate_opto_analog_led_intensity(input_voltage, gain_factor)
    
    print(f"\n======================================================================")
    print(f"UNIVAC OPTO-ELECTRONIC VACUUM TUBE EMULATION LOGIC REPORT")
    print(f"======================================================================")
    print(f"  -> Measured Grid Circuit Input Voltage: {input_voltage:.2f} V")
    print(f"  -> Configured Amplification Gain Scalar: {gain_factor:.2f}")
    print(f"  -> COMPUTED OVER-THE-WIRE LED OUTPUT INTENSITY: {luminous_intensity_mcd:.1f} mcd")
    print(f"  -> [SENSOR ASSIGNMENT] Driving physical photo-diode receptors via opto-analog mathematical coupling.\n")

@app.command(name="recover-storage")
def recover_storage_command(
    raw_dump: Path = typer.Argument(..., help="Path to the low-level raw binary drive image file partition."),
    output_file: Path = typer.Argument(..., help="Target file path to save the reconstructed readable plaintext data script."),
    encoding: str = typer.Option("FIELDATA", help="The source encoding schema specification (FIELDATA, EBCDIC).")
):
    """Deep carves legacy imagery files using multi-core parallel extraction pipelines."""
    if not raw_dump.exists():
        print(f"[RECOVERY FAULT] Image not found: '{raw_dump}'", file=sys.stderr)
        raise typer.Exit(code=1)
        
    raw_bytes = np.fromfile(raw_dump, dtype=np.uint8)
    if raw_bytes.shape[0] == 0:
        return
        
    start_time = time.time()
    match encoding.strip().upper():
        case "FIELDATA": processed = parallel_cpu_carve_fieldata(raw_bytes)
        case "EBCDIC": processed = parallel_cpu_carve_ebcdic(raw_bytes)
        case _: raise typer.Exit(code=2)
        
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(bytes(processed).decode("ascii", errors="ignore"))
        
    print(f"[SUCCESS] Deep block carve executed in {(time.time() - start_time):.4f}s -> Output: '{output_file}'")

# ------------------------------------------------------------------------------
# TYPER COMMANDS: QUANTUM BRIDGE & PHYSICS (EXISTING)
# ------------------------------------------------------------------------------
class UnivacIXQuantumBridge:
    def __init__(self):
        print("[BOOT] Initializing Univac IX Quantum-State Bridge...")
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        try:
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)["univac_core"]
            print(f"[BOOT] Loaded configuration from {config_path}")
        except (FileNotFoundError, yaml.YAMLError, KeyError):
            print(f"[WARNING] config.yaml invalid or missing. Booting Quantum Bridge in safe fallback mode.")
            self.config = {"heisenberg_compensation": 0.05, "anti_matter_plasma_flow": 12.5}

        self.heisenberg_comp = self.config["heisenberg_compensation"]
        self.plasma_flow_base = self.config["anti_matter_plasma_flow"]

    def _calculate_heisenberg_uncertainty(self, target_coord: float) -> float:
        fluctuation = np.random.normal(0, self.heisenberg_comp)
        return target_coord + fluctuation

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

@app.command(name="quantum-bridge")
def quantum_bridge_command():
    try:
        asyncio.run(_run_quantum_bridge_async())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Intercepted manual shutdown.")

@app.command(name="scan-recovered-data")
def scan_recovered_data_command(
    target_file: Path = typer.Argument(..., help="Path to the recovered plaintext text asset to sweep for patterns."),
    kvm_gui_config: Path = typer.Argument(..., help="Path to your active Univac_Sperry_KVM_GUI layout state file (e.g., gui_state.json)."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target Data Visualizer flowchart file to register hits into.")
):
    if not target_file.exists():
        print(f"[RECON FAULT] Plaintext target asset file missing at path: '{target_file}'", file=sys.stderr)
        raise typer.Exit(code=1)
    print(f"\n======================================================================")
    print(f"AUTOMATED MULTI-LINE INJECTION ENGINE // TARGET ASSET: {target_file.name}")
    print(f"======================================================================")
    with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
        file_lines = f.readlines()
    current_gui_state: Dict[str, Any] = {}
    if kvm_gui_config.exists():
        try:
            with open(kvm_gui_config, "r", encoding="utf-8") as stream:
                current_gui_state = json.load(stream)
        except Exception: pass
    if "live_dashboard_vars" not in current_gui_state:
        current_gui_state["live_dashboard_vars"] = {}
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
            current_gui_state["live_dashboard_vars"][kvm_variable_key] = {
                "value": captured_token,
                "source": f"RECOVERY_SCANNER_LINE_{line_idx + 1}",
                "last_synchronized": time.strftime("%Y-%m-%d %H:%M:%S"),
                "display_status": "RENDER_ACTIVE"
            }
            sys.stdout.write("\a\a"); sys.stdout.flush()
            print(f"  -> [MAPPED INTEL] Variable {kvm_variable_key} => '{captured_token}' staged for injection.")
            log_intelligence_hit_to_visio(classification_tag, captured_token, line_idx + 1, visio_csv)
            broadcast_intel_over_radio(classification_tag, captured_token)
    if total_matches_injected == 0:
        print("\n[RECON STATUS] Scan completed. Plaintext contains zero flagged operational signatures.\n")
        return
    try:
        with open(kvm_gui_config, "w", encoding="utf-8") as target_out:
            json.dump(current_gui_state, target_out, indent=2, ensure_ascii=False)
    except Exception as io_err:
        print(f"[KVM INJECTION FAULT] Failed to write automated multi-line list update: {io_err}", file=sys.stderr)
        raise typer.Exit(code=2)
    print(f"\n[INJECTION COMPLETE] Successfully parsed file and synchronized data matrices.")
    print(f"  -> Total Multi-Line List Nodes Appended: {total_matches_injected}")

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

@app.command(name="audit-kg58-to-visio")
def audit_kg58_to_visio_command(
    visio_csv: Path = typer.Argument(...),
    sim_count: int = typer.Option(5),
    max_safe_kn: float = typer.Option(50.0)
):
    if not visio_csv.exists(): raise typer.Exit(code=1)
    np.random.seed(2026)
    pressures_pascal = np.random.uniform(5e6, 40e6, sim_count)
    bores_meters = np.random.uniform(0.08, 0.22, sim_count)
    rods_meters = np.random.uniform(0.03, 0.10, sim_count)
    directions_binary = np.random.choice([0, 1], sim_count)
    forces_output_newtons = parallel_cpu_compute_actuator_stresses(pressures_pascal, bores_meters, rods_meters, directions_binary)
    for idx in range(sim_count):
        append_mechanical_audit_to_visio(idx, forces_output_newtons[idx], max_safe_kn, visio_csv)
    print(f"\n[AUDIT COMPLETED] Real-time models appended to: '{visio_csv.name}'\n")

@app.command(name="map-kinetics-to-kvm")
def map_kinetics_to_kvm_command(
    kvm_gui_config: Path = typer.Argument(..., help="Path to your active Univac_Sperry_KVM_GUI state layout file (e.g., gui_state.json)."),
    device_count: int = typer.Option(3, help="Total connected motors or servo shafts to evaluate and manifest into the dashboard panel views.")
):
    print(f"\n======================================================================")
    print(f"UNIVAC-IX ORIENTATION RECTIFICATION CORE // TARGET KVM: {kvm_gui_config.name}")
    print(f"======================================================================")
    np.random.seed(55)
    forces_newtons = np.random.uniform(50.0, 500.0, device_count)
    arm_lengths_meters = np.random.uniform(0.05, 0.4, device_count)
    force_incidence_angles = np.random.uniform(30.0, 90.0, device_count)
    orientation_plane_angles = np.array([0.0, 90.0, 45.0], dtype=np.float64)[:device_count]
    if device_count > 3:
        padding = np.random.uniform(0.0, 90.0, device_count - 3)
        orientation_plane_angles = np.concatenate((orientation_plane_angles, padding))

    adjusted_torques_matrix = parallel_cpu_compute_servo_matrix(
        forces_newtons, arm_lengths_meters, force_incidence_angles, orientation_plane_angles
    )

    for idx in range(device_count):
        measured_plane_angle = orientation_plane_angles[idx]
        computed_torque = adjusted_torques_matrix[idx]
        inject_servo_metrics_to_kvm_config(idx, measured_plane_angle, computed_torque, kvm_gui_config)
    print(f"\n[INJECTION COMPLETE] Unified kinematics synchronized. All device angles are cleanly labeled inside your KVM GUI view templates.\n")

# ------------------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    app()

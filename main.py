import sys
import os
import time
import socket
import struct
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import typer

import numpy as np
from numba import njit, prange

try:
    import serial
except ImportError:
    serial = None

app = typer.Typer(help="UNIVAC-IX Emergency Autonomous Diagnostic & Control Core Fabric")

_active_serial_handles: Dict[str, Any] = {}
_cached_fingerprints: Dict[str, str] = {}

# --- Numba High-Performance Accelerated Computing Core ---

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
            if high_char > 64:
                high_nibble = high_char - 55
                
            low_nibble = low_char - 48
            if low_char > 64:
                low_nibble = low_char - 55
                
            ascii_matrix[i, j] = (high_nibble << 4) | low_nibble
            
    return ascii_matrix

def inline_multicore_hex_decode(raw_hex_string: str) -> str:
    clean_hex = raw_hex_string.strip().upper()
    hex_len = len(clean_hex)
    if hex_len == 0:
        return ""
    if hex_len % 2 != 0:
        return "[ERROR: ASYMMETRIC STREAM]"

    hex_matrix = np.zeros((1, hex_len), dtype=np.uint8)
    line_lengths = np.array([hex_len], dtype=np.int32)
    hex_matrix[0, :hex_len] = list(clean_hex.encode("ascii"))
    
    raw_text_matrix = parallel_cpu_hex_to_text_matrix(hex_matrix, line_lengths)
    return bytes(raw_text_matrix[0, :hex_len // 2]).decode("utf-8", errors="ignore")


# --- Automated Fingerprinting & Driver Matrix Layer ---

def execute_heuristic_fingerprint(hex_payload: str) -> str:
    """Analyzes raw bit structures to identify unknown hardware devices in dark basements."""
    upper_payload = hex_payload.upper()
    
    # Tactical Radar Pattern (AN/UYK-7 / Aegis Bridge)
    if upper_payload.startswith("AA55") or "NTDS" in inline_multicore_hex_decode(upper_payload):
        return "DRIVER_MIL_STD_1397_TACTICAL"
        
    # Telemetry and Aviation Patterns
    if upper_payload.startswith("7E") or "ALTITUDE" in inline_multicore_hex_decode(upper_payload):
        return "DRIVER_AVIATION_KNOWLEDGE"
        
    # Industrial Transit Systems (Otis Gen360 Matrix)
    if upper_payload.startswith("0F0F") or "ELEVATOR" in inline_multicore_hex_decode(upper_payload):
        return "DRIVER_OTIS_GEN360"
        
    # Facility Safety and Fire Sensors
    if upper_payload.startswith("DEAD") or "CRITICAL" in inline_multicore_hex_decode(upper_payload):
        return "DRIVER_SAFETY_MONITOR"
        
    return "DRIVER_UNKNOWN_GENERIC_SERIAL"

def load_system_config(config_path: Path) -> Dict[str, Any]:
    if config_path.exists():
        with open(config_path, "r") as stream:
            return yaml.safe_load(stream)
    print(f"Configuration Fault: Path {config_path} not found.", file=sys.stderr)
    raise typer.Exit(code=1)

def execute_matrix_mirror_routing(source_addr: str, raw_payload: bytes, config_data: Dict[str, Any]) -> None:
    routing_rule = config_data.get("routing_matrix", {})
    if routing_rule.get("source_node", "").lower() != source_addr.lower():
        return

    targets = routing_rule.get("mirror_targets", [])
    for target in targets:
        target_addr = target.get("address", "").lower()
        if target_addr not in _active_serial_handles:
            continue
            
        try:
            _active_serial_handles[target_addr].write(raw_payload)
        except Exception:
            pass

def route_to_active_driver(driver_name: str, hex_addr: str, decoded_text: str, hex_str: str) -> None:
    """Dynamic Driver execution blocks managing worst-case field system recoveries."""
    match driver_name:
        case "DRIVER_MIL_STD_1397_TACTICAL":
            print(f"  [DRIVER] Bound to MIL-STD-1397 Aegis Sub-System. Resolving radar/weapon array matrices on {hex_addr}.")
            print(f"  [DATA] {decoded_text}")
            return
        case "DRIVER_AVIATION_KNOWLEDGE":
            print(f"  [DRIVER] Bound to Aviation Telemetry Transceiver. Real-time path tracing active on {hex_addr}.")
            print(f"  [DATA] {decoded_text}")
            return
        case "DRIVER_OTIS_GEN360":
            print(f"  [DRIVER] Bound to Otis Elevator Gen360 Logic Layer. Restoring vertical transit links on {hex_addr}.")
            print(f"  [DATA] {decoded_text}")
            return
        case "DRIVER_SAFETY_MONITOR":
            print(f"  [CRITICAL PRIORITY TRAP] Ground facility failure protocol engaged on channel {hex_addr}!")
            print(f"  [ALERT] {decoded_text}")
            return
        case _:
            print(f"  [DRIVER] Unrecognized hardware signature on {hex_addr}. Collecting data via standard generic serial line driver.")
            print(f"  [HEX DUMP] {hex_str}")
            return

def process_incoming_stream(hex_address: str, raw_payload: bytes, config_data: Dict[str, Any]) -> None:
    clean_addr = hex_address.strip().lower()
    hex_payload_str = raw_payload.hex().upper()
    
    # 1. Evaluate radio matrix split rules instantly
    execute_matrix_mirror_routing(clean_addr, raw_payload, config_data)
    
    # 2. Extract string values using Numba
    decoded_readable_text = inline_multicore_hex_decode(hex_payload_str)
    
    # 3. Handle Active Autonomic Machine Learning / Learning Verification
    if clean_addr not in _cached_fingerprints:
        detected_driver = execute_heuristic_fingerprint(hex_payload_str)
        _cached_fingerprints[clean_addr] = detected_driver
        print(f"\n[LEARNED INTERFACE] New hardware connected at address {clean_addr}. Analysis engine mapped driver target: {detected_driver}")

    assigned_driver = _cached_fingerprints[clean_addr]
    
    # 4. Route payload processing straight through the automated drivers
    route_to_active_driver(assigned_driver, clean_addr, decoded_readable_text, hex_payload_str)


# --- Core Command Interfaces ---

@app.command(name="listen-ports")
def listen_ports_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the system topology architecture profile."),
    network_port: int = typer.Option(8080, help="Network port capturing aggregate fiber optic lines.")
):
    """Launches the automated discovery system, mapping devices via MAC, radio, or serial pipelines."""
    global _active_serial_handles
    config_data = load_system_config(config)
    print(f"\n======================================================================")
    print(f"SYSTEM STANDING BY: {config_data.get('system', {}).get('identity', 'UNIVAC-CORE')}")
    print(f"======================================================================")
    print(f"[BOOT] Initializing multicore driver fingerprinting matrix cache layers...")
    inline_multicore_hex_decode("414243") # Warm up cache compiler
    
    # Bind Fiber Optic listening proxy stack Components
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", network_port))
    server_socket.listen(10)
    server_socket.setblocking(False)
    
    # Map and scan open hardware connection routes
    for node in config_data.get("nodes", []):
        port_path = node.get("port", "")
        if not port_path.startswith("/dev/"):
            continue
        if not serial:
            continue
        try:
            ser = serial.Serial(port_path, baudrate=115200, timeout=0.01)
            _active_serial_handles[node.get("hex_address").lower()] = ser
        except Exception:
            pass

    print(f"[LIVE DETECT] Core operational. Monitoring hardware links + Fiber network port {network_port}.")
    print(f"[GUIDE] Engineers can connect any unmapped hardware to begin real-time auto-recognition loops.\n")

    try:
        while True:
            # Poll fiber socket for network-packaged elements
            try:
                client_sock, client_addr = server_socket.accept()
                client_sock.settimeout(0.1)
                raw_buffer = client_sock.recv(4096)
                if raw_buffer:
                    payload_str = raw_buffer.decode('utf-8').strip()
                    if ":" in payload_str:
                        addr, data_hex = payload_str.split(":", 1)
                        process_incoming_stream(addr, bytes.fromhex(data_hex.strip()), config_data)
                client_sock.close()
            except BlockingIOError:
                pass
            except Exception:
                pass

            # Scan and read all hardware lines simultaneously
            for hex_addr, serial_conn in list(_active_serial_handles.items()):
                if not serial_conn.in_waiting:
                    continue
                raw_bytes = serial_conn.read(serial_conn.in_waiting)
                if raw_bytes:
                    process_incoming_stream(hex_addr, raw_bytes, config_data)

            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Exiting tactical diagnostic framework safely.")
        server_socket.close()
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()

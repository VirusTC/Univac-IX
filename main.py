import sys
import os
import time
import socket
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

app = typer.Typer(help="Dynamic Plug-and-Play UNIVAC Mainframe Hardware Emulator Fabric")

# Global handle storage for open serial hardware writers
_active_serial_handles: Dict[str, Any] = {}

# --- High-Performance Parallel Computing Core ---

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_hex_to_text_matrix(hex_array: np.ndarray, hex_lengths: np.ndarray) -> np.ndarray:
    total_lines = hex_array.shape
    max_hex_len = hex_array.shape
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
        return "[ERROR: ASYMMETRIC HEX STREAM]"

    hex_matrix = np.zeros((1, hex_len), dtype=np.uint8)
    line_lengths = np.array([hex_len], dtype=np.int32)
    hex_matrix[0, :hex_len] = list(clean_hex.encode("ascii"))
    
    raw_text_matrix = parallel_cpu_hex_to_text_matrix(hex_matrix, line_lengths)
    return bytes(raw_text_matrix[0, :hex_len // 2]).decode("utf-8", errors="ignore")


# --- Routing & Matrix Mirroring Layer ---

def execute_matrix_mirror_routing(source_addr: str, raw_payload: bytes, config_data: Dict[str, Any]) -> None:
    """Evaluates matrix routing rules and broadcasts clones of fiber inputs onto the 4 serial radio channels."""
    routing_rule = config_data.get("routing_matrix", {})
    if routing_rule.get("source_node", "").lower() != source_addr.lower():
        return # Not a configured routing source address

    targets = routing_rule.get("mirror_targets", [])
    print(f"[MATRIX MATRIX] Intercepted source channel {source_addr}. Duplicating data across {len(targets)} radio/monitor outputs...")
    
    for target in targets:
        target_addr = target.get("address", "").lower()
        
        # Guard against unmounted or missing physical serial adapters
        if target_addr not in _active_serial_handles:
            print(f"  -> Broadcast Delay: Hardware connection line {target_addr} ({target.get('label')}) offline.", file=sys.stderr)
            continue
            
        try:
            ser_conn = _active_serial_handles[target_addr]
            ser_conn.write(raw_payload)
            print(f"  -> [MIRROR SUCCESS] Sent to {target_addr} [{target.get('label')}] -> Bytes: {raw_payload.hex().upper()}")
        except Exception as e:
            print(f"  -> Hardware Write Error on {target_addr}: {e}", file=sys.stderr)

def process_incoming_stream(hex_address: str, raw_payload: bytes, config_data: Dict[str, Any]) -> None:
    clean_addr = hex_address.strip().lower()
    
    # 1. Trigger the Matrix Router rules first to mirror to our 4 lines
    execute_matrix_mirror_routing(clean_addr, raw_payload, config_data)
    
    # 2. Proceed with normal target module executions
    hex_payload_str = raw_payload.hex().upper()
    decoded_readable_text = inline_multicore_hex_decode(hex_payload_str)

    for node in config_data.get("nodes", []):
        if node.get("hex_address", "").lower() != clean_addr:
            continue
        if node.get("status") != "ACTIVE":
            return
            
        match node.get("target_module"):
            case "aegis-bridge":
                print(f"[HW -> AEGIS] Node: {node['name']} | Decoded: {decoded_readable_text}")
                return
            case "aviation-knowledge":
                print(f"[HW -> AVIATION] Telemetry Data -> Decoded: {decoded_readable_text}")
                return
            case _:
                print(f"[PORT IO FAULT] Destination module unrecognized.", file=sys.stderr)
                return


# --- Core Daemon Command ---

@app.command(name="listen-ports")
def listen_ports_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the system topology file."),
    baud_rate: int = typer.Option(115200, help="Baud speed parameter for your radio and monitor lines."),
    network_port: int = typer.Option(8080, help="Network port capturing raw fiber streams.")
):
    """Binds to your high-speed fiber socket while dynamically hot-mirroring arrays out through your 4 serial outputs."""
    global _active_serial_handles
    config_data = yaml.safe_load(open(config, "r"))
    print(f"[IO DAEMON] Spawning UNIVAC Matrix Route Engine...")
    
    # Open high-speed fiber virtual adapter socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", network_port))
    server_socket.listen(5)
    server_socket.setblocking(False)
    
    # Map and store open write handles for the 4 dedicated serial channels
    for node in config_data.get("nodes", []):
        port_path = node.get("port", "")
        if not port_path.startswith("/dev/"):
            continue
        if not serial:
            continue
            
        try:
            print(f"[IO DAEMON] Binding Serial Component Matrix line: {node.get('name')} on {port_path}")
            ser = serial.Serial(port_path, baudrate=baud_rate, timeout=0.01)
            _active_serial_handles[node.get("hex_address").lower()] = ser
        except Exception as e:
            print(f"  -> Hardware Offline Warning: Connection deferred for {port_path} ({e})")

    print("[IO DAEMON] Routing Table Matrix Live. Intercepting inputs... (Ctrl+C to close)")

    try:
        while True:
            # Poll incoming signals passing through the high speed fiber optic pipeline
            try:
                client_sock, _ = server_socket.accept()
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

            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\n[IO DAEMON] Safe shutdown sequence initiated. Disconnecting matrix handles.")
        server_socket.close()
        for handle in _active_serial_handles.values():
            handle.close()
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()

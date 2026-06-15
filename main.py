import sys
import os
import time
import socket
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import typer

import numpy as np
from numba import njit, prange, cuda

try:
    import serial
except ImportError:
    serial = None

app = typer.Typer(help="Dynamic Plug-and-Play UNIVAC Mainframe Hardware Emulator Fabric")

# --- High-Performance Parallel Computing Core ---

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
        return "[ERROR: ASYMMETRIC HEX STREAM]"

    hex_matrix = np.zeros((1, hex_len), dtype=np.uint8)
    line_lengths = np.array([hex_len], dtype=np.int32)
    hex_matrix[0, :hex_len] = list(clean_hex.encode("ascii"))
    
    raw_text_matrix = parallel_cpu_hex_to_text_matrix(hex_matrix, line_lengths)
    valid_text_len = hex_len // 2
    return bytes(raw_text_matrix[0, :valid_text_len]).decode("utf-8", errors="ignore")


# --- Routing & Processing Layer ---

def validate_word_alignment(bit_length: int) -> None:
    if bit_length == 36:
        return
    if bit_length == 18:
        return
    if bit_length == 16:
        return
    print(f"Hardware Fault: Unsupported bit architecture {bit_length}.", file=sys.stderr)
    raise typer.Exit(code=1)

def load_system_config(config_path: Path) -> Dict[str, Any]:
    if config_path.exists():
        with open(config_path, "r") as stream:
            return yaml.safe_load(stream)
    print(f"Configuration Fault: Path {config_path} not found.", file=sys.stderr)
    raise typer.Exit(code=1)

def process_incoming_stream(hex_address: str, raw_payload: bytes, config_data: Dict[str, Any]) -> None:
    clean_addr = hex_address.strip().lower()
    hex_payload_str = raw_payload.hex().upper()
    
    system_word_size = config_data.get("system", {}).get("default_word_size", 36)
    validate_word_alignment(system_word_size)
    
    decoded_readable_text = inline_multicore_hex_decode(hex_payload_str)

    for node in config_data.get("nodes", []):
        if node.get("hex_address", "").lower() != clean_addr:
            continue
        if node.get("status") != "ACTIVE":
            return
            
        # Differentiate routing notices based on interface hardware medium
        media_prefix = "[PORT SCANNED SERIAL]"
        if node.get("type") == "FIBER_OPTIC":
            media_prefix = "[HIGH-SPEED FIBER TRUNK]"

        match node.get("target_module"):
            case "aegis-bridge":
                print(f"{media_prefix} Node: {node['name']} (Addr: {clean_addr}) -> Decoded: {decoded_readable_text}")
                return
            case "aviation-knowledge":
                print(f"{media_prefix} Telemetry Input -> Decoded: {decoded_readable_text}")
                return
            case "safety-monitor":
                print(f"{media_prefix} Sensory Update -> Decoded: {decoded_readable_text}")
                return
            case "otis-gen360":
                print(f"{media_prefix} Structural Adjustment -> Decoded: {decoded_readable_text}")
                return
            case _:
                print(f"[PORT IO FAULT] Destination module unrecognized.", file=sys.stderr)
                return


# --- Core Command Interfaces ---

@app.command(name="listen-ports")
def listen_ports_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the system topology file."),
    baud_rate: int = typer.Option(115200, help="Baud speed parameter for converted legacy lines."),
    network_port: int = typer.Option(8080, help="Network port simulating high-speed fiber data streams.")
):
    """Binds to all 55 legacy mapped serial vectors and high-speed fiber interfaces concurrently."""
    config_data = load_system_config(config)
    print(f"[IO DAEMON] Initializing Unified Mainframe I/O Fabrics...")
    
    # Initialize Fiber Socket Framework
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", network_port))
    server_socket.listen(10)
    server_socket.setblocking(False)
    
    active_serial_handles: Dict[str, Any] = {}
    
    # Auto-detect and map all active entries out of the 55 possible channels
    for node in config_data.get("nodes", []):
        port_path = node.get("port", "")
        if not port_path.startswith("/dev/"):
            continue
        if not serial:
            continue
            
        try:
            ser = serial.Serial(port_path, baudrate=baud_rate, timeout=0.01)
            active_serial_handles[node.get("hex_address").lower()] = ser
        except Exception:
            pass # Suppress tracking error notifications if the target hardware pin is unplugged

    print(f"[IO DAEMON] Multiplexer operational. Monitoring {len(active_serial_handles)}/55 legacy lines + Fiber Line. (Ctrl+C to halt)")

    try:
        while True:
            # 1. Capture and process incoming packets from the High-Speed Fiber Pipe
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

            # 2. Sequential poll iteration through the 55 legacy serialized channels
            for hex_addr, serial_conn in active_serial_handles.items():
                if not serial_conn.in_waiting:
                    continue
                raw_bytes = serial_conn.read(serial_conn.in_waiting)
                if raw_bytes:
                    process_incoming_stream(hex_addr, raw_bytes, config_data)

            time.sleep(0.005) # Optimized sleep boundary for maximum scanning throughput

    except KeyboardInterrupt:
        print("\n[IO DAEMON] Safe shutdown sequence initiated. Disconnecting ports.")
        server_socket.close()
        raise typer.Exit(code=0)

if __name__ == "__main__":
    app()

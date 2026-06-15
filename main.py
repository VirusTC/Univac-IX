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


# --- High-Performance Parallel Computing Core (Cached & Vectorized) ---

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_text_to_hex_matrix(ascii_array: np.ndarray, line_lengths: np.ndarray) -> np.ndarray:
    total_lines = ascii_array.shape[0]
    max_len = ascii_array.shape[1]
    hex_matrix = np.zeros((total_lines, max_len * 2), dtype=np.uint8)
    
    for i in prange(total_lines):
        current_length = line_lengths[i]
        for j in range(current_length):
            val = ascii_array[i, j]
            high_nibble = (val >> 4) & 0x0F
            low_nibble = val & 0x0F
            
            high_char = high_nibble + 48
            if high_nibble > 9:
                high_char = high_nibble + 55
                
            low_char = low_nibble + 48
            if low_nibble > 9:
                low_char = low_nibble + 55
                
            hex_matrix[i, j * 2] = high_char
            hex_matrix[i, (j * 2) + 1] = low_char
            
    return hex_matrix

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


# --- High-Speed Real-time Decoding Helper Routine ---

def inline_multicore_hex_decode(raw_hex_string: str) -> str:
    """Invokes cached vector loops to instantaneously decode incoming network stream packages."""
    clean_hex = raw_hex_string.strip().upper()
    hex_len = len(clean_hex)
    
    if hex_len == 0:
        return ""
    if hex_len % 2 != 0:
        return "[ERROR: ASYMMETRIC HEX STREAM]"

    # Pack single message string data straight into vector matrices
    hex_matrix = np.zeros((1, hex_len), dtype=np.uint8)
    line_lengths = np.array([hex_len], dtype=np.int32)
    hex_matrix[0, :hex_len] = list(clean_hex.encode("ascii"))
    
    # Process utilizing the parallel multicore CPU math pipeline layers
    raw_text_matrix = parallel_cpu_hex_to_text_matrix(hex_matrix, line_lengths)
    
    valid_text_len = hex_len // 2
    decoded_bytes = bytes(raw_text_matrix[0, :valid_text_len])
    
    return decoded_bytes.decode("utf-8", errors="ignore")


# --- System Validation Operations ---

def validate_word_alignment(bit_length: int) -> None:
    if bit_length == 36:
        return
    if bit_length == 18:
        return
    if bit_length == 16:
        return
    print(f"Hardware Fault: Unsupported bit architecture {bit_length}.", file=sys.stderr)
    raise typer.Exit(code=1)

def convert_hex_stream(hex_payload: str) -> bytes:
    if len(hex_payload) % 2 == 0:
        return bytes.fromhex(hex_payload)
    print("Signal Fault: Hexadecimal streams must be symmetric (even length).", file=sys.stderr)
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

    # Perform immediate automated reverse translation computation on the raw incoming packet block
    decoded_readable_text = inline_multicore_hex_decode(hex_payload_str)

    for node in config_data.get("nodes", []):
        if node.get("hex_address", "").lower() != clean_addr:
            continue
        if node.get("status") != "ACTIVE":
            print(f"[PORT IO] Incoming on standby node {node.get('id')} rejected.", file=sys.stderr)
            return
            
        match node.get("target_module"):
            case "aegis-bridge":
                print(f"[HW -> AEGIS] Node: {node['name']} | Addr: {clean_addr}")
                print(f"  -> Raw Stream:    {hex_payload_str}")
                print(f"  -> Decoded Plain: {decoded_readable_text}")
                return
            case "aviation-knowledge":
                print(f"[HW -> AVIATION] Telemetry Signal Input Captured.")
                print(f"  -> Decoded Plain: {decoded_readable_text}")
                return
            case "safety-monitor":
                print(f"[HW -> SAFETY] Environment Sensory Update Captured.")
                print(f"  -> Decoded Plain: {decoded_readable_text}")
                return
            case "otis-gen360":
                print(f"[HW -> OTIS] Structural data array shifted.")
                print(f"  -> Decoded Plain: {decoded_readable_text}")
                return
            case "antigravity":
                print(f"[HW -> ANTIGRAVITY] Processing vector updates.")
                print(f"  -> Decoded Plain: {decoded_readable_text}")
                return
            case _:
                print(f"[PORT IO FAULT] Module route target '{node.get('target_module')}' unreachable.", file=sys.stderr)
                return

    print(f"[PORT IO WARNING] Data captured from unmapped link {hex_address} | Decoded: {decoded_readable_text}", file=sys.stderr)


# --- Commands Entry Interfaces ---

@app.command(name="route-signal")
def route_signal_command(
    hex_address: str = typer.Argument(..., help="Target device hexadecimal address."),
    payload: str = typer.Argument(..., help="The hexadecimal input or output signal payload data."),
    config: Path = typer.Option(Path("config.yaml"), help="Path to the node configuration registry file.")
):
    """Dynamically interfaces and maps I/O signals to attached repository software layers."""
    config_data = load_system_config(config)
    raw_data = convert_hex_stream(payload.strip().upper())
    process_incoming_stream(hex_address, raw_data, config_data)


@app.command(name="listen-ports")
def listen_ports_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the system topology file."),
    network_port: int = typer.Option(8080, help="Local network port baseline bound for socket stream capture.")
):
    """Binds live interface frameworks to process and decode incoming socket streams automatically."""
    config_data = load_system_config(config)
    print(f"[IO DAEMON] Initializing processing interface matrix on Core Network Port: {network_port}")
    
    # Warm up parallel engine cache before initializing network layers
    print("[IO DAEMON] Optimizing Numba parallel matrix compilation states...")
    inline_multicore_hex_decode("414243")
    print("[IO DAEMON] Compilation cache active. Full performance matrix ready.")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", network_port))
    server_socket.listen(5)
    server_socket.setblocking(False)
    
    print("[IO DAEMON] Auto-Decoding daemon network pipeline open. Listening... (Ctrl+C to halt)")

    try:
        while True:
            try:
                client_sock, client_addr = server_socket.accept()
                client_sock.settimeout(0.5)
                raw_buffer = client_sock.recv(1024)
                if raw_buffer:
                    payload_str = raw_buffer.decode('utf-8').strip()
                    if ":" in payload_str:
                        addr, data_hex = payload_str.split(":", 1)
                        converted_payload = bytes.fromhex(data_hex.strip())
                        process_incoming_stream(addr, converted_payload, config_data)
                client_sock.close()
            except BlockingIOError:
                pass
            except Exception:
                pass

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[IO DAEMON] Closing system network components safely.")
        server_socket.close()
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()

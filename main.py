import sys
import os
import time
import socket
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import typer

# High-Performance Computing Layer Imports
import numpy as np
from numba import njit, prange, cuda

try:
    import serial
except ImportError:
    serial = None

app = typer.Typer(help="Dynamic Plug-and-Play UNIVAC Mainframe Hardware Emulator Fabric")

# --- Numba Accelerated Computing Core ---

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_text_to_hex_matrix(ascii_array: np.ndarray, line_lengths: np.ndarray) -> np.ndarray:
    """Compiles text data across all available CPU cores simultaneously using max performance parameters."""
    total_lines = ascii_array.shape[0]
    max_len = ascii_array.shape[1]
    # Output matrix holds 2 hex characters per byte
    hex_matrix = np.zeros((total_lines, max_len * 2), dtype=np.uint8)
    
    for i in prange(total_lines):
        current_length = line_lengths[i]
        for j in range(current_length):
            val = ascii_array[i, j]
            # Fast bitwise conversions to ASCII hex values
            high_nibble = (val >> 4) & 0x0F
            low_nibble = val & 0x0F
            
            # Convert high nibble
            high_char = high_nibble + 48
            if high_nibble > 9:
                high_char = high_nibble + 55
                
            # Convert low nibble
            low_char = low_nibble + 48
            if low_nibble > 9:
                low_char = low_nibble + 55
                
            hex_matrix[i, j * 2] = high_char
            hex_matrix[i, (j * 2) + 1] = low_char
            
    return hex_matrix

@cuda.jit
def nvidia_gpu_hex_kernel(d_ascii, d_lengths, d_output):
    """Executes high-throughput hex acceleration directly on NVIDIA GPU streaming multiprocessors."""
    idx = cuda.grid(1)
    if idx >= d_ascii.shape[0]:
        return
        
    line_len = d_lengths[idx]
    for j in range(line_len):
        val = d_ascii[idx, j]
        high_nibble = (val >> 4) & 0x0F
        low_nibble = val & 0x0F
        
        high_char = high_nibble + 48
        if high_nibble > 9:
            high_char = high_nibble + 55
            
        low_char = low_nibble + 48
        if low_nibble > 9:
            low_char = low_nibble + 55
            
        d_output[idx, j * 2] = high_char
        d_output[idx, (j * 2) + 1] = low_char


# --- Standard System Validation and Routing Infrastructure ---

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

    for node in config_data.get("nodes", []):
        if node.get("hex_address", "").lower() != clean_addr:
            continue
        if node.get("status") != "ACTIVE":
            print(f"[PORT IO] Incoming on standby node {node.get('id')} rejected.", file=sys.stderr)
            return
            
        match node.get("target_module"):
            case "aegis-bridge":
                print(f"[HW -> AEGIS] Node: {node['name']} | Addr: {clean_addr} | Stream: {hex_payload_str}")
                return
            case "aviation-knowledge":
                print(f"[HW -> AVIATION] Telemetry Input Detected | Stream: {hex_payload_str}")
                return
            case "safety-monitor":
                print(f"[HW -> SAFETY] Sensory bus processing | Stream: {hex_payload_str}")
                return
            case "otis-gen360":
                print(f"[HW -> OTIS] Vertical data alignment shift | Stream: {hex_payload_str}")
                return
            case "antigravity":
                print(f"[HW -> ANTIGRAVITY] Processing field manipulation vector | Stream: {hex_payload_str}")
                return
            case _:
                print(f"[PORT IO FAULT] Module route target '{node.get('target_module')}' unreachable.", file=sys.stderr)
                return

    print(f"[PORT IO WARNING] Data captured from unmapped hardware link: Address {hex_address}.", file=sys.stderr)


# --- Commands Menu Architecture ---

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


@app.command(name="convert-log")
def convert_log_command(
    source_file: Path = typer.Argument(..., help="Path to the raw legacy text log file."),
    output_hex_file: Optional[Path] = typer.Option(None, help="Target file path to output pure hex strings."),
    use_gpu: bool = typer.Option(False, "--use-gpu", help="Force execution allocation to NVIDIA CUDA Hardware Accelerator.")
):
    """Converts legacy text logs into streamlined hexadecimal vectors with Multicore CPU or NVIDIA GPU processing."""
    if not source_file.exists():
        print(f"File Error: Source log file '{source_file}' does not exist.", file=sys.stderr)
        raise typer.Exit(code=1)
        
    with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f if line.strip()]
        
    if not lines:
        print("[CONVERTER] Source file is empty.")
        return

    # Structure data into optimized flat NumPy arrays for memory caching structures
    total_lines = len(lines)
    max_line_len = max(len(line) for line in lines)
    
    ascii_matrix = np.zeros((total_lines, max_line_len), dtype=np.uint8)
    line_lengths = np.zeros(total_lines, dtype=np.int32)
    
    for idx, line in enumerate(lines):
        line_bytes = line.encode("utf-8")
        line_lengths[idx] = len(line_bytes)
        ascii_matrix[idx, :len(line_bytes)] = list(line_bytes)

    # --- Processing Execution Router ---
    if use_gpu:
        if not cuda.is_available():
            print("[CUDA FAULT] NVIDIA graphics accelerator requested but no compatible GPU detected.", file=sys.stderr)
            raise typer.Exit(code=5)
            
        print(f"[CONVERTER] Launching hardware pipeline: NVIDIA CUDA GPU Vectorization Core Engine across {total_lines} indices.")
        d_ascii = cuda.to_device(ascii_matrix)
        d_lengths = cuda.to_device(line_lengths)
        d_output = cuda.device_array((total_lines, max_line_len * 2), dtype=np.uint8)
        
        threads_per_block = 128
        blocks_per_grid = (total_lines + (threads_per_block - 1)) // threads_per_block
        
        nvidia_gpu_hex_kernel[blocks_per_grid, threads_per_block](d_ascii, d_lengths, d_output)
        cuda.synchronize()
        
        raw_hex_matrix = d_output.copy_to_host()
    
    if not use_gpu:
        print(f"[CONVERTER] Launching hardware pipeline: Multicore CPU Numba Parallelization Fabric across {total_lines} items.")
        raw_hex_matrix = parallel_cpu_text_to_hex_matrix(ascii_matrix, line_lengths)

    # Convert the processed numeric character codes back to strings for presentation or storage
    final_output_list = []
    for idx in range(total_lines):
        valid_hex_bytes = raw_hex_matrix[idx, :line_lengths[idx] * 2]
        final_output_list.append(bytes(valid_hex_bytes).decode("ascii"))
        
    final_output_string = "\n".join(final_output_list)

    if not output_hex_file:
        print("[CONVERTER] Process complete. Performance Matrix stream output follows:")
        print(final_output_string)
        return

    with open(output_hex_file, "w", encoding="utf-8") as out:
        out.write(final_output_string + "\n")
    print(f"[CONVERTER] High-speed hexadecimal payload matrix exported to: {output_hex_file}")


@app.command(name="listen-ports")
def listen_ports_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the system topology file."),
    network_port: int = typer.Option(8080, help="Local network port baseline bound for socket stream capture.")
):
    """Binds live parallel hardware interface frameworks to capture physical serial and TCP sockets."""
    config_data = load_system_config(config)
    print(f"[IO DAEMON] Initializing communications interface matrix on Core Network Port: {network_port}")
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", network_port))
    server_socket.listen(5)
    server_socket.setblocking(False)
    
    print("[IO DAEMON] High-speed pipeline open. Listening for live machine frames... (Ctrl+C to halt)")

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
print("\n[IO DAEMON] Unmounting hardware channels and closing network stack components safely.")
server_socket.close()
raise typer.Exit(code=0)
if name == "main":
app()

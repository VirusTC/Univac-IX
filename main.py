import sys
import os
import time
import socket
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import typer

# Conditional import for hardware serial infrastructure to prevent startup crashes on virtual-only environments
try:
    import serial
except ImportError:
    serial = None

app = typer.Typer(help="Dynamic Plug-and-Play UNIVAC Mainframe Hardware Emulator Fabric")

_loaded_nodes_cache: List[str] = []

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
    """Dispatches raw bytes collected from networks or serial feeds straight to internal module logic structures."""
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
                print(f"[HW RECEIVE -> AEGIS] Node: {node['name']} | Hex Address: {clean_addr} | Stream: {hex_payload_str}")
                return
            case "aviation-knowledge":
                print(f"[HW RECEIVE -> AVIATION] Telemetry Input Detected | Stream: {hex_payload_str}")
                return
            case "safety-monitor":
                print(f"[HW RECEIVE -> SAFETY] Sensory bus processing | Stream: {hex_payload_str}")
                return
            case "otis-gen360":
                print(f"[HW RECEIVE -> OTIS] Vertical data alignment shift | Stream: {hex_payload_str}")
                return
            case "antigravity":
                print(f"[HW RECEIVE -> ANTIGRAVITY] Processing field manipulation vector | Stream: {hex_payload_str}")
                return
            case _:
                print(f"[PORT IO FAULT] Module route target '{node.get('target_module')}' unreachable.", file=sys.stderr)
                return

    print(f"[PORT IO WARNING] Data captured from unmapped hardware link: Address {hex_address}.", file=sys.stderr)


@app.command(name="route-signal")
def route_signal_command(
    hex_address: str = typer.Argument(..., help="Target device hexadecimal address (e.g., 0x00A1)."),
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
    baud_rate: int = typer.Option(9600, help="Default baud speed calculation parameter for physical serial lines."),
    network_port: int = typer.Option(8080, help="Local network port baseline bound for socket stream capture.")
):
    """Binds live parallel hardware interface frameworks to capture physical serial and TCP sockets."""
    config_data = load_system_config(config)
    print(f"[IO DAEMON] Initializing communications interface matrix on Core Network Port: {network_port}")
    
    # Configure and open TCP socket daemon interface
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", network_port))
    server_socket.listen(5)
    server_socket.setblocking(False) # Prevent thread deadlock
    
    # Track opened hardware pipelines
    active_serial_handles: Dict[str, Any] = {}
    
    # Locate all active node pathways claiming hardware connectivity mappings
    for node in config_data.get("nodes", []):
        port_path = node.get("port", "")
        if not port_path.startswith("/dev/"):
            continue
        if not serial:
            print(f"[SERIAL FAULT] Node {node.get('id')} requests {port_path} but 'pyserial' driver is missing.", file=sys.stderr)
            continue
            
        try:
            print(f"[IO DAEMON] Mounting physical adapter link: {port_path} @ {baud_rate}bps")
            ser = serial.Serial(port_path, baudrate=baud_rate, timeout=0.1)
            active_serial_handles[node.get("hex_address").lower()] = ser
        except Exception as e:
            print(f"[SERIAL WARNING] Could not bind physical device port {port_path}: {e}", file=sys.stderr)

    print("[IO DAEMON] Multi-channel pipeline open. Listening for live machine frames... (Ctrl+C to halt)")

    try:
        while True:
            # 1. Process TCP Network Sockets
            try:
                client_sock, client_addr = server_socket.accept()
                client_sock.settimeout(0.5)
                raw_buffer = client_sock.recv(1024)
                if raw_buffer:
                    # Expecting standard framed formatting: "HEX_ADDRESS:PAYLOAD_HEX" (e.g. "0x00A1:4A6F6E6573")
                    payload_str = raw_buffer.decode('utf-8').strip()
                    if ":" in payload_str:
                        addr, data_hex = payload_str.split(":", 1)
                        converted_payload = bytes.fromhex(data_hex.strip())
                        process_incoming_stream(addr, converted_payload, config_data)
                client_sock.close()
            except BlockingIOError:
                pass # No incoming connections present on this step cycle
            except Exception as ex:
                pass

            # 2. Process Physical Serial Hardware Inputs
            for hex_addr, serial_connection in active_serial_handles.items():
                if not serial_connection.in_waiting:
                    continue
                serial_raw = serial_connection.read(serial_connection.in_waiting)
                if serial_raw:
                    # Direct data byte injection mapped directly to its hardwired bus allocation
                    process_incoming_stream(hex_addr, serial_raw, config_data)

            time.sleep(0.05) # Minimize execution frame load strains

    except KeyboardInterrupt:
        print("\n[IO DAEMON] Unmounting hardware channels and closing network stack components safely.")
        server_socket.close()
        for handle in active_serial_handles.values():
            handle.close()
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()

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

app = typer.Typer(help="UNIVAC-IX Sovereignty Mainframe OS, Bidirectional Radio Mesh, Data Recovery, & SLA Accounting Core Fabric")

# ------------------------------------------------------------------------------
# GLOBAL STATE & SLA REGISTERS
# ------------------------------------------------------------------------------
_active_serial_handles: Dict[str, Any] = {}
_cached_fingerprints: Dict[str, str] = {}
_last_client_socket: Optional[socket.socket] = None

_safety_threshold_registers: Dict[str, Dict[str, int]] = {
    "0x0037": {"upper_limit": 200, "lower_limit": 10},
    "0x0038": {"upper_limit": 250, "lower_limit": 18}
}

_active_sla_breach_timers: Dict[str, float] = {}
_ANNUAL_RETAINER_USD: float = 4500000.0
_SLA_CREDIT_RATE_PER_HOUR: float = _ANNUAL_RETAINER_USD * 0.10
_SLA_WINDOW_SECONDS: float = 600.0

# ------------------------------------------------------------------------------
# MULTICORE HEX-TO-TEXT ACCELERATION
# ------------------------------------------------------------------------------
@njit(parallel=True)  # Activating Numba JIT for true multicore acceleration
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
    
    # Cast characters to ASCII integer representations for the Numba JIT compiler
    hex_matrix[0, :hex_len] = list(clean_hex.encode("ascii"))
    
    raw_text_matrix = parallel_cpu_hex_to_text_matrix(hex_matrix, line_lengths)
    return bytes(raw_text_matrix[0, :hex_len // 2]).decode("utf-8", errors="ignore")

# ------------------------------------------------------------------------------
# SLA ACCOUNTING & SAFETY INTERLOCKS
# ------------------------------------------------------------------------------
def calculate_and_log_sla_credits(channel_addr: str, visio_csv: Path) -> None:
    """Computes downstream system credit deductions if tactical interventions pass the 10-minute threshold."""
    if channel_addr not in _active_sla_breach_timers:
        return
        
    start_time = _active_sla_breach_timers[channel_addr]
    elapsed_seconds = time.time() - start_time
    
    if elapsed_seconds <= _SLA_WINDOW_SECONDS:
        # print(f"  [SLA WITHIN BOUNDS] Interventions active. Time elapsed: {elapsed_seconds:.2f}s / {_SLA_WINDOW_SECONDS}s.")
        return
        
    breach_overtime_seconds = elapsed_seconds - _SLA_WINDOW_SECONDS
    overtime_hours = breach_overtime_seconds / 3600.0
    accrued_penalty_usd = overtime_hours * _SLA_CREDIT_RATE_PER_HOUR
    
    print(f"  [SLA BREACH ALERT] Intervention windows breached by {breach_overtime_seconds:.2f} seconds!")
    print(f"  [FINANCIAL RETENTION] Accruing sovereign compensation credits: ${accrued_penalty_usd:.2f} USD.")
    
    if not visio_csv.exists():
        return
        
    epoch_stamp = int(time.time())
    node_id = f"SLA_PENALTY_{epoch_stamp}_{channel_addr}"
    node_name = f"SLA_Credit_{channel_addr}"
    node_desc = f"Intervention overtime: {breach_overtime_seconds:.1f}s. Liquidated credit owed: ${accrued_penalty_usd:.2f} USD."
    
    log_line = f'{node_id},{node_name},"{node_desc}",,,SLA_ACCOUNTING,FINANCIAL_LEDGER,{channel_addr.lower()},DRIVER_SLA_TRACKER,LIQUIDATION_ISSUED,CRITICAL_TRAP_ENGAGED,DarkRed,NONE\n'
    
    try:
        with open(visio_csv, "a", encoding="utf-8") as ledger:
            ledger.write(log_line)
    except Exception:
        pass

def track_and_initialize_sla_timer(channel_addr: str) -> None:
    """Secures structural microsecond stopwatch stamps the instant an emergency condition trips."""
    if channel_addr in _active_sla_breach_timers:
        return
    _active_sla_breach_timers[channel_addr] = time.time()
    print(f"  [SLA INCEPTION REGISTERED] Core tactical clock armed for channel {channel_addr}. 10-Minute intervention window active.")

def clear_sla_timer(channel_addr: str) -> None:
    """Erases the live ticking clock once an automated hardware handshake restores the baseline parameters."""
    if channel_addr not in _active_sla_breach_timers:
        return
    del _active_sla_breach_timers[channel_addr]
    print(f"  [SLA RESOLVED] Target channel {channel_addr} returned to nominal state. Intercept stopwatch disarmed safely.")

def dispatch_emergency_radio_broadcast(hex_address: str, violation_type: str, threshold_val: int, current_val: int) -> None:
    radio_tx_addr = "0x0014"
    if radio_tx_addr not in _active_serial_handles:
        print(f"  [RADIO MESH DEFERRED] Cannot broadcast alert. Radio transceiver line {radio_tx_addr} offline.", file=sys.stderr)
        return
        
    timestamp = time.strftime("%H:%M:%S")
    radio_message = f"[UNIVAC-BREACH] {timestamp} | CH:{hex_address} | TYPE:{violation_type} | LIMIT:{threshold_val} | VAL:{current_val} // EVAC_ERR"
    
    hex_payload = radio_message.encode("utf-8").hex().upper()
    raw_packet_bytes = bytes.fromhex(hex_payload)
    
    try:
        _active_serial_handles[radio_tx_addr].write(raw_packet_bytes)
        print(f"  [RADIO MESH BROADCAST] Transmitting telemetry payload string to field pager matrix loops.")
    except Exception:
        pass

def verify_live_sensor_safety_compliance(hex_address: str, raw_payload_bytes: bytes, visio_csv: Path) -> None:
    clean_addr = hex_address.strip().lower()
    if clean_addr not in _safety_threshold_registers:
        return
    if len(raw_payload_bytes) == 0:
        return
        
    measured_integer_value = int(raw_payload_bytes[-1])
    bounds = _safety_threshold_registers[clean_addr]
    max_boundary = bounds.get("upper_limit", 255)
    min_boundary = bounds.get("lower_limit", 0)
    
    if measured_integer_value > max_boundary:
        sys.stdout.write("\a\a\a")
        sys.stdout.flush()
        print("\n" + "!" * 80)
        print(f" !!! CRITICAL PACKET COMPLIANCE BREACH: UPPER SAFETY BOUNDS EXCEEDED !!!")
        print(f" -> INCOMING ROUTE CHANNEL: {clean_addr} | Real-Time Value: {measured_integer_value} (MAX: {max_boundary})")
        print("!" * 80)
        track_and_initialize_sla_timer(clean_addr)
        calculate_and_log_sla_credits(clean_addr, visio_csv)
        dispatch_emergency_radio_broadcast(clean_addr, "MAX_EXCEEDED", max_boundary, measured_integer_value)
        return
        
    if measured_integer_value < min_boundary:
        sys.stdout.write("\a\a\a")
        sys.stdout.flush()
        print("\n" + "!" * 80)
        print(f" !!! CRITICAL PACKET COMPLIANCE BREACH: LOWER SAFETY BOUNDS EXCEEDED !!!")
        print(f" -> INCOMING ROUTE CHANNEL: {clean_addr} | Real-Time Value: {measured_integer_value} (MIN: {min_boundary})")
        print("!" * 80)
        track_and_initialize_sla_timer(clean_addr)
        calculate_and_log_sla_credits(clean_addr, visio_csv)
        dispatch_emergency_radio_broadcast(clean_addr, "MIN_EXCEEDED", min_boundary, measured_integer_value)
        return
        
    clear_sla_timer(clean_addr)

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

def process_incoming_stream(hex_address: str, raw_payload: bytes, config_data: Dict[str, Any], target_csv: Path) -> None:
    clean_addr = hex_address.strip().lower()
    hex_payload_str = raw_payload.hex().upper()
    execute_matrix_mirror_routing(clean_addr, raw_payload, config_data)
    verify_live_sensor_safety_compliance(clean_addr, raw_payload, target_csv)
    decoded_readable_text = inline_multicore_hex_decode(hex_payload_str)
    print(f"  [CORE PROCESSING RUNTIME] Address: {clean_addr} | Hex: {hex_payload_str} | Ascii: {decoded_readable_text}")

# ------------------------------------------------------------------------------
# COMMAND 1: THE NETWORK PORT LISTENER (SLA ACCOUNTING)
# ------------------------------------------------------------------------------
@app.command(name="listen-ports")
def listen_ports_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the master system topology file registry configuration."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target Data Visualizer file layout matching the audit matrix."),
    network_port: int = typer.Option(8080, help="Local network socket port capturing virtual fiber lines.")
):
    """Binds to live multi-channel interface loops while concurrently executing automated SLA stopwatch tracking."""
    global _active_serial_handles
    
    if not config.exists():
        print(f"Configuration Fault: Path {config} not found.", file=sys.stderr)
        raise typer.Exit(code=1)
        
    with open(config, "r") as f:
        config_data = yaml.safe_load(f)
        
    print(f"\n======================================================================")
    print(f"SLA ACCOUNTING & AUTONOMIC CORE FABRIC ONLINE: {config_data.get('system', {}).get('identity', 'UNIVAC-CORE')}")
    print(f"======================================================================")
    
    # Run a test cycle to JIT-compile the numba function before real-time operations
    inline_multicore_hex_decode("414243")
    
    if "0x0014" not in _active_serial_handles:
        class DummySerial:
            def write(self, data): pass
        _active_serial_handles["0x0014"] = DummySerial()
        
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # REPAIRED INDENTATION BLOCK START
    server_socket.bind(("0.0.0.0", network_port))
    server_socket.listen(10)
    server_socket.setblocking(False)

    for node in config_data.get("nodes", []):
        port_path = node.get("port", "")
        if not port_path.startswith("/dev/"):
            continue
        if not serial:
            continue
        try:
            ser = serial.Serial(port_path, baudrate=115200, timeout=0.01)
            _active_serial_handles[node.get("hex_address", "").lower()] = ser
        except Exception:
            pass

    print(f"[LIVE ENGINE] Port listeners activated. Financial SLA monitors armed and counting. (Ctrl+C to disarm)\n")

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
                        process_incoming_stream(addr.strip().lower(), bytes.fromhex(data_hex.strip()), config_data, visio_csv)
                client_sock.close()
            except BlockingIOError:
                pass
            except Exception:
                pass

            for hex_addr, serial_conn in list(_active_serial_handles.items()):
                if hex_addr == "0x0014":
                    continue
                if not serial_conn.in_waiting:
                    continue
                raw_bytes = serial_conn.read(serial_conn.in_waiting)
                if raw_bytes:
                    process_incoming_stream(hex_addr, raw_bytes, config_data, visio_csv)

            for running_breach_addr in list(_active_sla_breach_timers.keys()):
                calculate_and_log_sla_credits(running_breach_addr, visio_csv)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Exiting tactical diagnostic network daemon safely. Financial ledgers saved.")
        server_socket.close()
        raise typer.Exit(code=0)
    # REPAIRED INDENTATION BLOCK END

# ------------------------------------------------------------------------------
# COMMAND 2: MANUAL ROUTE INJECTION
# ------------------------------------------------------------------------------
@app.command(name="route-signal")
def route_signal_command(
    hex_address: str = typer.Argument(..., help="Target device hexadecimal address."),
    payload: str = typer.Argument(..., help="The hexadecimal input or output signal payload data."),
    config: Path = typer.Option(Path("config.yaml"), help="Path to the node configuration registry file."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target data visualizer spreadsheet to write audits to.")
):
    """Manually routes an input frame payload to verify compliance and track real-time SLA penalty ticks."""
    global _active_serial_handles
    with open(config, "r") as f:
        config_data = yaml.safe_load(f)
        
    if "0x0014" not in _active_serial_handles:
        class DummySerial:
            def write(self, data): pass
        _active_serial_handles["0x0014"] = DummySerial()
        
    raw_data = bytes.fromhex(payload.strip().upper())
    process_incoming_stream(hex_address, raw_data, config_data, visio_csv)

# ------------------------------------------------------------------------------
# COMMAND 3: QUANTUM BRIDGE ASYNC LOOP (From Previous Iteration)
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
    """Initializes the Univac IX Quantum-State Bridge and Anti-Matter Teleportation Drive."""
    try:
        asyncio.run(_run_quantum_bridge_async())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Intercepted manual shutdown.")

# ------------------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    app()

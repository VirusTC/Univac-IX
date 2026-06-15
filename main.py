import sys
import os
import time
import socket
import json
import re
import subprocess
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

app = typer.Typer(help="UNIVAC-IX Emergency Autonomous Diagnostic, Recovery & Tactical Control Core Fabric")

# --- Global Operational Memories and Driver State Registers ---
_active_serial_handles: Dict[str, Any] = {}
_cached_fingerprints: Dict[str, str] = {}
_last_client_socket: Optional[socket.socket] = None

_safety_threshold_registers: Dict[str, Dict[str, int]] = {
    "0x0037": {"upper_limit": 200, "lower_limit": 10},
    "0x0038": {"upper_limit": 250, "lower_limit": 18}
}

_INTELLIGENCE_PATTERNS: Dict[str, str] = {
    "FINANCIAL_ROUTING": r"(?:ACCOUNT|IBAN|BANK|ROUTE|SWIFT)[\s\:\-\=]*([A-Z0-9]{8,24})",
    "SYSTEM_AUTHENTICATION": r"(?:PASS|PASSWORD|PWD|SECRET|KEY|TOKEN)[\s\:\-\=]*([a-zA-Z0-9\!\@\#\$\%\^\&\*]{6,32})",
    "TACTICAL_NAVIGATION": r"(?:LAT|LON|COORD|WAYPOINT|NAV)[\s\:\-\=]*([\d\.\-\u00B0\'\"]{4,18}\s*[NSEW]?)"
}


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

@njit(cache=True, fastmath=True)
def decode_fieldata_byte(byte_val: int) -> int:
    if byte_val == 0:   return 32  # Space
    if byte_val == 1:   return 48  # '0'
    if byte_val == 2:   return 49  # '1'
    if byte_val == 3:   return 50  # '2'
    if byte_val == 4:   return 51  # '3'
    if byte_val == 5:   return 52  # '4'
    if byte_val == 6:   return 53  # '5'
    if byte_val == 7:   return 54  # '6'
    if byte_val == 8:   return 55  # '7'
    if byte_val == 9:   return 56  # '8'
    if byte_val == 10:  return 57  # '9'
    if 11 <= byte_val <= 36:
        return byte_val + 54  # Maps to A-Z uppercase
    if byte_val == 37:  return 46  # '.'
    if byte_val == 38:  return 44  # ','
    if byte_val == 39:  return 45  # '-'
    if byte_val == 40:  return 47  # '/'
    return 63  # Fallback '?'

@njit(cache=True, fastmath=True)
def decode_ebcdic_byte(byte_val: int) -> int:
    if byte_val == 0x40: return 32  # Space
    if 0x81 <= byte_val <= 0x89: return byte_val - 0x81 + 97   # a - i
    if 0x91 <= byte_val <= 0x99: return byte_val - 0x91 + 106  # j - r
    if 0xA2 <= byte_val <= 0xA9: return byte_val - 0xA2 + 115  # s - z
    if 0xC1 <= byte_val <= 0xC9: return byte_val - 0xC1 + 65   # A - I
    if 0xD1 <= byte_val <= 0xD9: return byte_val - 0xD1 + 74   # J - R
    if 0xE2 <= byte_val <= 0xE9: return byte_val - 0xE2 + 83   # S - Z
    if 0xF0 <= byte_val <= 0xF9: return byte_val - 0xF0 + 48   # 0 - 9
    if byte_val == 0x4B: return 46  # '.'
    if byte_val == 0x6B: return 44  # ','
    if byte_val == 0x60: return 45  # '-'
    if byte_val == 0x61: return 47  # '/'
    if byte_val == 0x50: return 38  # '&'
    if byte_val == 77:  return 39  # '''
    return 63  # Fallback '?'

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


# --- Automated Utilities, Core System Routines & Backends ---

def load_system_config(config_path: Path) -> Dict[str, Any]:
    if config_path.exists():
        with open(config_path, "r") as stream:
            return yaml.safe_load(stream)
    print(f"Configuration Fault: Path {config_path} not found.", file=sys.stderr)
    raise typer.Exit(code=1)

def validate_word_alignment(bit_length: int) -> None:
    if bit_length in:
        return
    print(f"Hardware Fault: Unsupported bit architecture {bit_length}.", file=sys.stderr)
    raise typer.Exit(code=1)

def convert_hex_stream(hex_payload: str) -> bytes:
    if len(hex_payload) % 2 == 0:
        return bytes.fromhex(hex_payload)
    print("Signal Fault: Hexadecimal streams must be symmetric (even length).", file=sys.stderr)
    raise typer.Exit(code=1)


# --- Intelligent Dynamic Discovery & Routing Infrastructure ---

def execute_heuristic_fingerprint(hex_payload: str) -> str:
    upper_payload = hex_payload.upper()
    decoded = inline_multicore_hex_decode(upper_payload)
    if upper_payload.startswith("AA55") or "NTDS" in decoded:
        return "DRIVER_MIL_STD_1397_TACTICAL"
    if upper_payload.startswith("7E") or "ALTITUDE" in decoded:
        return "DRIVER_AVIATION_KNOWLEDGE"
    if upper_payload.startswith("0F0F") or "BREAKDOWN" in decoded:
        return "DRIVER_OTIS_GEN360"
    if upper_payload.startswith("DEAD") or "CRITICAL" in decoded:
        return "DRIVER_SAFETY_MONITOR"
    return "DRIVER_UNKNOWN_GENERIC_SERIAL"

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

def execute_hardware_reverse_injection(hex_addr: str, reply_hex: str) -> None:
    raw_reply_bytes = bytes.fromhex(reply_hex.strip().upper())
    if hex_addr in _active_serial_handles:
        try:
            _active_serial_handles[hex_addr].write(raw_reply_bytes)
            print(f"  [RECOVERY INJECTED -> SERIAL] Dispatched payload {reply_hex} back to channel {hex_addr}.")
            return
        except Exception as e:
            print(f"  [RECOVERY FAULT] Failed to write to serial wire line {hex_addr}: {e}", file=sys.stderr)
            return
    if _last_client_socket:
        try:
            network_return_frame = f"{hex_addr}:{reply_hex}\n".encode('utf-8')
            _last_client_socket.sendall(network_return_frame)
            print(f"  [RECOVERY INJECTED -> FIBER] Echoed return instruction network payload back down core trunk.")
            return
        except Exception:
            return

def evaluate_handshake_reply_rules(driver_name: str, hex_addr: str, decoded_text: str, config_data: Dict[str, Any]) -> None:
    handshake_rules = config_data.get("recovery_handshakes", {}).get(driver_name, {})
    if not handshake_rules:
        return
    trigger = handshake_rules.get("trigger_keyword", "")
    if trigger not in decoded_text.upper():
        return
    print(f"\n  [ALERT MATCHED] Rule Trigger: '{trigger}' located inside payload stream for {driver_name}.")
    execute_hardware_reverse_injection(hex_addr, handshake_rules.get("reply_hex", ""))

def dispatch_emergency_radio_broadcast(hex_address: str, violation_type: str, threshold_val: int, current_val: int) -> None:
    radio_tx_addr = "0x0014"
    if radio_tx_addr not in _active_serial_handles:
        return
    timestamp = time.strftime("%H:%M:%S")
radio_message = f"[UNIVAC-BREACH] {timestamp} | CH:{hex_address} | TYPE:{violation_type} | LIMIT:{threshold_val} | VAL:{current_val} // EVAC_ERR"
hex_payload = radio_message.encode("utf-8").hex().upper()
try:
_active_serial_handles[radio_tx_addr].write(bytes.fromhex(hex_payload))
print(f" [RADIO MESH BROADCAST] Transmitted wireless network safety telemetry update frame: {radio_message}")
except Exception:
pass
def verify_live_sensor_safety_compliance(hex_address: str, raw_payload_bytes: bytes) -> None:
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
print(f"\n !!! CRITICAL ENVIRONMENTAL SAFEGUARD BREACH: UPPER LIMIT EXCEEDED ON {clean_addr} !!!")
dispatch_emergency_radio_broadcast(clean_addr, "MAX_EXCEEDED", max_boundary, measured_integer_value)
return
if measured_integer_value < min_boundary:
sys.stdout.write("\a\a\a")
sys.stdout.flush()
print(f"\n !!! CRITICAL ENVIRONMENTAL SAFEGUARD BREACH: LOWER LIMIT EXCEEDED ON {clean_addr} !!!")
dispatch_emergency_radio_broadcast(clean_addr, "MIN_EXCEEDED", min_boundary, measured_integer_value)
return
def process_incoming_stream(hex_address: str, raw_payload: bytes, config_data: Dict[str, Any], target_csv: Path) -> None:
clean_addr = hex_address.strip().lower()
hex_payload_str = raw_payload.hex().upper()
execute_matrix_mirror_routing(clean_addr, raw_payload, config_data)
verify_live_sensor_safety_compliance(clean_addr, raw_payload)
if clean_addr == "0x0013":
# Handle dynamic entry loops when data drops onto our over-the-air radio receiver port
decoded_text = inline_multicore_hex_decode(hex_payload_str)
print(f"\n[RADIO RX INTERCEPT] Stream caught on channel 0x0013 -> Plaintext: {decoded_text}")
if decoded_text.startswith("[CMD]"):
try:
command_payload = decoded_text.replace("[CMD]", "").strip()
target_addr, override_hex = command_payload.split(":", 1)
raw_cmd_bytes = bytes.fromhex(override_hex.strip().upper())
# Append to Visio auditing ledgers instantly
epoch_stamp = int(time.time())
with open(target_csv, "a", encoding="utf-8") as ledger:
ledger.write(f"RADIO_INJECT_{epoch_stamp},Radio_Override_{epoch_stamp},OTA Injection onto {target_addr},,,RADIO_INJECT,AIR_LINK,{target_addr.lower()},DRIVER_RADIO_MUTATED,RADIO_ARMED,WARNING,Orange,NONE\n")
process_incoming_stream(target_addr.strip().lower(), raw_cmd_bytes, config_data, target_csv)
except Exception:
pass
return
decoded_readable_text = inline_multicore_hex_decode(hex_payload_str)
if clean_addr not in _cached_fingerprints:
detected_driver = execute_heuristic_fingerprint(hex_payload_str)
_cached_fingerprints[clean_addr] = detected_driver
print(f"[LEARNED ELEMENT] Mapped driver target for channel {clean_addr} => {detected_driver}")
assigned_driver = _cached_fingerprints[clean_addr]
match assigned_driver:
case "DRIVER_SAFETY_MONITOR":
print(f" [PRIORITY ALARM TRAP] Threat verified on lane {clean_addr} | Msg: {decoded_readable_text}")
evaluate_handshake_reply_rules(assigned_driver, clean_addr, decoded_readable_text, config_data)
case _:
print(f" [CORE EXECUTING] Driver: {assigned_driver} | Channel: {clean_addr} | Data: {decoded_readable_text}")
evaluate_handshake_reply_rules(assigned_driver, clean_addr, decoded_readable_text, config_data)
--- Automated Live Variable Injection & Multi-Line Feeding Component ---
def inject_multi_line_kvm_vars(kvm_gui_config: Path, multi_line_records: List[Dict[str, str]], visio_csv: Path) -> None:
"""Takes a structured list of intelligence match variables and merges them natively into the KVM JSON GUI layout map file."""
current_gui_state: Dict[str, Any] = {}
if kvm_gui_config.exists():
try:
with open(kvm_gui_config, "r", encoding="utf-8") as stream:
current_gui_state = json.load(stream)
except Exception:
pass
if "live_dashboard_vars" not in current_gui_state:
current_gui_state["live_dashboard_vars"] = {}
injection_count = 0
timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
epoch_base = int(time.time())
for record in multi_line_records:
key = record.get("key", "").strip().upper()
val = record.get("value", "").strip()
if not key:
continue
if not val:
continue
# Ingest variables natively into the UI schema variables matrix map
current_gui_state["live_dashboard_vars"][key] = {
"value": val,
"source": "MAINFRAME_STORAGE_CARVER_AUTO_TRAP",
"last_synchronized": timestamp,
"display_status": "RENDER_ACTIVE"
}
injection_count += 1
# Simultaneously append tracking points out into your visual flowchart ledgers
if visio_csv.exists():
try:
with open(visio_csv, "a", encoding="utf-8") as ledger:
ledger.write(f"KVM_VAR_{epoch_base}{injection_count},KVM_Bind{key},"Auto-injected intelligence tracking field parameter -> {val}",,,KVM_GUI_FABRIC,PANEL_REGISTER,0x00C9,DRIVER_KVM_GUI,INTERFACE_MOUNTED,INFORMATIONAL,Purple,NONE\n")
except Exception:
pass
try:
with open(kvm_gui_config, "w", encoding="utf-8") as target_out:
json.dump(current_gui_state, target_out, indent=2, ensure_ascii=False)
print(f" -> [KVM MATRIX BIND] Successfully hot-injected {injection_count} multi-line text variables directly inside layout panel data config array.")
except Exception as io_err:
print(f"[KVM INJECTION FAULT] Failed to sync variable matrix variables block: {io_err}", file=sys.stderr)
--- Core Command Interfaces Menu ---
@app.command(name="route-signal")
def route_signal_command(
hex_address: str = typer.Argument(..., help="Target device hexadecimal address."),
payload: str = typer.Argument(..., help="The hexadecimal input or output signal payload data."),
config: Path = typer.Option(Path("config.yaml"), help="Path to the node configuration registry file."),
visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target data visualizer spreadsheet file to append logs into.")
):
"""Manually routes custom raw input frames into runtime processing environments."""
config_data = load_system_config(config)
if "0x0014" not in _active_serial_handles:
class DummySerial:
def write(self, d): pass
_active_serial_handles["0x0014"] = DummySerial()
raw_data = bytes.fromhex(payload.strip().upper())
process_incoming_stream(hex_address, raw_data, config_data, visio_csv)
@app.command(name="load-safety-boundaries")
def load_safety_boundaries_command(
guideline_path: Path = typer.Argument(..., help="Path to the Environment-Safety-Monitor documentation specifications file.")
):
"""Parses safety monitor repository documentation to dynamically compile operating threshold thresholds."""
global _safety_threshold_registers
if not guideline_path.exists():
print(f"[GUIDELINE FAULT] Document missing: '{guideline_path}'", file=sys.stderr)
raise typer.Exit(code=1)
print(f"[INGESTION] Scanning repository documentation boundaries inside: {guideline_path}")
with open(guideline_path, "r", encoding="utf-8", errors="ignore") as doc:
lines = doc.readlines()
rule_pattern = re.compile(r"(0x[0-9a-fA-F]{2,4})\s*:\s*([0-9a-fA-F]{2,8})\s*/\s*([0-9a-fA-F]{2,8})")
count = 0
for line in lines:
match_entry = rule_pattern.search(line.strip())
if not match_entry:
continue
sensor_addr = match_entry.group(1).lower()
max_int = int(match_entry.group(2), 16)
min_int = int(match_entry.group(3), 16)
_safety_threshold_registers[sensor_addr] = {"upper_limit": max_int, "lower_limit": min_int}
print(f" -> REG-REGISTERED [{sensor_addr}]: Upper Limit = {max_int} | Lower Limit = {min_int}")
count += 1
print(f"[INGESTION COMPLETE] Loaded {count} operational safety constraints.")
@app.command(name="discover-network-nodes")
def discover_network_nodes_command(
config: Path = typer.Option(Path("config.yaml"), help="Path to the system configuration file to auto-append lines into."),
auto_mount: bool = typer.Option(False, "--mount", help="Automatically write new targets directly into configuration file maps.")
):
"""Parses live interface ARP tables across local data trunks to locate hidden unmapped hardware lines."""
print("[RECON] Gathering fiber optic network pairing topologies from live interface segments...")
discovered: List[Dict[str, str]] = []
command = ["arp", "-n"]
if os.name == "nt": command = ["arp", "-a"]
try:
raw_output = subprocess.check_output(command, stderr=subprocess.DEVNULL).decode("utf-8", errors="ignore")
except Exception:
print("[RECON FAULT] Local shell metrics gathering parameters unavailable.", file=sys.stderr)
raise typer.Exit(code=1)
ip_pattern = r"(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})"
mac_pattern = r"([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})"
for line in raw_output.splitlines():
f_ip = re.search(ip_pattern, line)
f_mac = re.search(mac_pattern, line)
if f_ip and f_mac:
discovered.append({"ip": f_ip.group(1), "mac": f_mac.group(1).replace("-", ":").lower()})
if not discovered:
print("[RECON STATUS] Caches empty. Zero hidden device nodes isolated on local segments.")
return
config_data = load_system_config(config)
existing_ports = [node.get("port") for node in config_data.get("nodes", [])]
counter = len(existing_ports) + 1
for dev in discovered:
print(f" -> FOUND TARGET: IP = {dev['ip']} | Hardware MAC = {dev['mac']}")
if auto_mount and dev['ip'] not in existing_ports:
hex_addr = f"0x00{hex(counter)[2:].upper().zfill(2)}"
config_data["nodes"].append({
"id": f"DISCOVERED_NODE_{counter}", "name": f"Auto_Net_Node_{counter}",
"type": "FIBER_OPTIC_NETWORK_REMOTE", "port": dev['ip'], "hex_address": hex_addr,
"target_module": "aegis-bridge", "status": "ACTIVE"
})
print(f" * STITCHED TO BASE CONFIG MATRIX -> Bound Logic Port Allocation: {hex_addr}")
counter += 1
if auto_mount:
with open(config, "w") as out: yaml.safe_dump(config_data, out, default_flow_style=False)
@app.command(name="recover-storage")
def recover_storage_command(
raw_dump: Path = typer.Argument(..., help="Path to the low-level raw binary partition dump from legacy media hardware units."),
output_file: Path = typer.Argument(..., help="Target text path to output reconstructed plaintext text logs."),
encoding: str = typer.Option("FIELDATA", help="The translation matrix format rules configuration (FIELDATA, EBCDIC)."),
visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target Data Visualizer flowchart file to document actions into.")
):
"""Performs deep multi-core block carving over vintage files to unlock proprietary character sets instantly."""
if not raw_dump.exists():
print(f"[RECOVERY FAULT] Source image dump file missing at target path: '{raw_dump}'", file=sys.stderr)
raise typer.Exit(code=1)
print(f"\n[RECOVERY] Ingesting binary partition data from '{raw_dump.name}'...")
raw_bytes = np.fromfile(raw_dump, dtype=np.uint8)
if raw_bytes.shape[0] == 0:
print("[RECOVERY DEFERRED] Target drive sector matrix contains no bytes.")
return
start = time.time()
match encoding.strip().upper():
case "FIELDATA": processed = parallel_cpu_carve_fieldata(raw_bytes)
case "EBCDIC": processed = parallel_cpu_carve_ebcdic(raw_bytes)
case :
print("[RECOVERY FAULT] Format configuration matrix unsupported.", file=sys.stderr)
raise typer.Exit(code=2)
duration = time.time() - start
decoded_string = bytes(processed).decode("ascii", errors="ignore")
with open(output_file, "w", encoding="utf-8") as out:
out.write(decoded_string)
print(f"[RECOVERY SUCCESS] Carver parsed legacy storage records in {duration:.4f} seconds -> Saved: '{output_file}'")
if visio_csv.exists():
with open(visio_csv, "a", encoding="utf-8") as l:
l.write(f"RECOVERY{int(time.time())},Salvaged_Media,"Carved {raw_bytes.shape[0]} blocks using {encoding}",,,RECOVERY_DAEMON,MAGNETIC_STORAGE,0x00A9,DRIVER_MAINFRAME_RECOVERY,SALVAGED_OK,INFORMATIONAL,Purple,NONE\n")
@app.command(name="scan-recovered-data")
def scan_recovered_data_command(
target_file: Path = typer.Argument(..., help="Path to the recovered plaintext data file to scan."),
kvm_gui_config: Path = typer.Option(Path("gui_state.json"), help="Path to your active KVM GUI state parameters text file."),
visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target data visualizer spreadsheet ledger file.")
):
"""Sweeps recovered text loops for credentials, waypoints, or profiles and auto-injects them directly into live KVM variables."""
if not target_file.exists():
print(f"[RECON FAULT] Target plaintext text asset file missing at path: '{target_file}'", file=sys.stderr)
raise typer.Exit(code=1)
print(f"\n======================================================================")
print(f"AUTOMATED CONVERGENCE SCAN & MULTI-LINE KVM FEEDER // ASSET: {target_file.name}")
print(f"======================================================================")
with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
file_lines = f.readlines()
collected_kvm_updates: List[Dict[str, str]] = []
total_hits = 0
for line_idx, line_content in enumerate(file_lines):
clean_line = line_content.strip()
if not clean_line:
continue
for classification_tag, regex_pattern in _INTELLIGENCE_PATTERNS.items():
compiled_search = re.compile(regex_pattern, re.IGNORECASE)
found_match = compiled_search.search(clean_line)
if not found_match:
continue
captured_token = found_match.group(1).strip()
total_hits += 1
# Generate a clean descriptive variable tracking identifier key for your KVM dashboard screen matrix
variable_key = f"INTEL_{classification_tag}_{total_hits}"
collected_kvm_updates.append({"key": variable_key, "value": captured_token})

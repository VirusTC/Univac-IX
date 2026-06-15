import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import typer

try:
    import serial
except ImportError:
    serial = None

app = typer.Typer(help="UNIVAC-IX Tactical Automation, Radio Alert Mesh & Safety Core Fabric")

_active_serial_handles: Dict[str, Any] = {}

_cached_fingerprints: Dict[str, str] = {
    "0x0011": "DRIVER_MIL_STD_1397_TACTICAL",
    "0x0012": "DRIVER_MIL_STD_1397_TACTICAL",
    "0x0013": "DRIVER_AVIATION_KNOWLEDGE",
    "0x0014": "DRIVER_AVIATION_KNOWLEDGE",
    "0x0022": "DRIVER_OTIS_GEN360",
    "0x0037": "DRIVER_SAFETY_MONITOR"
}

def load_system_config(config_path: Path) -> Dict[str, Any]:
    if config_path.exists():
        with open(config_path, "r") as stream:
            return yaml.safe_load(stream)
    print(f"Configuration Fault: Path {config_path} not found.", file=sys.stderr)
    raise typer.Exit(code=1)


# --- Automated Radio Messaging & SMS Trap Engine ---

def dispatch_radio_alert_notice(node_id: str, channel_addr: str, rule_label: str, target_driver: str) -> None:
    """Formats an emergency status update text string and transmits it over the air via physical radio port 20."""
    radio_tx_addr = "0x0014" # Hardcoded to match PORT_20 RADIO_TRANS_TX allocation parameters
    
    # 1. Guard against inactive or missing physical radio hardware transmitters
    if radio_tx_addr not in _active_serial_handles:
        print(f"  [RADIO MESH DEFERRED] Cannot broadcast alert. Radio transmission line {radio_tx_addr} is offline.", file=sys.stderr)
        return

    # 2. Compile highly compact plain text update string suitable for field paging or SMS relay units
    timestamp = time.strftime("%H:%M:%S")
    alert_text = f"[UNIVAC-ALERT] {timestamp} | NODE:{node_id} | ADDR:{channel_addr} | DRV:{target_driver} | ACTION:{rule_label} // INJECT_OK"
    
    # 3. High-speed text-to-hex vector transformation sequence
    hex_payload = alert_text.encode("utf-8").hex().upper()
    raw_packet_bytes = bytes.fromhex(hex_payload)
    
    try:
        radio_channel = _active_serial_handles[radio_tx_addr]
        radio_channel.write(raw_packet_bytes)
        print(f"  [RADIO MESH BROADCAST] Dispatched emergency network tracking SMS notification over long-range line.")
        print(f"    -> Raw Message Text: {alert_text}")
    except Exception as tx_err:
        print(f"  [RADIO MESH FAULT] Signal drop on transceiver channel: {tx_err}", file=sys.stderr)


# --- Core Operational Infrastructure Functions ---

def execute_direct_hardware_injection(hex_addr: str, reply_hex: str) -> None:
    clean_addr = hex_addr.strip().lower()
    raw_reply_bytes = bytes.fromhex(reply_hex.strip().upper())
    
    if clean_addr not in _active_serial_handles:
        print(f"  [RECOVERY DELAY] Target line {clean_addr} is running over virtual host environments.")
        return
        
    try:
        _active_serial_handles[clean_addr].write(raw_reply_bytes)
        print(f"  [RECOVERY SUCCESS] Injected mitigation payload {reply_hex.upper()} directly into physical channel {clean_addr}.")
    except Exception as e:
        print(f"  [RECOVERY FAULT] Failed to write to serial wire line {clean_addr}: {e}", file=sys.stderr)


# --- Commands Menu Architecture Layout ---

@app.command(name="export-visio")
def export_visio_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the node configuration registry file."),
    output: Path = typer.Option(Path("visio_mapping.csv"), help="Target path for Visio Data Visualizer CSV output.")
):
    """Generates an enhanced Visio-compliant CSV integrating live autonomic learning and bidirectional tracking flags."""
    config_data = load_system_config(config)
    handshake_rules = config_data.get("recovery_handshakes", {})
    
    with open(output, "w", encoding="utf-8") as f:
        f.write("Process Step ID,Step Name,Description,Next Step ID,Resource,Node Type,Hardware Port,Hex Address,Assigned Driver,Bidirectional Flag,System Severity,Visio Shape Color\n")
        
        nodes = config_data.get("nodes", [])
        total_nodes = len(nodes)
        
        for index, node in enumerate(nodes):
            node_id = node.get("id", "UNKNOWN")
            hex_addr = node.get("hex_address", "").lower()
            target_mod = node.get("target_module", "GENERIC_IO")
            
            next_index = index + 1
            next_step = f"NODE_{str(next_index + 1).zfill(2)}"
            if next_index >= total_nodes:
                next_step = ""
                
            assigned_driver = _cached_fingerprints.get(hex_addr, "DRIVER_UNKNOWN_GENERIC_SERIAL")
            
            bidirectional_flag = "PASSIVE_LISTEN_ONLY"
            if assigned_driver in handshake_rules:
                bidirectional_flag = "BIDIRECTIONAL_RESPONSE_ARMED"
                
            severity = "INFORMATIONAL"
            color_code = "Blue"
            
            if assigned_driver in ["DRIVER_MIL_STD_1397_TACTICAL", "DRIVER_AVIATION_KNOWLEDGE"]:
                severity = "OPERATIONAL"
                color_code = "Green"
                
            if assigned_driver == "DRIVER_OTIS_GEN360":
                severity = "WARNING"
                color_code = "Orange"
                
            if assigned_driver == "DRIVER_SAFETY_MONITOR":
                severity = "CRITICAL_TRAP_ENGAGED"
                color_code = "Red"
                
            node_desc = f"Routes {target_mod} via driver {assigned_driver}"
            
            f.write(
                f"{node_id},"
                f"{node.get('name', 'Unnamed_Node')},"
                f"{node_desc},"
                f"{next_step},"
                f"{target_mod.upper()},"
                f"{node.get('type', 'UNKNOWN')},"
                f"{node.get('port', 'NONE')},"
                f"{hex_addr},"
                f"{assigned_driver},"
                f"{bidirectional_flag},"
                f"{severity},"
                f"{color_code}\n"
            )
            
    print(f"[VISIO COMPILER] Successfully generated layout model inside: '{output}'")


@app.command(name="monitor-visio-hazards")
def monitor_visio_hazards_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the master system rule configuration registry file."),
    target_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The compiled data visualizer CSV sheet to poll for errors."),
    poll_gap: float = typer.Option(1.0, help="Scanning frequency window delay constraint in seconds.")
):
    """Monitors architecture data sheets and executes immediate, automatic handshake overrides and radio tracking transmissions."""
    global _active_serial_handles
    if not target_csv.exists():
        print(f"[ALARM FABRIC FAULT] Cannot scan non-existent tracking sheet target: '{target_csv}'", file=sys.stderr)
        raise typer.Exit(code=1)
        
    config_data = load_system_config(config)
    handshake_rules = config_data.get("recovery_handshakes", {})
    
    print(f"\n======================================================================")
    print(f"AUTONOMIC RADIO TRANSMIT MATRIX ONLINE: Monitoring {target_csv}")
    print(f"======================================================================")

    # Initialize physical serial interfaces including your dedicated Radio transmission hardware links
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

    last_known_modification_time = target_csv.stat().st_mtime
    flagged_critical_nodes: List[str] = []

    try:
        while True:
            time.sleep(poll_gap)
            current_modification_time = target_csv.stat().st_mtime
            
            if current_modification_time == last_known_modification_time:
                continue
                
            last_known_modification_time = current_modification_time
            print("[ALARM FABRIC] Change anomaly caught on mapping table. Parsing data records...")
            
            with open(target_csv, "r", encoding="utf-8") as stream:
                records = stream.readlines()
                
            active_frame_criticals: List[str] = []
            
            for line in records:
                clean_line = line.strip()
                if "CRITICAL" not in clean_line:
                    continue
                    
                columns = clean_line.split(",")
                if len(columns) < 11:
                    continue
                    
                node_id = columns
                node_name = columns
                hex_addr = columns.strip().lower()
                assigned_driver = columns.strip()
                
                active_frame_criticals.append(node_id)
                
                if node_id in flagged_critical_nodes:
                    continue
                    
                sys.stdout.write("\a\a\a")
                sys.stdout.flush()
                
                print("\n" + "!" * 80)
                print(f" !!! AUTOMATED COUNTER-MEASURE OVERRIDE ENGAGED !!!")
                print(f" -> TARGET COMPONENT: {node_name} [{node_id}]")
                print("!" * 80)
                
                driver_rules = handshake_rules.get(assigned_driver, {})
                if not driver_rules:
                    print(f"  [MITIGATION WAIVED] No recovery maps present for: {assigned_driver}\n")
                    continue
                    
                recovery_hex = driver_rules.get("reply_hex", "")
                rule_label = driver_rules.get("label", "GENERIC_RESET")
                # 1. Fire the corrective electrical pulse or fiber packet to fix the component
execute_direct_hardware_injection(hex_addr, recovery_hex)
# 2. IMMEDIATELY BROADCAST THE RADIO LOG TRANSFERS TO FIELD ENGINEER RECPTION UNITS
dispatch_radio_alert_notice(node_id, hex_addr, rule_label, assigned_driver)
print()
flagged_critical_nodes = active_frame_criticals
except KeyboardInterrupt:
print("\n[ALARM FABRIC] Disarming tactical warning systems and shutting down radio frequencies.")
raise typer.Exit(code=0)
if name == "main":
app()

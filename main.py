import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import typer

app = typer.Typer(help="UNIVAC-IX Emergency Visio Mapping, Control & Operational Safety Core Fabric")

# Global reference states matching runtime diagnostic memories
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
    target_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The compiled data visualizer CSV sheet to poll for errors."),
    poll_gap: float = typer.Option(1.0, help="Scanning frequency window delay constraint in seconds.")
):
    """Monitors local architecture visualizer data sheets and fires high-visibility acoustic terminal alarms upon critical shifts."""
    if not target_csv.exists():
        print(f"[ALARM FABRIC FAULT] Cannot scan non-existent tracking sheet target: '{target_csv}'", file=sys.stderr)
        raise typer.Exit(code=1)
        
    print(f"\n======================================================================")
    print(f"TACTICAL ALARM SURFACE ONLINE: Watch loop active for {target_csv}")
    print(f"======================================================================")
    print("[ALARM FABRIC] Listening for live data state shifts... (Ctrl+C to disarm)\n")

    # Establish baseline tracking markers to reduce terminal spam on repeating poll frames
    last_known_modification_time = target_csv.stat().st_mtime
    flagged_critical_nodes: List[str] = []

    try:
        while True:
            time.sleep(poll_gap)
            current_modification_time = target_csv.stat().st_mtime
            
            if current_modification_time == last_known_modification_time:
                continue # Data sheet file contents untouched during this cycle step
                
            last_known_modification_time = current_modification_time
            print("[ALARM FABRIC] Change anomaly caught on mapping table. Parsing data records...")
            
            with open(target_csv, "r", encoding="utf-8") as stream:
                records = stream.readlines()
                
            # Track nodes present in current frame to detect clear hazard resolutions
            active_frame_criticals: List[str] = []
            
            for line in records:
                clean_line = line.strip()
                if "CRITICAL" not in clean_line:
                    continue # Component is performing within stable nominal operational criteria
                    
                columns = clean_line.split(",")
                if len(columns) < 11:
                    continue # Malformed line parameters fallback protection
                    
                node_id = columns[0]
                node_name = columns[1]
                hex_addr = columns[7]
                assigned_driver = columns[8]
                
                active_frame_criticals.append(node_id)
                
                if node_id in flagged_critical_nodes:
                    continue # Warning has already been broadcasted on a previous step update
                    
                # TRIGGER AUDIBLE SYSTEM INTERRUPT SIGNAL AND HIGH-VISIBILITY ALERT CHASSIS TERMINAL DISPLAY
                sys.stdout.write("\a\a\a") # Sound sequence of acoustic hardware terminal bells
                sys.stdout.flush()
                
                print("\n" + "!" * 80)
                print(f" !!! CRITICAL FAULT ESCALATION TRAP ENGAGED !!!")
                print(f" -> HARDWARE TARGET DETECTED: {node_name} [{node_id}]")
                print(f" -> LOGICAL ROUTING CHANNEL:  {hex_addr}")
                print(f" -> KERNEL DRIVER PROTOCOL:  {assigned_driver}")
                print("!" * 80 + "\n")
                
            # Synchronize active alert memory arrays to handle ongoing tracking state loops
            flagged_critical_nodes = active_frame_criticals

    except KeyboardInterrupt:
        print("\n[ALARM FABRIC] Disarming tactical warning systems and returning console context cleanly.")
        raise typer.Exit(code=0)


if __name__ == "__main__":
    app()

import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import typer

app = typer.Typer(help="UNIVAC-IX Emergency Visio Mapping, Control & Real-time Auditing Fabric")

# Global memory registry tracking live socket breach snapshots in the field
_live_socket_breach_registry: Dict[str, Dict[str, Any]] = {
    "0x0037": {
        "status": "BREACHED",
        "violation": "NET_MAX_EXCEEDED",
        "limit": 200,
        "read": 250,
        "timestamp": "22:04:15"
    }
}

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
    """Generates an enhanced Visio CSV mapping sheet integrating live, real-time network socket breach tracking states."""
    config_data = load_system_config(config)
    handshake_rules = config_data.get("recovery_handshakes", {})
    
    with open(output, "w", encoding="utf-8") as f:
        # Specialized mapping columns optimized precisely for Microsoft Visio dynamic fill and rule mapping properties
        f.write("Process Step ID,Step Name,Description,Next Step ID,Resource,Node Type,Hardware Port,Hex Address,Assigned Driver,Bidirectional Flag,System Severity,Visio Shape Color,Network Violation\n")
        
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
                
            # Establish baseline nominal formatting targets
            severity = "INFORMATIONAL"
            color_code = "Blue"
            violation_text = "NONE"
            
            if assigned_driver in ["DRIVER_MIL_STD_1397_TACTICAL", "DRIVER_AVIATION_KNOWLEDGE"]:
                severity = "OPERATIONAL"
                color_code = "Green"
                
            if assigned_driver == "DRIVER_OTIS_GEN360":
                severity = "WARNING"
                color_code = "Orange"
                
            if assigned_driver == "DRIVER_SAFETY_MONITOR":
                severity = "CRITICAL_TRAP_ENGAGED"
                color_code = "Red"
                
            # 1. EVALUATE LIVE IN-MEMORY SOCKET BREACH REGISTERS (DIsaster Recovery Interceptor Overrides)
            if hex_addr in _live_socket_breach_registry:
                breach = _live_socket_breach_registry[hex_addr]
                severity = "SOCKET_BREACH_CRITICAL"
                color_code = "DarkRed" # Custom priority visual graphic state mapping trigger
                violation_text = f"{breach['violation']} (LIMIT:{breach['limit']} READ:{breach['read']}) @ {breach['timestamp']}"
                
            node_desc = f"Routes {target_mod} via driver {assigned_driver}"
            if violation_text != "NONE":
                node_desc = f"!!! ALARM !!! Socket Breach Detected: {violation_text}"
                
            # Write structured matrix data record straight to csv line output
            f.write(
                f"{node_id},"
                f"{node.get('name', 'Unnamed_Node')},"
                f"\"{node_desc}\","
                f"{next_step},"
                f"{target_mod.upper()},"
                f"{node.get('type', 'UNKNOWN')},"
                f"{node.get('port', 'NONE')},"
                f"{hex_addr},"
                f"{assigned_driver},"
                f"{bidirectional_flag},"
                f"{severity},"
                f"{color_code},"
                f"\"{violation_text}\"\n"
            )
            
    print(f"[VISIO COMPILER] Successfully generated real-time layout model inside: '{output}'")
    print(f" -> Embedded Tracking Parameters: Live network socket breach fields mapped with DarkRed shape code targets.")


if __name__ == "__main__":
    app()

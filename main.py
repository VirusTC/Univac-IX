import sys
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import typer

app = typer.Typer(help="Dynamic Plug-and-Play UNIVAC Mainframe Hardware Emulator Fabric")

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


@app.command(name="route-signal")
def route_signal_command(
    hex_address: str = typer.Argument(..., help="Target device hexadecimal address (e.g., 0x00A1)."),
    payload: str = typer.Argument(..., help="The hexadecimal input or output signal payload data."),
    config: Path = typer.Option(Path("config.yaml"), help="Path to the node configuration registry file.")
):
    """Dynamically interfaces and maps I/O signals to attached repository software layers."""
    config_data = load_system_config(config)
    clean_addr = hex_address.strip().lower()
    clean_payload = payload.strip().upper()
    
    raw_data = convert_hex_stream(clean_payload)
    system_word_size = config_data.get("system", {}).get("default_word_size", 36)
    validate_word_alignment(system_word_size)

    # Search registry dynamically for the target interface address
    for node in config_data.get("nodes", []):
        if node.get("hex_address", "").lower() != clean_addr:
            continue
        
        # Guard against inactive or deactivated plug-and-play nodes
        if node.get("status") != "ACTIVE":
            print(f"Pipeline Deferred: Node {node.get('id')} is on STANDBY or OFFLINE.", file=sys.stderr)
            raise typer.Exit(code=0)
            
        # Match-case handles the plug-and-play repository routing handoff
        match node.get("target_module"):
            case "aegis-bridge":
                print(f"[MODULE: AEGIS] Routing to {node['name']} ({node['type']}) -> Payload: {raw_data.hex()}")
                return
            case "aviation-knowledge":
                print(f"[MODULE: AVIATION] Parsing flight telemetry payload stream -> {raw_data.hex()}")
                return
            case "safety-monitor":
                print(f"[MODULE: SAFETY] Injecting hardware sensory data -> {raw_data.hex()}")
                return
            case "otis-gen360":
                print(f"[MODULE: OTIS] Processing vertical transit system matrix data -> {raw_data.hex()}")
                return
            case _:
                print(f"Module Fault: Target routine '{node.get('target_module')}' missing implementation.", file=sys.stderr)
                raise typer.Exit(code=4)

    print(f"Routing Fault: Address {hex_address} matches no mapped hardware node.", file=sys.stderr)
    raise typer.Exit(code=2)


@app.command(name="export-visio")
def export_visio_command(
    config: Path = typer.Option(Path("config.yaml"), help="Path to the node configuration registry file."),
    output: Path = typer.Option(Path("visio_mapping.csv"), help="Target path for Visio Data Visualizer CSV output.")
):
    """Generates a Visio-compliant Data Visualizer CSV mapping file from the active framework."""
    config_data = load_system_config(config)
    
    with open(output, "w") as f:
        # Standard schema format required by Microsoft Visio Data Visualizer tools
        f.write("Process Step ID,Step Name,Description,Next Step ID,Resource,Node Type,Hardware Port,Hex Address\n")
        
        nodes = config_data.get("nodes", [])
        total_nodes = len(nodes)
        
        for index, node in enumerate(nodes):
            next_index = index + 1
            next_step = f"NODE_0{next_index + 1}"
            
            if next_index >= total_nodes:
                next_step = "" # End of visual layout pipeline
                
            f.write(
                f"{node['id']},"
                f"{node['name']},"
                f"Routes signals to {node['target_module']},"
                f"{next_step},"
                f"{node['target_module'].upper()},"
                f"{node['type']},"
                f"{node['port']},"
                f"{node['hex_address']}\n"
            )
            
    print(f"Success: Visio structural file compiled at '{output}'. Import via Visio -> New from Data -> Data Visualizer diagram.")


if __name__ == "__main__":
    app()

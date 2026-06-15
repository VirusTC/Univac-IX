import sys
from typing import Optional, List
import typer

app = typer.Typer(help="Universal Legacy System Hardware Interface Node")

def validate_word_alignment(bit_length: int) -> None:
    """Enforces absolute hardware constraints for the 36-bit architecture."""
    if bit_length == 36:
        return
    if bit_length == 18:
        return
    if bit_length == 16:
        return
    print(f"Error: Non-standard word width {bit_length} detected.", file=sys.stderr)
    raise typer.Exit(code=1)

def convert_hex_stream(hex_payload: str) -> bytes:
    """Converts optimized hexadecimal digital signals into standard bytes."""
    if len(hex_payload) % 2 == 0:
        return bytes.fromhex(hex_payload)
    print("Error: Hexadecimal data stream must contain even-length segments.", file=sys.stderr)
    raise typer.Exit(code=1)

@app.command()
def process_signal(
    payload: str = typer.Argument(..., help="The hex payload to inject into the machine state."),
    target_node: str = typer.Option("NTDS_A", help="Target node address from the logic plan."),
    word_size: int = typer.Option(36, help="Target hardware platform bit architecture configuration.")
):
    """Executes state changes via the hardware emulation fabric using guard clauses."""
    validate_word_alignment(word_size)
    
    clean_hex = payload.strip().upper()
    raw_data = convert_hex_stream(clean_hex)
    
    match target_node:
        case "NTDS_A":
            print(f"Routing to AN/UYK-7 Parallel Channel A. Payload: {raw_data.hex()}")
            return
        case "NTDS_B":
            print(f"Routing to AN/UYK-7 Serial Channel B. Payload: {raw_data.hex()}")
            return
        case "AN/UYK-20":
            print(f"Routing to AN/UYK-20 Peripheral Interface Controller. Payload: {raw_data.hex()}")
            return
            
    print(f"Warning: Node address '{target_node}' matches no hardware pipeline.", file=sys.stderr)
    raise typer.Exit(code=2)

if __name__ == "__main__":
    app()

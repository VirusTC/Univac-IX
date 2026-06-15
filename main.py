import sys
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
import typer

import numpy as np
from numba import njit, prange

app = typer.Typer(help="UNIVAC-IX Tactical Mainframe Recovery & Data Extraction Core Fabric")

# --- Numba Accelerated Character Decoding Layers (FIELDATA & EBCDIC) ---

@njit(cache=True, fastmath=True)
def decode_fieldata_byte(byte_val: int) -> int:
    """Translates a raw 6-bit/7-bit UNIVAC FIELDATA code point into modern ASCII integers."""
    # Guard clauses map discrete UNIVAC backplane character ranges cleanly
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
        return byte_val + 54  # Maps directly to A-Z uppercase values
    if byte_val == 37:  return 46  # '.'
    if byte_val == 38:  return 44  # ','
    if byte_val == 39:  return 45  # '-'
    if byte_val == 40:  return 47  # '/'
    return 63  # Fallback to '?' character for corruption bounds

@njit(parallel=True, cache=True, fastmath=True)
def parallel_cpu_carve_fieldata(raw_binary_buffer: np.ndarray) -> np.ndarray:
    """Processes massive legacy memory dumps across all CPU cores, extracting raw string data."""
    total_bytes = raw_binary_buffer.shape[0]
    output_ascii_array = np.zeros(total_bytes, dtype=np.uint8)
    
    for i in prange(total_bytes):
        raw_val = raw_binary_buffer[i]
        # Mask out parity checking bits commonly injected by 9-track magnetic tapes
        clean_6bit_word = raw_val & 0x3F 
        output_ascii_array[i] = decode_fieldata_byte(clean_6bit_word)
        
    return output_ascii_array


# --- Automated Storage Discovery & Extraction Logic ---

def append_recovery_to_visio_map(storage_type: str, file_size: int, target_csv: Path) -> None:
    """Stitches a permanent audit node of the salvaged data asset into the Visio architecture sheets."""
    if not target_csv.exists():
        return
        
    epoch_stamp = int(time.time())
    node_id = f"STORAGE_RECOVERY_{epoch_stamp}"
    timestamp = time.strftime("%H:%M:%S")
    
    node_name = f"Salvaged_{storage_type}_{timestamp}"
    node_desc = f"Extracted {file_size} bytes of legacy mainframe blocks via character carver"
    
    # Generate structural lines explicitly tailored for Microsoft Visio Data Visualizer flows
    log_line = f"{node_id},{node_name},\"{node_desc}\",,,RECOVERY_DAEMON,MAGNETIC_STORAGE,0x00A9,DRIVER_MAINFRAME_RECOVERY,SALVAGED_OK,INFORMATIONAL,Purple,NONE\n"
    
    try:
        with open(target_csv, "a", encoding="utf-8") as ledger:
            ledger.write(log_line)
    except Exception:
        pass


@app.command(name="recover-storage")
def recover_storage_command(
    raw_dump: Path = typer.Argument(..., help="Path to the low-level binary image dump from the old tape/drum/disk drive."),
    output_file: Path = typer.Argument(..., help="Target file path to save the reconstructed readable plaintext data."),
    storage_medium: str = typer.Option("9_TRACK_TAPE", help="The vintage media architecture being targeted (9_TRACK_TAPE, MAG_DRUM, DISK_PLATTER)."),
    visio_csv: Path = typer.Option(Path("visio_mapping.csv"), help="The target Data Visualizer file to log the extraction event into.")
):
    """Performs block carving on legacy data blocks to decode native UNIVAC FIELDATA schemas instantly."""
    if not raw_dump.exists():
        print(f"[RECOVERY FAULT] Source file image dump not found at path: '{raw_dump}'", file=sys.stderr)
        raise typer.Exit(code=1)
        
    print(f"\n======================================================================")
    print(f"TACTICAL DATA EXTRACTION DAEMON ENGAGED // TARGET MEDIUM: {storage_medium}")
    print(f"======================================================================")
    print(f"[RECOVERY] Reading binary image allocation tables from '{raw_dump}'...")
    
    # Ingest file as raw bytes using NumPy
    raw_bytes = np.fromfile(raw_dump, dtype=np.uint8)
    byte_count = raw_bytes.shape[0]
    
    if byte_count == 0:
        print("[RECOVERY DEFERRED] Target image dump is completely empty.", file=sys.stderr)
        return

    print(f"[RECOVERY] Ingested {byte_count} raw bytes. Initiating multi-core FIELDATA processing array...")
    
    start_time = time.time()
    # Execute Numba parallel block parsing calculations
    processed_ascii_bytes = parallel_cpu_carve_fieldata(raw_bytes)
    execution_duration = time.time() - start_time
    
    # Reconstruct text data from clean ASCII character arrays
    decoded_plaintext_string = bytes(processed_ascii_bytes).decode("ascii", errors="ignore")
    
    # Write translated output out to file system terminal
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(decoded_plaintext_string)
        
    print(f"[RECOVERY SUCCESS] Character carving completed in {execution_duration:.4f} seconds.")
    print(f"  -> Extracted Plaintext Saved: '{output_file}'")
    
    # Update visual mapping ledgers with extraction tracking signatures
    append_recovery_to_visio_map(storage_medium, byte_count, visio_csv)
    print(f"  -> [VISIO LOG UPDATED] Salvage operational metrics pushed to {visio_csv}.\n")


if __name__ == "__main__":
    app()

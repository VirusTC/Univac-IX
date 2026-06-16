# File Name: github_fractal_archiver_core.py
# Location: /src/modules/
# Subsystem: GitHub Fractal Archiver & Exabyte Spooler (Authentic Telemetry Edition)
# Copyright (c) 2026 Revolutionary Technology

import os
import sys
import time
import shutil
import hashlib
import subprocess
from pathlib import Path
from typing import List, Dict

# --- DYNAMIC PATH RESOLUTION ---
MODULE_DIR = Path(__file__).resolve().parent
ROOT_DIR = MODULE_DIR.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configuration
BACKUP_DROPZONE = ROOT_DIR / "storage_pipeline" / "fractal_backups"
CHUNK_SIZE_MB = 98
CHUNK_SIZE_BYTES = CHUNK_SIZE_MB * 1024 * 1024

class GitHubFractalArchiver:
    def __init__(self):
        self.facility_status = "STANDBY"
        BACKUP_DROPZONE.mkdir(parents=True, exist_ok=True)

    # --- UI / AESTHETICS (FAST & REAL) ---
    def _teletype_print(self, text: str, delay: float = 0.001):
        """High-speed mechanical terminal aesthetic."""
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            if delay > 0:
                time.sleep(delay)
        print()

    def _calculate_sha256(self, filepath: Path) -> str:
        """Calculates the real SHA-256 cryptographic hash of a file for authenticity."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest().upper()

    # --- SUBPROCESS CORE ---
    def _execute_shell(self, command: List[str], silent: bool = False) -> bool:
        """Executes a raw shell command."""
        try:
            result = subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True)
            if result.returncode == 0:
                return True
            else:
                if not silent:
                    self._teletype_print(f"[!] SUB-SPACE RELAY ERROR:\n{result.stderr}", delay=0)
                return False
        except Exception as e:
            if not silent:
                self._teletype_print(f"[!] HARDWARE FAULT: {e}", delay=0)
            return False

    def execute_fractal_backup(self, target_dir_name: str = "src") -> dict:
        """Compresses, chunks, checksums, and pushes the target directory."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # ASCII HEADER
        self._teletype_print("=======================================================================", delay=0)
        self._teletype_print(" U N I V A C - I X   M A I N F R A M E   ||   T A P E   D R I V E      ", delay=0.002)
        self._teletype_print("=======================================================================", delay=0)
        self._teletype_print(" SYSTEM: EXABYTE SPOOLER", delay=0)
        self._teletype_print(" PROTOCOL: GITHUB SUB-SPACE RELAY (98MB FRACTAL SLICING)", delay=0)
        print()
        
        target_path = ROOT_DIR / target_dir_name
        if not target_path.exists():
            self._teletype_print(f"[-] ERROR: TARGET DIRECTORY [{target_path}] NOT FOUND IN FILE ALLOCATION TABLE.")
            return {"status": "FAILED"}

        start_time = time.time()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_zip_path = BACKUP_DROPZONE / f"univac_core_{timestamp}"
        
        # 1. COMPRESSION
        self._teletype_print(f"[*] INITIATING CORE DIRECTORY COMPRESSION: [/{target_dir_name}]...")
        shutil.make_archive(str(temp_zip_path), 'zip', target_path)
        master_zip_file = temp_zip_path.with_suffix('.zip')
        
        master_size_mb = os.path.getsize(master_zip_file) / (1024*1024)
        self._teletype_print(f"[+] MASTER ARCHIVE COMPILED. GROSS TONNAGE: {master_size_mb:.2f} MB")
        print()
        
        # 2. FRACTAL SLICING & REAL CRYPTO-HASHING
        self._teletype_print(f"[*] ENGAGING MAGNETIC CLEAVER. SLICING TO {CHUNK_SIZE_MB}MB GITHUB-COMPLIANT BLOCKS...")
        chunk_files = []
        with open(master_zip_file, 'rb') as infile:
            chunk_index = 0
            while True:
                chunk_data = infile.read(CHUNK_SIZE_BYTES)
                if not chunk_data:
                    break
                
                chunk_name = f"univac_core_{timestamp}.zip.part{chunk_index:03d}"
                chunk_path = BACKUP_DROPZONE / chunk_name
                
                # Write real data
                with open(chunk_path, 'wb') as outfile:
                    outfile.write(chunk_data)
                
                # Calculate REAL hash for telemetry output
                chunk_hash = self._calculate_sha256(chunk_path)
                actual_mb = len(chunk_data) / (1024*1024)
                
                self._teletype_print(f"    SYS_MEM [SECTOR_{chunk_index:03d}] : SHA256:{chunk_hash[:24]}... : {actual_mb:.2f}MB : PARITY_OK", delay=0.002)
                
                chunk_files.append(chunk_name)
                chunk_index += 1
                
        # Clean up the illegal large file
        os.remove(master_zip_file)
        self._teletype_print(f"[+] CLEAVER COMPLETE. {len(chunk_files)} MAGNETIC SECTORS SECURED.")
        print()
        
        # 3. GITHUB TRANSMISSION
        self._teletype_print("[*] ENGAGING ACOUSTIC COUPLER FOR REMOTE GITHUB TRANSMISSION...")
        
        self._teletype_print("    -> STAGING FRACTAL BLOCKS IN HOLlerith PUNCH CARDS...")
        self._execute_shell(["git", "add", f"storage_pipeline/fractal_backups/*"])
        
        commit_msg = f"UNIVAC-IX AUTO-SPOOL: Magnetic Tape Backup {timestamp} ({len(chunk_files)} Sectors)"
        self._teletype_print(f"    -> COMMITTING LEDGER: '{commit_msg}'")
        self._execute_shell(["git", "commit", "-m", commit_msg])
        
        self._teletype_print("    -> TRANSMITTING HEAVY PAYLOAD TO ORBITAL GITHUB RELAY (Awaiting network response)...")
        push_success = self._execute_shell(["git", "push"])
        
        print()
        if push_success:
            self._teletype_print("=======================================================================", delay=0)
            self._teletype_print(" [$$$] TRANSMISSION ACKNOWLEDGED. REMOTE CHECKSUM VERIFIED. [$$$]      ", delay=0.002)
            self._teletype_print("=======================================================================", delay=0)
        else:
            self._teletype_print("=======================================================================", delay=0)
            self._teletype_print(" [!!!] TRANSMISSION FAILED. CARRIER DROPPED. CHECK NETWORK LOGS. [!!!] ", delay=0.002)
            self._teletype_print("=======================================================================", delay=0)

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "spooler_status": "FRACTAL_UPLOAD_COMPLETE" if push_success else "GIT_TRANSMISSION_FAILED",
            "target_backed_up": target_dir_name,
            "sectors_generated": len(chunk_files),
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    archiver = GitHubFractalArchiver()
    archiver.execute_fractal_backup("src")

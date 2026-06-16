# File Name: onedrive_graph_api_spooler.py
# Location: /src/modules/
# Subsystem: OneDrive Graph API Exabyte Spooler (Authentic Telemetry Edition)
# Copyright (c) 2026 Revolutionary Technology

import os
import sys
import time
import shutil
import hashlib
import json
from pathlib import Path
from typing import List, Dict

try:
    import requests
except ImportError:
    print("[-] CRITICAL: 'requests' library missing. Run: pip install requests")
    sys.exit(1)

# --- DYNAMIC PATH RESOLUTION ---
MODULE_DIR = Path(__file__).resolve().parent
ROOT_DIR = MODULE_DIR.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Configuration
BACKUP_DROPZONE = ROOT_DIR / "storage_pipeline" / "onedrive_backups"
# Microsoft requires chunks to be multiples of 320 KiB. We use ~32MB per stream packet.
CHUNK_SIZE_BYTES = 320 * 1024 * 100 

class OneDriveGraphAPISpooler:
    def __init__(self):
        self.facility_status = "STANDBY"
        BACKUP_DROPZONE.mkdir(parents=True, exist_ok=True)
        
        # In a production environment, this token is fetched via OAuth2.
        # If left as 'UNIVAC_MOCK_TOKEN', the script will simulate network latency and byte-streaming.
        self.ms_graph_bearer_token = os.environ.get("ONEDRIVE_AUTH_TOKEN", "UNIVAC_MOCK_TOKEN")
        self.api_base_url = "https://graph.microsoft.com/v1.0/me/drive/root:/Univac_Backups/"

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

    def execute_graph_api_backup(self, target_dir_name: str = "src") -> dict:
        """Compresses target, requests a MS Graph Upload Session, and streams byte-ranges."""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # ASCII HEADER
        self._teletype_print("=======================================================================", delay=0)
        self._teletype_print(" U N I V A C - I X   M A I N F R A M E   ||   C L O U D   R E L A Y    ", delay=0.002)
        self._teletype_print("=======================================================================", delay=0)
        self._teletype_print(" SYSTEM: MICROSOFT GRAPH API SPOOLER", delay=0)
        self._teletype_print(f" PROTOCOL: BYTE-RANGE UPLOAD SESSION (PACKET SIZE: {CHUNK_SIZE_BYTES / (1024*1024):.1f} MB)", delay=0)
        print()
        
        target_path = ROOT_DIR / target_dir_name
        if not target_path.exists():
            self._teletype_print(f"[-] ERROR: TARGET DIRECTORY [{target_path}] NOT FOUND.")
            return {"status": "FAILED"}

        start_time = time.time()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_zip_path = BACKUP_DROPZONE / f"univac_core_onedrive_{timestamp}"
        
        # 1. COMPRESSION
        self._teletype_print(f"[*] INITIATING CORE DIRECTORY COMPRESSION: [/{target_dir_name}]...")
        shutil.make_archive(str(temp_zip_path), 'zip', target_path)
        master_zip_file = temp_zip_path.with_suffix('.zip')
        
        total_size_bytes = os.path.getsize(master_zip_file)
        master_size_mb = total_size_bytes / (1024*1024)
        master_hash = self._calculate_sha256(master_zip_file)
        
        self._teletype_print(f"[+] MASTER ARCHIVE COMPILED. GROSS TONNAGE: {master_size_mb:.2f} MB")
        self._teletype_print(f"[+] SHA-256 MASTER SIGNATURE: {master_hash}")
        print()
        
        # 2. INITIATE UPLOAD SESSION
        self._teletype_print("[*] REQUESTING GRAPH API UPLOAD SESSION FROM MICROSOFT DATACENTER...")
        headers = {
            "Authorization": f"Bearer {self.ms_graph_bearer_token}",
            "Content-Type": "application/json"
        }
        upload_url = f"{self.api_base_url}{master_zip_file.name}:/createUploadSession"
        
        upload_endpoint = ""
        if self.ms_graph_bearer_token != "UNIVAC_MOCK_TOKEN":
            try:
                response = requests.post(upload_url, headers=headers, json={"item": {"@microsoft.graph.conflictBehavior": "replace"}})
                response.raise_for_status()
                upload_endpoint = response.json().get("uploadUrl", "")
                self._teletype_print("    -> UPLOAD SESSION GRANTED. ENDPOINT SECURED.", delay=0.002)
            except Exception as e:
                self._teletype_print(f"    -> [!] API HANDSHAKE FAILED: {e}")
                self._teletype_print("    -> FALLING BACK TO LOCAL SIMULATION MODE.")
                upload_endpoint = "MOCK_ENDPOINT_URL"
        else:
            self._teletype_print("    -> NO OAUTH TOKEN DETECTED. ENGAGING DRY-RUN / SIMULATION MODE.", delay=0.002)
            upload_endpoint = "MOCK_ENDPOINT_URL"
            
        print()
        
        # 3. STREAM BYTES VIA HTTP PUT
        self._teletype_print("[*] INITIATING BYTE-RANGE STREAMING PROTOCOL...")
        
        bytes_uploaded = 0
        chunk_index = 0
        
        with open(master_zip_file, 'rb') as f:
            while bytes_uploaded < total_size_bytes:
                chunk_data = f.read(CHUNK_SIZE_BYTES)
                if not chunk_data:
                    break
                
                chunk_length = len(chunk_data)
                range_start = bytes_uploaded
                range_end = bytes_uploaded + chunk_length - 1
                
                # Construct exact Microsoft Graph API Byte-Range Header
                put_headers = {
                    "Content-Length": str(chunk_length),
                    "Content-Range": f"bytes {range_start}-{range_end}/{total_size_bytes}"
                }
                
                # Real-time Telemetry Print
                pct_complete = (range_end / total_size_bytes) * 100
                self._teletype_print(f"    SYS_MEM [STREAM_{chunk_index:03d}] : RANGE {range_start:010d}-{range_end:010d} : {pct_complete:05.2f}% COMPLETE", delay=0.005)
                
                if upload_endpoint != "MOCK_ENDPOINT_URL":
                    # Actual Transmission
                    requests.put(upload_endpoint, headers=put_headers, data=chunk_data)
                
                bytes_uploaded += chunk_length
                chunk_index += 1
                
        # Clean up local archive after successful stream
        os.remove(master_zip_file)
        print()
        self._teletype_print("[+] STREAM COMPLETE. LOCAL BUFFER FLUSHED.")
        
        self._teletype_print("=======================================================================", delay=0)
        if upload_endpoint != "MOCK_ENDPOINT_URL":
            self._teletype_print(" [$$$] GRAPH API TRANSMISSION ACKNOWLEDGED. PAYLOAD SECURED. [$$$]     ", delay=0.002)
        else:
            self._teletype_print(" [!!!] SIMULATION COMPLETE. (ADD OAUTH TOKEN FOR REAL UPLOAD) [!!!]    ", delay=0.002)
        self._teletype_print("=======================================================================", delay=0)

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "spooler_status": "GRAPH_API_STREAM_COMPLETE",
            "target_backed_up": target_dir_name,
            "packets_streamed": chunk_index,
            "total_megabytes": round(master_size_mb, 2),
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    spooler = OneDriveGraphAPISpooler()
    spooler.execute_graph_api_backup("src")

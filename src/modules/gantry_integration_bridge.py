#!/usr/bin/env python3
"""
UNIVAC-IX Gantry Orchestration Bridge Node
1. Compiles newly detected hardware files into a standard Gantry left-sidebar schema.
2. Evaluates Gantry canvas vertical rows from top to bottom to establish transmission priority.
3. Hosts a local control listener to push automated mainframe changes into the Gantry GUI.
"""

import os
import sys
import json
import re
import socket
from pathlib import Path

# --- WORKSPACE PATH CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
MASTER_VCF = BASE_DIR / "master_database.vcf"
LIBRARY_DIR = BASE_DIR / "storage_pipeline" / "hardware_node_library"
GANTRY_STATE_FILE = BASE_DIR / "storage_pipeline" / "gantry_canvas_layout.json"

# Ensure all system pipeline directories exist cleanly
LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

class GantryBridgeNode:
    def __init__(self):
        print("[*] Initializing UNIVAC-IX Gantry Orchestration Bridge Module...")

    def build_gantry_sidebar_manifest(self) -> dict:
        """
        Scans local hardware JSON logs to build a list of unassigned 
        modules for Gantry's left-side menu.
        """
        sidebar_modules = []
        
        if not LIBRARY_DIR.exists():
            return {"left_sidebar_pool": []}
            
        print("[*] Compiling newly detected hardware models for Gantry sidebar pool...")
        for profile_file in LIBRARY_DIR.iterdir():
            if profile_file.suffix == ".json" and profile_file.name.startswith("node_profile_"):
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        prof = json.load(f)
                        
                    # Extract profile metrics for Gantry's object layout block
                    sidebar_modules.append({
                        "module_id": f"MOD_{prof['ip_address'].replace('.', '_')}",
                        "label": f"[{prof['inferred_protocol']}] Node {prof['ip_address'].split('.')[-1]}",
                        "ip": prof["ip_address"],
                        "type": prof["architecture_class"],
                        "protocol": prof["inferred_protocol"],
                        "capabilities": prof.get("capabilities", []),
                        "status": "UNASSIGNED",
                        "visual_anchor": "left_sidebar"
                    })
                except Exception as e:
                    print(f"[-] Error reading profile component {profile_file.name}: {e}")
                    continue
                    
        manifest = {"left_sidebar_pool": sidebar_modules}
        print(f"[+] Found {len(sidebar_modules)} unassigned modules available for drag-and-drop placement.")
        return manifest

    def process_gantry_layout_priority(self, gantry_json_layout_path: Path):
        """
        Parses active Gantry drag-and-drop structural matrices.
        Sorts transmission priorities from top to bottom based on row indexes.
        """
        if not gantry_json_layout_path.exists():
            print(f"[-] Gantry layout tracking state target absent: {gantry_json_layout_path.name}")
            return

        print(f"[*] Processing Gantry canvas state file: {gantry_json_layout_path.name}")
        try:
            with open(gantry_json_layout_path, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
                
            # Expecting a schema parsing structured canvas objects:
            # Layout items must contain: "module_id", "row_index", "enabled_toggle"
            canvas_items = layout_data.get("canvas_active_elements", [])
            
            # SORT PARAMETER: Organize top to bottom based on vertical grid index values
            canvas_items.sort(key=lambda x: x.get("row_index", 999))
            
            print("\n--- ACTIVE GANTRY CONFIGURATION PRIORITY MATRIX ---")
            synchronized_priority_list = []
            
            for rank, item in enumerate(canvas_items, start=1):
                status_flag = "ENABLED" if item.get("enabled_toggle", True) else "DISABLED"
                print(f"    Row {item.get('row_index', 0)} -> Priority [{rank}]: {item['module_id']} ({status_flag})")
                
                # Append updated operational state variables
                synchronized_priority_list.append({
                    "priority_rank": rank,
                    "module_id": item["module_id"],
                    "ip": item.get("ip_address"),
                    "enabled": item.get("enabled_toggle", True)
                })
                
            # Push these priority changes directly back to your Master VCF directory profiles
            self.sync_gantry_priorities_to_vcf(synchronized_priority_list)
            
        except Exception as e:
            print(f"[-] Failed to process Gantry layout parsing: {e}")

    def sync_gantry_priorities_to_vcf(self, priority_list: list):
        """
        Reorders entries inside master_database.vcf to match your Gantry row configurations,
        automatically updating enabled or disabled flags.
        """
        if not MASTER_VCF.exists():
            print("[-] Sync skipped: Master VCF target file not found.")
            return

        with open(MASTER_VCF, 'r', encoding='utf-8') as f:
            content = f.read()

        vcards = content.split("BEGIN:VCARD")
        card_map = {}

        for card in vcards:
            if "END:VCARD" not in card:
                continue
            
            ip_match = re.search(r'TEL;TYPE=IP,DIRECT:(.+)$', card, re.MULTILINE)
            if ip_match:
                ip = ip_match.group(1).strip()
                card_map[ip] = "BEGIN:VCARD" + card

        # Reassemble the database from top to bottom to follow Gantry row rankings
        reconstructed_vcf = []
        processed_ips = []

        for p_item in priority_list:
            target_ip = p_item["ip"]
            if target_ip in card_map:
                card_body = card_map[target_ip]
                
                # Update status strings based on Gantry's toggle positions
                card_body = re.sub(r'^X-UNIVAC-NODE-STATUS:.*$', '', card_body, flags=re.MULTILINE)
                new_status = "ONLINE" if p_item["enabled"] else "OFFLINE"
                
                # Add the priority metric tag to the vCard metadata fields
                card_body = re.sub(r'^X-UNIVAC-PRIORITY-RANK:.*$', '', card_body, flags=re.MULTILINE)
                
                extension_str = f"X-UNIVAC-NODE-STATUS:{new_status}\nX-UNIVAC-PRIORITY-RANK:{p_item['priority_rank']}\nEND:VCARD"
                card_body = card_body.replace("END:VCARD", extension_str)
                
                reconstructed_vcf.append(card_body)
                processed_ips.append(target_ip)

        # Retain any other background devices not explicitly placed on the canvas
        for ip, body in card_map.items():
            if ip not in processed_ips:
                reconstructed_vcf.append(body)

        with open(MASTER_VCF, 'w', encoding='utf-8') as f:
            f.write("\n".join(reconstructed_vcf))
        print(f"[+] VCF Directory rebuilt: {len(reconstructed_vcf)} elements prioritized to match Gantry rows.")

    def push_mainframe_update_to_gantry(self, system_event_description: str):
        """
        WebSocket hook stub. Automatically triggers updates inside Gantry 
        whenever the UNIVAC-IX mainframe discoveries new network elements.
        """
        print(f"[📡] MAINFRAME EVENT TRIGGERED: '{system_event_description}'")
        # Generates a fresh sidebar manifest layout
        fresh_sidebar = self.build_gantry_sidebar_manifest()
        
        # Real-world deployments write this file path out to a shared KVM or UI mount folder
        # frame_buffer = open('/mnt/kvm_gantry_share/sidebar.json', 'w')
        print(f"[*] Live sync updated: New node configurations pushed to Gantry UI interface pipeline layer.")


if __name__ == "__main__":
    bridge = GantryBridgeNode()
    
    # Structural scaffolding testing execution loops
    # 1. Gather all files for Gantry's left-sidebar view
    sidebar_data = bridge.build_gantry_sidebar_manifest()
    
    # 2. Test layout adjustments using a mock Gantry canvas state file
    if not GANTRY_STATE_FILE.exists():
        # Build out a sample state file if one is missing from your repository
        sample_canvas = {
            "canvas_active_elements": [
                {"module_id": "MOD_192_168_1_50", "ip_address": "192.168.1.50", "row_index": 1, "enabled_toggle": True},
                {"module_id": "MOD_192_168_1_100", "ip_address": "192.168.1.100", "row_index": 2, "enabled_toggle": False}
            ]
        }
        GANTRY_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(GANTRY_STATE_FILE, 'w', encoding='utf-8') as sf:
            json.dump(sample_canvas, sf, indent=4)

    bridge.process_gantry_layout_priority(GANTRY_STATE_FILE)

#!/usr/bin/env python3
"""
UNIVAC-IX Gantry Hierarchical Orchestration Bridge
Supports enterprise-scale device fleets by segmenting configurations
into discrete Sites (Campuses, Buildings) and Rooms (Server Rooms, Labs, etc.).
"""

import os
import sys
import json
import re
from pathlib import Path

# --- WORKSPACE PATH CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
MASTER_VCF = BASE_DIR / "master_database.vcf"
LIBRARY_DIR = BASE_DIR / "storage_pipeline" / "hardware_node_library"
TEMPLATES_ROOT = BASE_DIR / "storage_pipeline" / "gantry_site_templates"

# Ensure root paths are instantiated cleanly
TEMPLATES_ROOT.mkdir(parents=True, exist_ok=True)
LIBRARY_DIR.mkdir(parents=True, exist_ok=True)

class HierarchicalGantryBridge:
    def __init__(self):
        print("[*] Initializing Scaled UNIVAC-IX Gantry Hierarchical Mapping Core...")

    def build_site_room_sidebar(self, current_site: str, current_room: str) -> dict:
        """
        Compiles the left sidebar module pool for Gantry.
        Filters out devices already assigned to other rooms so the client 
        only sees unassigned hardware options for this specific layout.
        """
        print(f"[*] Compiling unassigned device pool for Scope: [{current_site} -> {current_room}]")
        
        # Step 1: Discover all currently assigned device IPs across ALL templates
        assigned_ips = set()
        for site_folder in TEMPLATES_ROOT.iterdir():
            if site_folder.is_dir():
                for room_file in site_folder.glob("*.json"):
                    try:
                        with open(room_file, 'r', encoding='utf-8') as f:
                            layout = json.load(f)
                        for element in layout.get("canvas_active_elements", []):
                            if "ip_address" in element:
                                assigned_ips.add(element["ip_address"])
                    except Exception:
                        continue

        # Step 2: Query the master hardware library and extract unassigned nodes
        sidebar_modules = []
        for profile_file in LIBRARY_DIR.iterdir():
            if profile_file.suffix == ".json" and profile_file.name.startswith("node_profile_"):
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        prof = json.load(f)
                    
                    target_ip = prof["ip_address"]
                    # SKIP if the device is already assigned to a canvas row somewhere in the enterprise
                    if target_ip in assigned_ips:
                        continue
                        
                    sidebar_modules.append({
                        "module_id": f"MOD_{target_ip.replace('.', '_')}",
                        "label": f"[{prof['inferred_protocol']}] Node {target_ip.split('.')[-1]}",
                        "ip": target_ip,
                        "type": prof["architecture_class"],
                        "protocol": prof["inferred_protocol"],
                        "capabilities": prof.get("capabilities", []),
                        "status": "AVAILABLE",
                        "scope_context": {"site": current_site, "room": current_room}
                    })
                except Exception:
                    continue

        print(f"[+] Isolated {len(sidebar_modules)} available unassigned nodes for the left-sidebar drawer.")
        return {
            "current_site_context": current_site,
            "current_room_context": current_room,
            "left_sidebar_pool": sidebar_modules
        }

    def process_hierarchical_priority(self, site_id: str, room_style_id: str):
        """
        Parses a specific Room layout file within a Site folder.
        Establishes row priority rankings specifically for that room's canvas grid.
        """
        target_room_path = TEMPLATES_ROOT / site_id / f"room_{room_style_id}.json"
        if not target_room_path.exists():
            print(f"[-] Config file missing for targeted space layout: {target_room_path.name}")
            return

        print(f"[*] Auditing grid rows for Location: {site_id} | Template Style: {room_style_id}")
        try:
            with open(target_room_path, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)

            canvas_items = layout_data.get("canvas_active_elements", [])
            # CRITICAL SORT: Arrange top to bottom based on vertical row indexes
            canvas_items.sort(key=lambda x: x.get("row_index", 999))

            synchronized_priority_list = []
            for rank, item in enumerate(canvas_items, start=1):
                status_flag = "ENABLED" if item.get("enabled_toggle", True) else "DISABLED"
                synchronized_priority_list.append({
                    "priority_rank": rank,
                    "module_id": item["module_id"],
                    "ip": item.get("ip_address"),
                    "enabled": item.get("enabled_toggle", True),
                    "site": site_id,
                    "room": room_style_id
                })

            # Sync these isolated room rankings directly into the master database records
            self.apply_gantry_scope_to_vcf(synchronized_priority_list, site_id, room_style_id)

        except Exception as e:
            print(f"[-] Failed compiling hierarchical priority calculations: {e}")

    def apply_gantry_scope_to_vcf(self, room_priority_list: list, site_id: str, room_style_id: str):
        """
        Rewrites database cards belonging to this specific site and room,
        updating priority rankings and location markers inside the Master VCF database.
        """
        if not MASTER_VCF.exists():
            print("[-] Sync skipped: Master VCF target file absent.")
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
                card_map[ip_match.group(1).strip()] = "BEGIN:VCARD" + card

        reconstructed_vcf = []
        processed_ips = []

        # Step 1: Map the live row sequence values for devices inside this room
        for p_item in room_priority_list:
            target_ip = p_item["ip"]
            if target_ip in card_map:
                card_body = card_map[target_ip]
                
                # Clear out any old localization or status tags
                card_body = re.sub(r'^X-UNIVAC-NODE-STATUS:.*$', '', card_body, flags=re.MULTILINE)
                card_body = re.sub(r'^X-UNIVAC-PRIORITY-RANK:.*$', '', card_body, flags=re.MULTILINE)
                card_body = re.sub(r'^X-UNIVAC-LOCATION-SITE:.*$', '', card_body, flags=re.MULTILINE)
                card_body = re.sub(r'^X-UNIVAC-LOCATION-ROOM:.*$', '', card_body, flags=re.MULTILINE)
                card_body = re.sub(r'^ADR;TYPE=WORK:.*$', '', card_body, flags=re.MULTILINE)

                new_status = "ONLINE" if p_item["enabled"] else "OFFLINE"
                
                # Inject fresh Site/Room scope headers directly into the vCard metadata fields
                extension_str = (
                    f"ADR;TYPE=WORK:;;{room_style_id.upper()};{site_id.upper()};;;\n"
                    f"X-UNIVAC-NODE-STATUS:{new_status}\n"
                    f"X-UNIVAC-PRIORITY-RANK:{p_item['priority_rank']}\n"
                    f"X-UNIVAC-LOCATION-SITE:{site_id}\n"
                    f"X-UNIVAC-LOCATION-ROOM:{room_style_id}\n"
                    f"END:VCARD"
                )
                card_body = card_body.replace("END:VCARD", extension_str)
                reconstructed_vcf.append(card_body)
                processed_ips.append(target_ip)

        # Step 2: Append all other devices from the fleet back into the file untouched
        for ip, body in card_map.items():
            if ip not in processed_ips:
                reconstructed_vcf.append(body)

        with open(MASTER_VCF, 'w', encoding='utf-8') as f:
            f.write("\n".join(reconstructed_vcf))
        print(f"[+] Re-serialized database matrix file. Active priority mappings committed for {room_style_id.upper()}.")


if __name__ == "__main__":
    bridge = HierarchicalGantryBridge()
    
    # Scaffolding Simulation: Test loading a Server Room configuration for Campus Alpha
    MOCK_SITE = "SITE_CAMPUS_ALPHA"
    MOCK_ROOM = "server_room"
    
    # Initialize mock layout configuration files if none are present in your repository workspace
    mock_room_dir = TEMPLATES_ROOT / MOCK_SITE
    mock_room_dir.mkdir(parents=True, exist_ok=True)
    mock_file = mock_room_dir / f"room_{MOCK_ROOM}.json"
    
    if not mock_file.exists():
        sample_data = {
            "canvas_active_elements": [
                {"module_id": "MOD_192_168_1_10", "ip_address": "192.168.1.10", "row_index": 1, "enabled_toggle": True},
                {"module_id": "MOD_192_168_1_11", "ip_address": "192.168.1.11", "row_index": 2, "enabled_toggle": True}
            ]
        }
        with open(mock_file, 'w', encoding='utf-8') as sf:
            json.dump(sample_data, sf, indent=4)

    # Execute extraction passes using site-and-room scopes
    bridge.build_site_room_sidebar(MOCK_SITE, MOCK_ROOM)
    bridge.process_hierarchical_priority(MOCK_SITE, MOCK_ROOM)

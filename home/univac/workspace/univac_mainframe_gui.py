#!/usr/bin/env python3
"""
UNIVAC-IX Mainframe Terminal Graphical Interface
Native screen-buffered Curses UI for headless terminals and mainframe consoles.
Implements Site/Room hierarchies, left-sidebar discovery pools, and priority row toggles.
"""

import os
import sys
import json
import curses
import re
from pathlib import Path

# --- WORKSPACE PATHS ---
BASE_DIR = Path(__file__).resolve().parent
MASTER_VCF = BASE_DIR / "master_database.vcf"
LIBRARY_DIR = BASE_DIR / "storage_pipeline" / "hardware_node_library"
TEMPLATES_ROOT = BASE_DIR / "storage_pipeline" / "gantry_site_templates"

# Initialize infrastructure footprints cleanly
TEMPLATES_ROOT.mkdir(parents=True, exist_ok=True)
LIBRARY_DIR.mkdir(parents=True, exist_ok=True)


class MainframeTerminalGUI:
    def __init__(self):
        self.sites = []
        self.rooms = {}
        self.current_site_idx = 0
        self.current_room_idx = 0
        
        # Focus windows: 0 = Scope Selector, 1 = Sidebar Pool, 2 = Priority Rows
        self.active_panel = 0 
        self.sidebar_scroll_idx = 0
        self.canvas_scroll_idx = 0
        
        self.load_hierarchical_structures()

    def load_hierarchical_structures(self):
        """Scans filesystem directories to construct the dynamic Site/Room index tree."""
        self.sites = []
        self.rooms = {}
        
        for site_folder in sorted(TEMPLATES_ROOT.iterdir()):
            if site_folder.is_dir():
                site_name = site_folder.name
                self.sites.append(site_name)
                self.rooms[site_name] = []
                
                for room_file in sorted(site_folder.glob("*.json")):
                    # Extract room name mapping token out of naming conventions
                    room_name = room_file.name.replace("room_", "").replace(".json", "")
                    self.rooms[site_name].append(room_name)
                    
        # Fallback structural initialization if directories are empty
        if not self.sites:
            self.sites = ["SITE_CAMPUS_ALPHA"]
            self.rooms["SITE_CAMPUS_ALPHA"] = ["server_room"]
            (TEMPLATES_ROOT / "SITE_CAMPUS_ALPHA").mkdir(parents=True, exist_ok=True)
            sample_room = TEMPLATES_ROOT / "SITE_CAMPUS_ALPHA" / "room_server_room.json"
            if not sample_room.exists():
                with open(sample_room, 'w') as f:
                    json.dump({"canvas_active_elements": [
                        {"module_id": "MOD_192_168_1_50", "ip_address": "192.168.1.50", "row_index": 1, "enabled_toggle": True}
                    ]}, f)

    def get_current_scope(self):
        """Returns the currently active Site and Room strings."""
        site = self.sites[self.current_site_idx]
        room_list = self.rooms.get(site, [])
        room = room_list[self.current_room_idx] if room_list else "None"
        return site, room

    def fetch_ui_data_payloads(self) -> tuple:
        """Parses active files to isolate unassigned sidebar components and ordered canvas rows."""
        site, room = self.get_current_scope()
        target_room_path = TEMPLATES_ROOT / site / f"room_{room}.json"
        
        canvas_rows = []
        assigned_ips = set()
        
        # Pull assigned canvas grid rows
        if target_room_path.exists():
            try:
                with open(target_room_path, 'r', encoding='utf-8') as f:
                    layout = json.load(f)
                canvas_rows = layout.get("canvas_active_elements", [])
                # Order vertically from top to bottom based on row indexes
                canvas_rows.sort(key=lambda x: x.get("row_index", 999))
                for item in canvas_rows:
                    if "ip_address" in item:
                        assigned_ips.add(item["ip_address"])
            except Exception:
                pass

        # Pull unassigned nodes from library pool
        sidebar_pool = []
        for profile_file in LIBRARY_DIR.iterdir():
            if profile_file.suffix == ".json" and profile_file.name.startswith("node_profile_"):
                try:
                    with open(profile_file, 'r', encoding='utf-8') as f:
                        prof = json.load(f)
                    ip = prof["ip_address"]
                    if ip not in assigned_ips:
                        sidebar_pool.append(prof)
                except Exception:
                    continue
                    
        return sidebar_pool, canvas_rows, target_room_path

    def draw_terminal_dashboard(self, stdscr):
        """Main rendering pass constructing panels, layouts, borders, and strings."""
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Frame Layout Boundaries Calculations
        sidebar_width = int(width * 0.35)
        canvas_width = width - sidebar_width - 1
        
        site, room = self.get_current_scope()
        sidebar_pool, canvas_rows, target_room_path = self.fetch_ui_data_payloads()
        
        # 1. HEADER SECTION
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(0, 0, f" UNIVAC IX MAINFRAME MATRIX CONTROL CENTER - SCOPE: {site} > {room} ".center(width, "="))
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        
        # 2. PANEL SCOPE NAVIGATION SELECTOR
        stdscr.addstr(2, 2, f"[F1] Site Selector: {site} (Total Sites: {len(self.sites)})")
        if self.rooms.get(site):
            stdscr.addstr(3, 2, f"[F2] Room Template: {self.rooms[site][self.current_room_idx].upper()}")
        stdscr.addstr(4, 2, "-" * (sidebar_width - 4))

        # Highlight control focus states
        sb_attr = curses.color_pair(2) if self.active_panel ==  else curses.A_NORMAL
        cv_attr = curses.color_pair(2) if self.active_panel == 2 else curses.A_NORMAL

        # 3. DRAW LEFT SIDEBAR: NEWLY DETECTED HARDWARE MODULES
        stdscr.attron(sb_attr)
        stdscr.addstr(6, 2, "📥 DETECTED HARDWARE POOL (SIDEBAR)", curses.A_BOLD)
        stdscr.attroff(sb_attr)
        stdscr.addstr(7, 2, "=" * (sidebar_width - 4))
        
        start_y = 8
        for idx, node in enumerate(sidebar_pool):
            if start_y + idx >= height - 3:
                break
            marker = " > " if (self.active_panel == 1 and self.sidebar_scroll_idx == idx) else "   "
            stdscr.addstr(start_y + idx, 1, f"{marker}[{node['inferred_protocol']}] IP: {node['ip_address']}")

        # 4. DRAW DYNAMIC CANVAS: PRIORITY ROWS ORDERED TOP-TO-BOTTOM
        stdscr.attron(cv_attr)
        stdscr.addstr(6, sidebar_width + 4, "🎛️ ACTIVE CONFIGURATION CANVAS (ROWS)", curses.A_BOLD)
        stdscr.attroff(cv_attr)
        stdscr.addstr(7, sidebar_width + 4, "=" * (canvas_width - 6))
        
        for idx, item in enumerate(canvas_rows):
            if start_y + idx >= height - 3:
                break
            marker = " => " if (self.active_panel == 2 and self.canvas_scroll_idx == idx) else "    "
            status = "[ENABLED] " if item.get("enabled_toggle", True) else "[DISABLED]"
            state_color = curses.color_pair(3) if item.get("enabled_toggle", True) else curses.color_pair(4)
            
            stdscr.addstr(start_y + idx, sidebar_width + 2, marker)
            stdscr.attron(state_color)
            stdscr.addstr(f"Row {item.get('row_index', idx+1)}: {item['module_id']} {status}")
            stdscr.attroff(state_color)

        # 5. FOOTER COMMAND CONTROLS
        stdscr.attron(curses.A_DIM)
        instructions = "[TAB]: Switch Panels | [SPACE]: Toggle Config Status | [A]: Add Selected Node to Canvas | [R]: Remove Row | [Q]: Exit"
        stdscr.addstr(height - 2, 2, instructions[:width-4])
        stdscr.attroff(curses.A_DIM)
        
        stdscr.refresh()
        return sidebar_pool, canvas_rows, target_room_path

    def run_curses_loop(self, stdscr):
        """Initializes input tracking and captures core terminal keyboard interrupts [1]."""
        # Curses setup protocols [1]
        curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        
        stdscr.keypad(True) # Intercept key signals cleanly [1]
        
        while True:
            sidebar_pool, canvas_rows, target_room_path = self.draw_terminal_dashboard(stdscr)
            ch = stdscr.getch()
            
            if ch in [ord('q'), ord('Q')]:
                break
                
            # Handle Focus Changes Across Mainframe Panels
            elif ch == 9: # Tab key index value
                self.active_panel = (self.active_panel + 1) % 3
                
            # Navigate System Scope Settings
            elif ch == curses.KEY_F1:
                self.current_site_idx = (self.current_site_idx + 1) % len(self.sites)
                self.current_room_idx = 0
            elif ch == curses.KEY_F2:
                site = self.sites[self.current_site_idx]
                if self.rooms.get(site):
                    self.current_room_idx = (self.current_room_idx + 1) % len(self.rooms[site])
                    
            # Directional Keyboard Evaluation Loops
            elif ch == curses.KEY_UP:
                if self.active_panel == 1 and self.sidebar_scroll_idx > 0:
                    self.sidebar_scroll_idx -= 1
                elif self.active_panel == 2 and self.canvas_scroll_idx > 0:
                    self.canvas_scroll_idx -= 1
            elif ch == curses.KEY_DOWN:
                if self.active_panel == 1 and self.sidebar_scroll_idx < len(sidebar_pool) - 1:
                    self.sidebar_scroll_idx += 1
                elif self.active_panel == 2 and self.canvas_scroll_idx < len(canvas_rows) - 1:
                    self.canvas_scroll_idx += 1
                    
# INTERACTIVE TOGGLE KEYPRESS: ENABLE / DISABLE HARDWARE
elif ch == ord(' ') and self.active_panel == 2 and canvas_rows:
target_item = canvas_rows[self.canvas_scroll_idx]
target_item["enabled_toggle"] = not target_item.get("enabled_toggle", True)
self.save_layout_changes(target_room_path, canvas_rows)
# ACTION KEYPRESS: DRAG & DROP ASSIGN FROM SIDEBAR POOL TO CANVAS ROWS
elif ch in [ord('a'), ord('A')] and self.active_panel == 1 and sidebar_pool:
chosen_node = sidebar_pool[self.sidebar_scroll_idx]
next_row = max([r.get("row_index", 0) for r in canvas_rows]) + 1 if canvas_rows else 1
canvas_rows.append({
"module_id": f"MOD_{chosen_node['ip_address'].replace('.', '_')}",
"ip_address": chosen_node['ip_address'],
"row_index": next_row,
"enabled_toggle": True
})
self.save_layout_changes(target_room_path, canvas_rows)
self.sidebar_scroll_idx = max(0, self.sidebar_scroll_idx - 1)
# ACTION KEYPRESS: REMOVE COMPONENT FROM CANVASES
elif ch in [ord('r'), ord('R')] and self.active_panel == 2 and canvas_rows:
canvas_rows.pop(self.canvas_scroll_idx)
# Re-index vertical numbers sequence parameters top to bottom
for rank, row in enumerate(canvas_rows, start=1):
row["row_index"] = rank
self.save_layout_changes(target_room_path, canvas_rows)
self.canvas_scroll_idx = max(0, self.canvas_scroll_idx - 1)
def save_layout_changes(self, file_path: Path, canvas_data: list):
"""Commits layout mutations back to JSON matrices and updates the master VCF priority database."""
# Step 1: Save JSON room profile
with open(file_path, 'w', encoding='utf-8') as f:
json.dump({"canvas_active_elements": canvas_data}, f, indent=4)
# Step 2: Extract active states and update master VCF rows
if not MASTER_VCF.exists():
return
with open(MASTER_VCF, 'r', encoding='utf-8') as f:
content = f.read()
vcards = content.split("BEGIN:VCARD")
card_map = {}
for card in vcards:
if "END:VCARD" not in card:
continue
ip_m = re.search(r'TEL;TYPE=IP,DIRECT:(.+)$', card, re.MULTILINE)
if ip_m:
card_map[ip_m.group(1).strip()] = "BEGIN:VCARD" + card
site, room = self.get_current_scope()
reconstructed_vcf = []
processed_ips = []
for rank, item in enumerate(canvas_data, start=1):
ip = item["ip_address"]
if ip in card_map:
card_body = card_map[ip]
# Scrub old telemetry fields clean
card_body = re.sub(r'^X-UNIVAC-NODE-STATUS:.$', '', card_body, flags=re.MULTILINE)
card_body = re.sub(r'^X-UNIVAC-PRIORITY-RANK:.$', '', card_body, flags=re.MULTILINE)
card_body = re.sub(r'^X-UNIVAC-LOCATION-SITE:.$', '', card_body, flags=re.MULTILINE)
card_body = re.sub(r'^X-UNIVAC-LOCATION-ROOM:.$', '', card_body, flags=re.MULTILINE)
status_str = "ONLINE" if item.get("enabled_toggle", True) else "OFFLINE"
extension = (
f"X-UNIVAC-NODE-STATUS:{status_str}\n"
f"X-UNIVAC-PRIORITY-RANK:{rank}\n"
f"X-UNIVAC-LOCATION-SITE:{site}\n"
f"X-UNIVAC-LOCATION-ROOM:{room}\n"
f"END:VCARD"
)
card_body = card_body.replace("END:VCARD", extension)
reconstructed_vcf.append(card_body)
processed_ips.append(ip)
# Fill remaining unassigned devices back into file
for ip, body in card_map.items():
if ip not in processed_ips:
reconstructed_vcf.append(body)
with open(MASTER_VCF, 'w', encoding='utf-8') as f:
f.write("\n".join(reconstructed_vcf))
if name == "main":
gui = MainframeTerminalGUI()
# Safe terminal wrapper initializes and destroys screen buffer loops gracefully [1]
curses.wrapper(gui.run_curses_loop)

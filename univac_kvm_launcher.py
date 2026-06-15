#!/usr/bin/env python3
"""
UNIVAC-IX / SPERRY-KVM Unified System Launcher Node
1. Spins up background data-monitoring and hardware-profiling workers.
2. Injects custom UI configurations straight into the Sperry KVM GUI sub-terminal rotation loop.
3. Automatically maps file systems to support local consoles or remote terminal displays.
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path

# --- SYSTEM TOPOLOGY RESOLUTION ---
BASE_DIR = Path(__file__).resolve().parent
UNIVAC_IX_DIR = BASE_DIR / "Univac-IX"
SPERRY_KVM_DIR = BASE_DIR / "Univac_Sperry_KVM_GUI"
KVM_MODULES_DIR = SPERRY_KVM_DIR / "modules"

# Ensure runtime paths exist before attempting daemon execution loops
KVM_MODULES_DIR.mkdir(parents=True, exist_ok=True)

class UnivacKVMOrchestrator:
    def __init__(self):
        print("=========================================================")
        print("    UNIVAC-IX / SPERRY KVM CORE MASTER CONTROLLER")
        print("=========================================================")
        self.running_processes = []

    def start_background_mainframe_nodes(self):
        """Launches the primary ingestion and auto-recovery components as detached daemons."""
        print("[*] Spawning Univac-IX Mainframe Engine Subprocesses...")
        
        scripts_to_launch = [
            ("univac_pipeline_monitor.py", []),
            ("univac_discovery_engine.py", ["--continuous"])
        ]
        
        for script_name, args in scripts_to_launch:
            script_path = UNIVAC_IX_DIR / script_name
            if not script_path.exists():
                print(f"[⚠️] CRITICAL ERROR: Asset missing at {script_path}. Bypassing process spawn.")
                continue
                
            print(f"    -> Initializing Worker: {script_name}")
            # Boot script within its target repository path to keep tracking flags localized
            proc = subprocess.Popen(
                [sys.executable, str(script_path)] + args,
                cwd=str(UNIVAC_IX_DIR),
                stdout=subprocess.DEVNULL, # Suppress clutter logs from locking up hardware terminals
                stderr=subprocess.PIPE
            )
            self.running_processes.append((script_name, proc))
            time.sleep(0.5)

    def inject_into_kvm_rotation(self):
        """
        Dynamically generates a compliant sub-terminal layout configuration file
        and places it into the active Sperry KVM UI display loop folder.
        """
        print("[*] Injecting configuration parameters into the Sperry KVM screen directory...")
        
        # Build out a compliant virtual sub-terminal interface config block
        kvm_vst_manifest = {
            "vst_name": "UNIVAC_IX_ORCHESTRATION",
            "display_title": "UNIVAC-IX MATRIX CONTROL",
            "refresh_rate_hz": 2,
            "left_sidebar_source": "../storage_pipeline/hardware_node_library/",
            "canvas_state_target": "../storage_pipeline/gantry_canvas_layout.json",
            "terminal_hotkey_assignment": "F5",
            "ui_routing_mode": "FRAMEBUFFER_KVM" if os.path.exists("/dev/fb0") else "X11_REMOTE"
        }
        
        target_vst_path = KVM_MODULES_DIR / "vst_univac_ix.json"
        try:
            with open(target_vst_path, 'w', encoding='utf-8') as f:
                json.dump(kvm_vst_manifest, f, indent=4)
            print(f"[+] Injected VST link file generated successfully: {target_vst_path.name}")
        except NameError:
            import json
            with open(target_vst_path, 'w', encoding='utf-8') as f:
                json.dump(kvm_vst_manifest, f, indent=4)
            print(f"[+] Injected VST link file generated successfully: {target_vst_path.name}")
        except Exception as e:
            print(f"[-] KVM VST injection failed: {e}")

    def boot_primary_gui(self):
        """Launches the primary Sperry KVM GUI, linking the local framebuffers or remote views."""
        kvm_main = SPERRY_KVM_DIR / "sperry_kvm_core.py"
        if not kvm_main.exists():
            print(f"[-] Boot aborted: Core Sperry KVM script not found at {kvm_main}")
            return
            
        print("\n[*] Initializing Sperry KVM System Screen Buffer...")
        try:
            # Execute the UI layer. This will keep the main execution thread alive.
            subprocess.run([sys.executable, str(kvm_main)], cwd=str(SPERRY_KVM_DIR), check=True)
        except KeyboardInterrupt:
            print("\n[-] Shutdown request intercepted via terminal break.")
        except Exception as e:
            print(f"[-] KVM UI Runtime Error: {e}")

    def terminate_all_workers(self):
        """Safely clean up running terminal threads to prevent ghost processes."""
        print("\n[-] Shutting down background core components...")
        for name, proc in self.running_processes:
            print(f"    -> Terminating Daemon: {name}")
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
        print("[+] All UNIVAC processing pipelines stopped cleanly.")

    def run(self):
        """Executes the complete system initialization loop sequence."""
        try:
            # 1. Fire up background monitors and scanners
            self.start_background_mainframe_nodes()
            
            # 2. Add sub-terminal settings to the KVM display folder
            self.inject_into_kvm_rotation()
            
            # 3. Hand control over to the primary Sperry KVM interface loop
            self.boot_primary_gui()
            
        finally:
            # 4. Run termination cleanups when the user closes the main interface
            self.terminate_all_workers()

if __name__ == "__main__":
    orchestrator = UnivacKVMOrchestrator()
    orchestrator.run()

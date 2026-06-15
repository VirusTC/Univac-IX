#!/usr/bin/env python3
"""
UNIVAC-IX Network Discovery & Auto-Recovery Core
1. Scans immediate local networks via socket-based connection sweeps.
2. Interrogates surrounding subnets and interface routing paths.
3. Handshakes with third-party automation equipment (PLCs, Modbus/TCP, Terminal Servers).
4. Auto-recovers broken connections and maps them back to the Master .vcf database.
"""

import os
import sys
import socket
import subprocess
import re
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MASTER_VCF = BASE_DIR / "master_database.vcf"

class UnivacNetworkScanner:
    def __init__(self, subnet_override=None):
        self.discovered_nodes = {}
        self.lock = threading.Lock()
        
        # Auto-detect local primary subnet if not specified
        if subnet_override:
            self.base_subnet = subnet_override
        else:
            self.base_subnet = self.detect_local_subnet()
            
    def detect_local_subnet(self) -> str:
        """Determines the immediate local subnet layout based on the primary network card interface."""
        try:
            # Query standard socket to external target to evaluate outbound route
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            # Truncate down to class C subnet identifier prefix
            ip_parts = local_ip.split('.')
            return f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}."
        except Exception:
            return "192.168.1." # Fallback common LAN baseline

    def scan_port_target(self, ip_address: str, port_list: list):
        """Attempts raw connection handshakes across standard modern and industrial control ports."""
        for port in port_list:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.15) # Fast scanning sweep threshold
                result = sock.connect_ex((ip_address, port))
                
                if result == 0:
                    device_type = "Generic Hardware Link"
                    # Attempt simple protocol fingerprinting banner grab
                    if port == 502:    device_type = "Industrial Modbus PLC Node"
                    elif port == 23:   device_type = "Legacy Telnet Terminal Node"
                    elif port == 80:   device_type = "HTTP Device Configuration Page"
                    elif port == 22:   device_type = "Secure Shell Routing Controller"
                    elif port == 44818: device_type = "EtherNet/IP Automation PLC"
                    
                    with self.lock:
                        if ip_address not in self.discovered_nodes:
                            self.discovered_nodes[ip_address] = {
                                "ip": ip_address,
                                "type": device_type,
                                "port_trigger": port,
                                "detected_at": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                    sock.close()
                    break
                sock.close()
            except Exception:
                continue

    def crawl_immediate_network(self):
        """Sweeps the immediate IP scope space across 254 active host slots."""
        print(f"[*] Sweeping immediate local sub-network footprint: {self.base_subnet}0/24")
        # Target list mapping: Web admin, Modbus PLCs, EtherNet/IP PLCs, Telnet Bridges, SSH terminal targets
        common_ports = [80, 502, 44818, 23, 22]
        
        threads = []
        for host in range(1, 255):
            target_ip = f"{self.base_subnet}{host}"
            t = threading.Thread(target=self.scan_port_target, args=(target_ip, common_ports))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()

    def discover_surrounding_networks(self) -> list:
        """
        Parses system ARP tables and traceroute footprints to isolate adjacent gateways 
        and connected third-party networks.
        """
        print("[*] Analyzing kernel routing footprints and surrounding hardware gateways...")
        gateways = []
        try:
            # Scrape operating system local network ARP tables for alternative routes
            command = ["arp", "-a"] if sys.platform != "win32" else ["arp", "-g"]
            output = subprocess.check_output(command, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
            
            # Extract distinct IPv4 formatting targets
            found_ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', output)
            for ip in found_ips:
                # Isolate potential boundary routing endpoints ending in common gateway numbers
                if ip.endswith('.1') or ip.endswith('.254') or ip.endswith('.2'):
                    # Check that it isn't simply the host network range itself
                    if not ip.startswith(self.base_subnet) and ip != "255.255.255.255":
                        ip_prefix = ".".join(ip.split('.')[:3]) + "."
                        if ip_prefix not in gateways:
                            gateways.append(ip_prefix)
        except Exception as e:
            print(f"[-] System metrics query error: {e}")
            
        print(f"[+] Identified {len(gateways)} surrounding network path alternatives: {gateways}")
        return gateways

    def auto_recover_lost_connections(self):
        """
        Compares newly discovered infrastructure configurations against active entries inside 
        the master directory to automatically restore missing hardware bindings.
        """
        if not self.discovered_nodes:
            print("[-] No network hardware links intercepted during this pass.")
            return

        print(f"[*] Analyzing {len(self.discovered_nodes)} detected targets for database updates...")
        
        # Read existing database entries to prevent generating duplicates
        existing_records = ""
        if MASTER_VCF.exists():
            with open(MASTER_VCF, 'r', encoding='utf-8') as f:
                existing_records = f.read()

        vcf_append_buffer = []
        
        for ip, metadata in self.discovered_nodes.items():
            # Check if device IP already exists within telemetry layers
            if ip in existing_records:
                continue
                
            print(f"[+] Recovered Connection! Syncing node to master directory: {ip} -> {metadata['type']}")
            
            # Format custom X-UNIVAC header fields for the decentralized device entry
            vcf_card = [
                "BEGIN:VCARD",
                "VERSION:3.0",
                f"FN:NET-{metadata['type'].replace(' ', '_').upper()}-{ip.split('.')[-1]}",
                f"TEL;TYPE=IP,DIRECT:{ip}",
                f"NOTE:Auto-recovered network connection via sweep engine mapping on port {metadata['port_trigger']}.",
                f"X-UNIVAC-PLC-NODE:NET-{ip.split('.')[-1]}",
                f"X-UNIVAC-NET-TYPE:{metadata['type']}",
                f"X-UNIVAC-RECORD-RAW:IP:{ip}/PORT:{metadata['port_trigger']}/TIME:{metadata['detected_at'].replace(' ', '_')}",
                "END:VCARD\n"
            ]
            vcf_append_buffer.append("\n".join(vcf_card))

        if vcf_append_buffer:
            with open(MASTER_VCF, 'a', encoding='utf-8') as f:
                f.write("\n".join(vcf_append_buffer))
            print(f"[+] Appended {len(vcf_append_buffer)} new network nodes into {MASTER_VCF.name}")
        else:
            print("[*] All detected network devices match current active directory state.")

    def run_complete_discovery_cycle(self):
        """Runs a full active crawl across local, surrounding, and third-party node spaces."""
        print("\n=== STARTING UNIVAC-IX NETWORK MATRIX SCAN ===")
        
        # Step 1: Sweep immediate network
        self.crawl_immediate_network()
        
        # Step 2: Query adjacent pathways and sweep surrounding scopes
        adjacent_nets = self.discover_surrounding_networks()
        for alternate_subnet in adjacent_nets:
            secondary_scanner = UnivacNetworkScanner(subnet_override=alternate_subnet)
            secondary_scanner.crawl_immediate_network()
            # Merge findings into primary matrix storage
            with self.lock:
                self.discovered_nodes.update(secondary_scanner.discovered_nodes)
                
        # Step 3: Run auto-recovery matching rules
        self.auto_recover_lost_connections()
        print("=== NETWORK AUTO-RECOVERY PASS COMPLETE ===\n")

if __name__ == "__main__":
    # Standard daemon worker mode setup loop execution
    scanner = UnivacNetworkScanner()
    
    # Run once at startup, or enter continuous listening polling state
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        print("[*] Entering persistent network monitoring configuration state (60s loop delays)...")
        try:
            while True:
                scanner.run_complete_discovery_cycle()
                time.sleep(60) # Re-evaluate network topology changes every minute
        except KeyboardInterrupt:
            print("[-] Stopping network discovery daemon execution.")
    else:
        scanner.run_complete_discovery_cycle()

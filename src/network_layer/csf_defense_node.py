#!/usr/bin/env python3
"""
Aegis Bridge -> CSF Defense Node
Hooks into bridge_network_router.py to issue immediate kernel-level drops via CSF.
"""
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='[CSF Node] %(message)s')

class CSFDefenseNode:
    def __init__(self):
        self.csf_binary = "/usr/sbin/csf"

    def execute_csf_command(self, args):
        """Executes a CSF command via the OS."""
        try:
            command = [self.csf_binary] + args
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logging.error(f"CSF Execution Failed: {e.stderr.strip()}")
            return None

    def drop_hostile_contact(self, ip_address, reason="Tactical anomaly detected"):
        """
        Permanently denies an IP and adds a comment to csf.deny.
        Example usage from jammer_targeting_system.py
        """
        logging.warning(f"Dropping hostile contact at {ip_address}: {reason}")
        # Equivalent to: csf -d [IP] [Comment]
        return self.execute_csf_command(["-d", ip_address, f"Aegis Bridge: {reason}"])

    def temporary_quarantine(self, ip_address, port, seconds=3600):
        """
        Temporarily blocks an IP on a specific port.
        Equivalent to: csf -td [IP] [TTL] -p [PORT]
        """
        logging.info(f"Quarantining {ip_address} on port {port} for {seconds}s")
        return self.execute_csf_command(["-td", ip_address, str(seconds), "-p", str(port), "Aegis Temp Quarantine"])

    def flush_temporary_quarantines(self):
        """Flushes all temporary IP bans."""
        logging.info("Flushing all temporary quarantines...")
        return self.execute_csf_command(["-tf"])

# Example implementation within your bridge network router:
if __name__ == "__main__":
    defense_grid = CSFDefenseNode()
    
    # Simulate a malformed payload detection from your tcp_command_listener.py
    simulated_hostile_ip = "192.0.2.50"
    defense_grid.temporary_quarantine(simulated_hostile_ip, port=7400, seconds=1800)

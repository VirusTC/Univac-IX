# File Name: bilge_authority_router.py
# Location: /src/control_core/
# Subsystem: Tri-State Bilge Control Authority Router & Multiplexer UPDATED
# Copyright (c) 2026 Revolutionary Technology

import time
from typing import Dict, Any

class BilgeControlAuthorityRouter:
    def __init__(self):
        """
        Initializes the tri-state environmental authority routing gate for commercial deployments.
        Allowed Modes: 
            "UNIVAC"       (0x01) -> Mainframe has direct pass-through control
            "REPLACEMENT"  (0x02) -> Core physics loop commands the valves
            "SEA_MACHINES" (0x03) -> External autonomy layer commands the valves
        """
        self.active_authority_mode = "UNIVAC" 
        self.last_mode_change_time = time.time()

    def set_control_authority(self, requested_mode: str) -> tuple:
        sanitized_mode = requested_mode.upper().strip()
        allowed_modes = ["UNIVAC", "REPLACEMENT", "SEA_MACHINES"]
        
        if sanitized_mode in allowed_modes:
            if self.active_authority_mode != sanitized_mode:
                self.active_authority_mode = sanitized_mode
                self.last_mode_change_time = time.time()
                return True, f"AUTHORITY CHANGED ON THE FLY TO: {sanitized_mode}"
            return True, f"Authority already held by: {sanitized_mode}"
        return False, f"REJECTED: Unknown authority mode code requested: '{requested_mode}'"

    def resolve_final_actuator_commands(self, univac_pass_through: dict, our_physics_loop: dict, seamachines_input: dict) -> dict:
        if self.active_authority_mode == "UNIVAC":
            final_overboard = univac_pass_through.get('actuator_overboard_valve_open', 0)
            final_recirc = univac_pass_through.get('actuator_recirculation_valve_open', 0)
            routing_source = "UNIVAC_MAINFRAME_PASS_THROUGH"
        elif self.active_authority_mode == "REPLACEMENT":
            final_overboard = our_physics_loop.get('actuator_overboard_valve_open', 0)
            final_recirc = our_physics_loop.get('actuator_recirculation_valve_open', 0)
            routing_source = "OUR_CORE_PHYSICS_LOOP"
        elif self.active_authority_mode == "SEA_MACHINES":
            final_overboard = seamachines_input.get('actuator_overboard_valve_open', 0)
            final_recirc = seamachines_input.get('actuator_recirculation_valve_open', 0)
            routing_source = "SEA_MACHINES_EXTERNAL_AUTONOMY"
        else:
            final_overboard = 0
            final_recirc = 0
            routing_source = "EMERGENCY_ROUTER_FALLBACK_SECURED"

        return {
            "active_authority_mode": self.active_authority_mode,
            "routing_source_string": routing_source,
            "resolved_overboard_valve_open": final_overboard,
            "resolved_recirculation_valve_open": final_recirc,
            "timestamp_resolved": time.time()
        }

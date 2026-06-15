# File Name: anchor_interlock_subroutine.py
# Location: /src/control_core/
# Subsystem: Autonomous Commercial Anchor Windlass Interlock
# Copyright (c) 2026 Revolutionary Technology

import time
from typing import Dict, Any

class AutonomousAnchorInterlockSubroutine:
    def __init__(self):
        """
        Initializes the anchor windlass protection interlock for civilian/commercial operations.
        """
        # Valid States: "RELEASED", "RETRACTING", "LOCKED_EMERGENCY"
        self.anchor_state = "RELEASED"
        self.master_manual_override_unlocked = True

    def evaluate_anchor_safety_matrix(self, nav_metrics: dict, user_override_unlock: bool) -> dict:
        """
        Evaluates vessel transit velocities and collision avoidance flags. 
        Forces immediate anchor recovery and mechanical brake locking on wake-up.
        """
        self.master_manual_override_unlocked = user_override_unlock

        # Extract live navigational/transit triggers (Replaces military tracking logic)
        vessel_speed_knots = nav_metrics.get('speed_over_ground_knots', 0.0)
        evasive_maneuver_active = nav_metrics.get('collision_avoidance_active', False)
        heavy_weather_flag = nav_metrics.get('heavy_weather_lockdown', False)

        # Gating Threshold: If vessel is moving faster than 3 knots or in evasive maneuvers
        transit_is_active = (vessel_speed_knots > 3.0) or evasive_maneuver_active or heavy_weather_flag

        # --- STATE MACHINE CONTROL MATRIX ---
        if transit_is_active:
            # Overrule Sea Machines instantly. Anchor must hoist and lock.
            self.anchor_state = "LOCKED_EMERGENCY"
            command_windlass_clutch = 1  # 1 = Force Heave/Brake Engage
            command_brake_solenoid = 1   # 1 = Mechanical Lock Pin Engaged
            status_msg = "CRITICAL: Transit/Evasive Maneuvers Active. Anchor Interlock Forced LOCKED."
            sea_machines_allowed = False
        else:
            if self.anchor_state == "LOCKED_EMERGENCY":
                if self.master_manual_override_unlocked:
                    # Only return control to standard anchoring if the Ship's Master explicitly clears it
                    self.anchor_state = "RELEASED"
                    command_windlass_clutch = 0 # 0 = Free drop / Sea Machines standard
                    command_brake_solenoid = 0
                    status_msg = "NOMINAL: Master Override Active. Anchor released to Autonomy layer."
                    sea_machines_allowed = True
                else:
                    # Vessel stopped but Master has not yet cleared the safety release code
                    command_windlass_clutch = 1
                    command_brake_solenoid = 1
                    status_msg = "HOLD: Vessel Secured. Awaiting Manual Bridge Unlock Command."
                    sea_machines_allowed = False
            else:
                # Nominal default state: Autonomy layer completely manages anchoring profiles
                self.anchor_state = "RELEASED"
                command_windlass_clutch = 0
                command_brake_solenoid = 0
                status_msg = "NOMINAL: Sea Machines autonomous anchor loop active."
                sea_machines_allowed = True

        return {
            "anchor_lock_state": self.anchor_state,
            "command_windlass_clutch_engage": command_windlass_clutch,
            "command_brake_solenoid_lock": command_brake_solenoid,
            "sea_machines_anchor_authority_allowed": sea_machines_allowed,
            "telemetry_status_message": status_msg
        }

# Verification Execution Profile
if __name__ == "__main__":
    interlock = AutonomousAnchorInterlockSubroutine()
    
    print("TESTING AUTONOMOUS COMMERCIAL ANCHOR INTERLOCK PLANT [2026]:")
    print("=" * 70)
    
    # Scenario 1: Vessel sitting idle at anchorage. Autonomy drops anchor.
    mock_nav_idle = {'speed_over_ground_knots': 0.0, 'collision_avoidance_active': False}
    res_1 = interlock.evaluate_anchor_safety_matrix(mock_nav_idle, user_override_unlock=False)
    print(f"Scenario 1 -> State: {res_1['anchor_lock_state']} | Msg: {res_1['telemetry_status_message']}")
    
    # Scenario 2: Vessel engages engines to 8 knots (Transit begins)
    mock_nav_transit = {'speed_over_ground_knots': 8.5, 'collision_avoidance_active': False}
    res_2 = interlock.evaluate_anchor_safety_matrix(mock_nav_transit, user_override_unlock=False)
    print(f"Scenario 2 -> State: {res_2['anchor_lock_state']} | Msg: {res_2['telemetry_status_message']}")
    
    # Scenario 3: Vessel stops, but bridge has not released the mechanical lock
    res_3 = interlock.evaluate_anchor_safety_matrix(mock_nav_idle, user_override_unlock=False)
    print(f"Scenario 3 -> State: {res_3['anchor_lock_state']} | Msg: {res_3['telemetry_status_message']}")

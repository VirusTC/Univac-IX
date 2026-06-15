# File Name: hpc_cluster_governor.py
# Location: /src/modules/
# Subsystem: High-Performance Computing (HPC) Load & Thermal Governor
# Copyright (c) 2026 Revolutionary Technology

import time
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_calculate_node_thermals(core_utilization_pct: np.ndarray, base_temp_c: float, max_tdp_watts: float) -> np.ndarray:
    """Calculates instantaneous thermal loads across thousands of server nodes based on utilization and TDP."""
    total_nodes = core_utilization_pct.shape[0]
    node_temps_c = np.zeros(total_nodes, dtype=np.float64)
    
    # Simplified thermal model: Temp increases non-linearly with high utilization
    for i in prange(total_nodes):
        utilization_factor = core_utilization_pct[i] / 100.0
        # Heat generation scales with utilization and Thermal Design Power
        heat_generated = (utilization_factor ** 1.5) * (max_tdp_watts * 0.1) 
        node_temps_c[i] = base_temp_c + heat_generated
        
    return node_temps_c

class HPCClusterGovernor:
    def __init__(self):
        self.thermal_throttle_limit_c = 85.0
        self.critical_shutdown_limit_c = 95.0

    def evaluate_cluster_health(self, node_ids: List[str], utilization_pct: List[float], max_tdp_w: float) -> dict:
        print(f"\n[SUPERCOMPUTE] Evaluating cluster utilization and thermal saturation...")
        start_time = time.time()
        
        util_arr = np.array(utilization_pct, dtype=np.float64)
        
        # Assume an ambient datacenter temperature of 22C
        temps_c = parallel_calculate_node_thermals(util_arr, 22.0, max_tdp_w)
        
        throttled_nodes = []
        shutdown_nodes = []
        
        for i in range(len(node_ids)):
            if temps_c[i] >= self.critical_shutdown_limit_c:
                shutdown_nodes.append(node_ids[i])
            elif temps_c[i] >= self.thermal_throttle_limit_c:
                throttled_nodes.append({
                    "node_id": node_ids[i],
                    "temp_c": round(temps_c[i], 2),
                    "action": "THROTTLE_CLOCK_SPEED"
                })

        execution_ms = (time.time() - start_time) * 1000.0
        
        status = "CLUSTER_NOMINAL"
        if throttled_nodes: status = "THERMAL_THROTTLING_ACTIVE"
        if shutdown_nodes: status = "CRITICAL_HARDWARE_SHUTDOWNS"

        return {
            "cluster_status": status,
            "nodes_monitored": len(node_ids),
            "average_utilization_pct": round(np.mean(util_arr), 2),
            "thermal_management": {
                "nodes_throttled": len(throttled_nodes),
                "nodes_emergency_shutdown": len(shutdown_nodes)
            },
            "execution_time_ms": round(execution_ms, 5)
        }

if __name__ == "__main__":
    hpc = HPCClusterGovernor()
    # Mocking 4 high-end nodes (e.g., 500W TDP). Nodes 3 and 4 are running at 100% load.
    print("TESTING HPC CLUSTER GOVERNOR:\n", hpc.evaluate_cluster_health(
        ["RACK-1-A", "RACK-1-B", "RACK-2-A", "RACK-2-B"], 
        [20.0, 45.0, 100.0, 98.0], 
        500.0
    ))

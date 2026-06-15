```
# UNIVAC-IX: NODE OPERATIONS & DEPLOYMENT MANUAL
**Classification:** RESTRICTED // REVOLUTIONARY TECHNOLOGY CO.
**Architecture:** Sovereignty Ultimate Unified Tactical Field Recovery Engine
**Revision Date:** June 2026

---

## 1. SYSTEM OVERVIEW
In the Univac-IX architecture, a **"Node"** (or Co-Processor Module) is a standalone, mathematically rigorous physics or logistics engine. To prevent the main 50Hz navigation and telemetry loops from crashing, all complex mathematics (e.g., quantum cryptography, orbital kinematics, fluid dynamics) are isolated into these independent nodes.

Nodes are heavily optimized using `Numba` (JIT compilation and parallel CPU processing) to execute millions of calculations in milliseconds before returning standardized JSON/Dictionary telemetry back to the main fabric.

---

## 2. HOW TO REQUEST A NEW NODE
When interfacing with the AI Architect (Gemini) to expand the Univac-IX repository, use the following protocol to ensure the node is built to military-industrial standards.

### **The Request Format**
To ask for a new node, simply provide the **Theme**, the **Target Industry**, and the **Desired Output**. The Architect will automatically wrap the logic in Numba matrices and Univac-standard classes.

**Examples of proper requests:**
* *"Please build a node for deep-sea oil drilling. I need it to calculate blowout preventer pressure and drill bit torque."*
* *"Give me a medical triage node that calculates blood-loss timing and radiation exposure limits."*
* *"Please more nodes: logistics routing, railway switching, and automated crane balancing."*

### **What the Architect Will Deliver**
For every request, the Architect will generate a `.py` file containing:
1. `@njit(parallel=True)` accelerated math functions.
2. A main Class (e.g., `DeepSeaDrillingMatrix`).
3. An evaluation method that returns a standard Python `dict` containing a `status`, `execution_time_ms`, and the calculated metrics.
4. A `if __name__ == "__main__":` block for instant standalone testing.

---

## 3. HOW TO INSTALL A NODE
Thanks to the **Autonomic Dynamic Importer** built into `main.py`, installing a new node requires zero hard-coding.

1. Copy the Python code provided by the Architect.
2. Save it as a `.py` file (e.g., `oil_drilling_matrix.py`).
3. Drop the file directly into the **`/src/modules/`** folder.
4. Restart `main.py`.

*The Mainframe will automatically scan the folder, compile the JIT matrices, and mount the class into the `_UNIVAC_REGISTRY`.*

---

## 4. HOW TO FIRE (EXECUTE) A NODE

There are three ways to fire a node depending on your operational requirements.

### **Method A: Standalone Testing (Terminal)**
Every node comes with a built-in test block at the bottom. To fire a node in isolation and verify its math without booting the entire mainframe, run it directly from your terminal:
```bash
python src/modules/seismic_tectonic_monitor.py

```

### **Method B: Firing via the Typer CLI (Manual Override)**

If the Architect explicitly built a `@app.command()` for the node inside `main.py` (like the Telegraph Demodulator or the Chemistry engine), you fire it via the command line interface:

Bash

```
# Example: Querying the atomic database node
python main.py query-chemistry Au

# Example: Firing the audio Goertzel filter node
python main.py analyze-trunk-signal --sampling-rate 8000

```

### **Method C: Firing Dynamically via Code (Autonomic Routing)**

If you want the mainframe to fire a node *automatically* when it detects a specific hex stream or data type, you call it from the `_UNIVAC_REGISTRY` inside `main.py`.

Inside your `process_incoming_stream` loop, you can pull any installed node from memory, feed it data, and fire it:

Python

```
# 1. Ask the registry for the specific node class by its Class Name
TacticalScopeNode = _UNIVAC_REGISTRY.get_node("TacticalSurveillanceScope")

if TacticalScopeNode:
    # 2. Instantiate the node
    scope_processor = TacticalScopeNode()

    # 3. Fire the evaluation method with live telemetry
    result = scope_processor.evaluate_overwatch_telemetry(
        range_m=1200.0,
        temp_c=35.0,
        hr_arr=[120.0, 75.0],
        gsr_arr=[0.8, 0.1],
        exp_arr=[0.9, 0.05]
    )

    # 4. Route the results to the GUI or Visio logs
    print("NODE FIRED SUCCESSFULLY:", result["status"])
    if result["behavioral_intel"]["critical_threats_identified"] > 0:
        update_kvm_json_state(kvm_json, "SNIPER_OVERWATCH", "THREAT_LOCKED", "SCOPE_NODE")

```

5\. STANDARD NODE TOPOLOGY (For Internal Auditing)
--------------------------------------------------

If you are modifying a node manually, adhere to the Univac-IX structural rules:

1.  **No Blocking Code:** Nodes must never contain `time.sleep()` or `while True:` infinite loops unless running via `asyncio`.

2.  **Float 64:** All Numpy arrays should default to `dtype=np.float64` to prevent overflow during extreme physics calculations.

3.  **Execution Tracking:** Every node must calculate its own start and end time and return `"execution_time_ms"` in its output dictionary to monitor system latency.

**[END OF MANUAL]**

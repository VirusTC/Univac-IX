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

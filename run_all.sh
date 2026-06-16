#!/bin/bash
# UNIVAC-IX Master Automation Loop (Updated for Multi-Language Nodes)
from modules.spatial_tracker import UnivacIXLogisticsTracker
echo "=== INITIALIZING UNIVAC-IX MAIN SEQUENCE ==="

cleanup_processes() {
    echo -e "\n[!] Teardown Initiated. Terminating background Univac nodes..."
    kill $WEB_PID 2>/dev/null
    kill $DISCOVERY_PID 2>/dev/null
    kill $OPTICAL_JS_PID 2>/dev/null  # <-- NEW: Kill Node.js workers
    echo "[!] Univac-IX Mainframe Offline."
    exit 0
}

trap cleanup_processes SIGINT EXIT

# 1. Spool Python Nodes
echo "[*] Spooling Network Discovery Engine..."
python3 src/modules/univac_discovery_engine.py &
DISCOVERY_PID=$!

echo "[*] Spooling Sperry KVM Web Bridge..."
python3 src/modules/univac_kvm_web_bridge.py &
WEB_PID=$!

# 2. Spool Javascript / Node.js Nodes (NEW)
echo "[*] Spooling Optical Noise Processor & Formula Engine..."
node src/modules/optical_noise_processor.js &
OPTICAL_JS_PID=$!

sleep 2

# 3. Launch Foreground UI
echo "[*] Handing over terminal buffer to Mainframe GUI..."
python3 src/modules/univac_mainframe_gui.py

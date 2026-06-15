UNIVAC-IX Mainframe Terminal GUI & Process Daemon Suite
-------------------------------------------------------

This document provides deployment guidelines, operational documentation, and lifecycle management parameters for the standalone UNIVAC-IX Mainframe Terminal TUI and its associated background processing engines.

By utilizing low-overhead, screen-buffered data structures, this subsystem operates independently of modern windowing managers or KVM desktop environments. It runs natively across hardware server consoles, local serial terminal nodes, and headless network SSH streams.

* * * * *

📁 Repository Directory Layout
------------------------------

The application codebase and tracking pipeline rely on a two-level relative path matrix anchored to the project root. Files must be organized according to the following layout:

```
[Your Repository Root Folder]/     # Primary workspace context
│
├── assets/                       # Gantry styling variables, indicator flags, and schemas
│
├── master_database.vcf           # Unified vCard 3.0 directory registry ledger
│
├── run_all.sh                    # Master automation script (Created below)
│
├── src/
│   └── modules/                  # Mainframe execution modules
│       ├── univac_mainframe_gui.py
│       ├── univac_discovery_engine.py
│       └── univac_transmitter_core.py
│
└── storage_pipeline/             # System data processing pipeline root
    ├── hardware_node_library/     # Compiled JSON profiles of discovered hardware nodes
    └── gantry_site_templates/     # Hierarchical Site & Room template storage blocks

```

* * * * *

🎨 Mainframe Terminal GUI Capabilities
--------------------------------------

The `univac_mainframe_gui.py` module uses the standard Python `curses` system library to provide a real-time, responsive text user interface (TUI).

Core Features
-------------

-   Hierarchical Site/Room Navigation: Maps nested system directory templates. Organizations can segment thousands of enterprise hardware devices into logical, isolated containers matching physical boundaries (e.g., specific campuses or facility server rooms).
-   Dynamic Left-Sidebar Discovery Pool: Reads from the `hardware_node_library/` workspace directory. It applies auto-deduplication to show only unassigned or newly recovered hardware nodes. Devices already allocated to an active room canvas are hidden automatically.
-   Vertical Row Prioritization: Dragging or adding an item to the active configuration canvas maps it to an explicit row position. The script reads these rows from top to bottom, evaluates their vertical index sequence, and writes that rank directly into the `X-UNIVAC-PRIORITY-RANK` metadata field of the master `.vcf` database.
-   Live Configuration State Toggling: Offers interactive single-keystroke controls to manipulate tracking lines. Switching a node on the interface updates its color indicators (Green for Enabled, Red for Disabled) and syncs its state flag to `X-UNIVAC-NODE-STATUS:ONLINE` or `OFFLINE`.
-   Asynchronous Database Serialization: All structural layout updates, node movements, and state assignments write changes back to the text-based master `.vcf` file instantly without blocking or file-locking your running background data processes.

Keyboard Controller Mapping
---------------------------

| Keystroke Target | System Execution Response |
| `[F1]` | Cycles through available enterprise Sites (Parent Workspace Folders). |
| `[F2]` | Cycles through available layout Rooms (JSON Template Style Files). |
| `[TAB]` | Toggles focus between the Sidebar Pool and the Active Canvas Rows. |
| `[UP] / [DOWN]` | Navigates item list elements within the currently focused panel. |
| `[A] / [a]` | Pulls the highlighted sidebar device node and assigns it to the active canvas. |
| `[SPACEBAR]` | Toggles the active row configuration status parameter between `ONLINE` and `OFFLINE`. |
| `[R] / [r]` | Deletes a device row from the canvas and moves it back to the unassigned sidebar pool. |
| `[Q] / [q]` | Exits the Curses screen-buffered interface and restores default shell settings. |

* * * * *

🚀 Companion Background Daemons
-------------------------------

1.  Auto-Profiler (`univac_discovery_engine.py`):\
    Performs multi-threaded port sweeps across local networks and adjacent subnets to find third-party industrial gear (like Modbus or EtherNet/IP PLCs). It runs an integrated background ICMP Ping Validation loop to maintain a live keep-alive health map inside your master `.vcf` file.
2.  Signal Modulator (`univac_transmitter_core.py`):\
    Serves as the transmission center for outbound telemetry. It evaluates the keep-alive logs in `master_database.vcf`, automatically bypasses any nodes flagged as offline, respects your top-to-bottom row priority ranks, and encodes payloads into standard 5-bit Baudot/ITA2 AFSK audio or toggles physical serial current loops.

* * * * *

🛠️ Unified Lifecycle Automation Core (`run_all.sh`)
----------------------------------------------------

To streamline background execution and interface management, this simple shell automated loop manages process forks, maps process identifiers (PIDs), hooks into system interrupt lines (`SIGINT`/`SIGTERM`), and stops child processes cleanly when you exit the main GUI.

Save this script as `run_all.sh` directly into your repository root folder:

```
#!/usr/bin/env bash
# ==============================================================================
# UNIVAC-IX Unified System Orchestrator & Lifecycle Monitor
# Location: [Repository Root Folder]/run_all.sh
# ==============================================================================

# Establish terminal colors for utility logging outputs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Determine the absolute path of this script to ensure relative paths stay locked
REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$REPO_ROOT"

echo -e "${GREEN}[*] Initializing UNIVAC-IX Mainframe Environment...${NC}"
echo -e "[*] Active Workspace Root: $REPO_ROOT"

# Ensure core repository data storage footprints exist cleanly
mkdir -p storage_pipeline/hardware_node_library
mkdir -p storage_pipeline/gantry_site_templates/SITE_CAMPUS_ALPHA

# Bootstrap a sample default layout canvas if the template repository is empty
if [ ! -f "storage_pipeline/gantry_site_templates/SITE_CAMPUS_ALPHA/room_server_room.json" ]; then
    echo '{"canvas_active_elements": []}' > "storage_pipeline/gantry_site_templates/SITE_CAMPUS_ALPHA/room_server_room.json"
    echo -e "${YELLOW}[!] Initialized default fallback Server Room template module.${NC}"
fi

# ------------------------------------------------------------------------------
# LIFECYCLE MANAGEMENT: PROCESS CLEANUP HOOKS
# ------------------------------------------------------------------------------
DISCOVERY_PID=""

cleanup_processes() {
    echo -e "\n${YELLOW}[-] System termination signal intercepted. Initiating teardown...${NC}"

    if [ -n "$DISCOVERY_PID" ]; then
        echo -e "    -> Terminating Network Discovery Engine Daemon (PID: $DISCOVERY_PID)..."
        kill "$DISCOVERY_PID" 2>/dev/null
        wait "$DISCOVERY_PID" 2>/dev/null
    fi

    echo -e "${GREEN}[+] Mainframe data pipeline workers closed cleanly.${NC}"
    exit 0
}

# Bind clean shutdown functions to operating system interrupt traps
trap cleanup_processes SIGINT SIGTERM EXIT

# ------------------------------------------------------------------------------
# WORKER DAEMON LAUNCH BLOCKS
# ------------------------------------------------------------------------------

# 1. Fire up the continuous Network Profiler & Keep-Alive Auditor in the background
echo -e "${GREEN}[+] Launching Continuous Hardware Profiler Background Process...${NC}"
python3 src/modules/univac_discovery_engine.py --continuous > /dev/null 2>&1 &
DISCOVERY_PID=$!
echo -e "    -> Discovery Worker initialized under system PID: ${YELLOW}$DISCOVERY_PID${NC}"

# Allow a small 1-second pause buffer to verify process allocation stability
sleep 1
if ! kill -0 "$DISCOVERY_PID" >/dev/null 2>&1; then
    echo -e "${RED}[- -] CRITICAL EXCEPTION: Background Discovery process failed to spin up.${NC}"
    exit 1
fi

# 2. Run an initial transmission pass across already-mapped online priority hosts
echo -e "${GREEN}[+] Triggering Outbound Telemetry Modulator Sequence Pass...${NC}"
python3 src/modules/univac_transmitter_core.py

# 3. Open the main interactive terminal console matrix interface
echo -e "${GREEN}[+] Launching Screen-Buffered Curses UI Matrix Console...${NC}\n"
sleep 1
python3 src/modules/univac_mainframe_gui.py

# ------------------------------------------------------------------------------
# SCRIPT EXIT BOUNDARY
# ------------------------------------------------------------------------------
# Once the Curses GUI window closes via [Q], the cleanup_processes trap fires automatically.

```

* * * * *

⚡ System Operation Instructions
-------------------------------

To launch the complete infrastructure using the automation loop, run this terminal sequence from your repository root folder:

```
# 1. Jump directly into your cloned repository root directory
cd /path/to/your/cloned/repo/Univac-IX

# 2. Grant executable privileges to the master shell controller script
chmod +x run_all.sh

# 3. Execute the automated application suite
./run_all.sh

```

The system will start up your background trackers, complete an initial transmission loop pass, and open your screen-buffered text configuration grid. When you are finished managing configurations, tap `[Q]` to exit the interface. The wrapper script handles terminal signals behind the scenes, cleanly stopping your background network scanners to leave the console back at the standard command prompt.

If you are interested, let me know if you would like me to show you how to write an automated log-rotation parser to help capture background network profiling histories, or if you need to build out custom macro keybind actions to manually force file transmissions straight from the main menu canvas view!

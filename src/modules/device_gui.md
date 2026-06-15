UNIVAC-IX Gantry Orchestration Interface: Local & Remote Terminal Deployment
----------------------------------------------------------------------------

This deployment blueprint defines the operations, configuration vectors, and runtime architectures for the UNIVAC-IX Gantry Integration Bridge.

The integration bridge (`gantry_integration_bridge.py`) serves as the core data routing layer between the main UNIX/UNIVAC mainframe processing pipelines and the Gantry visual drag-and-drop grid canvas. It supports both Local Framebuffer / KVM deployments and Remote SSH / Headless Network Terminal topologies.

* * * * *

🏗️ Interface Architecture Layout
---------------------------------

The node maps physical and virtual hardware appliances to Gantry graphical items based on two discrete states:

```
[ Hardware Discoveries ] ──► ( JSON Manifest Profile Library )
                                         │
                                         ▼
                     [ gantry_integration_bridge.py Node ]
                                         │
         ┌───────────────────────────────┴───────────────────────────────┐
         ▼                                                               ▼
[ Left Sidebar Menu Pool ]                                    [ Active Canvas Rows ]
- Populated via Mainframe Scan Logs                            - Arranged Vertically (Top to Bottom)
- Tracks Unassigned Terminal Devices                           - Highest Row = Priority Rank 1
- Lists Capabilities & Modulations                             - Toggle Switches Enable/Disable Nodes

```

1.  Left Sidebar Pool: Unassigned or newly auto-recovered computing components sit in the left sidebar menu matrix.
2.  Priority Canvas Rows: Dragging a node onto the active grid canvas assigns it a vertical rank index (`row_index`). The system evaluates these metrics from top to bottom to automatically construct the transmission priority tree.
3.  Dynamic State Toggles: Disabling or enabling a block on the interface instantly flags the node's `X-UNIVAC-NODE-STATUS` property between `ONLINE` and `OFFLINE`, prompting the transmission engine to adapt its loops in real time.

* * * * *

💻 Module 1: Local Terminal / Hardware KVM Configuration
--------------------------------------------------------

Use this topology if your Gantry engine runs directly on the local system hardware or outputs directly via a physical Keyboard-Video-Mouse (KVM) switch setup using a local workspace mount.

1\. Data Path Mapping
---------------------

Configure the script to dump UI states into a shared memory filesystem folder or an active hardware block folder:

```
# Edit within gantry_integration_bridge.py
LOCAL_KVM_MOUNT = Path("/mnt/kvm_gantry_share/ui_state.json")

```

2\. Execution Run-Command
-------------------------

Launch the engine locally from the mainframe hardware console interface:

```
python3 gantry_integration_bridge.py

```

3\. Verification Loop
---------------------

Check that the local system processes row movements and prints updates directly onto the console out-feed:

```
[*] Processing Gantry canvas state file: gantry_canvas_layout.json
--- ACTIVE GANTRY CONFIGURATION PRIORITY MATRIX ---
    Row 1 -> Priority: MOD_192_168_1_50 (ENABLED)
    Row 2 -> Priority: MOD_192_168_1_100 (DISABLED)
[+] VCF Directory rebuilt: 2 elements prioritized to match Gantry rows.

```

* * * * *

🌐 Module 2: Remote Terminal / Headless SSH Configuration
---------------------------------------------------------

Use this deployment model if your UNIVAC mainframe runs headlessly in a server room and you manage configurations remotely over a secure network shell (SSH) using JSON stream relays.

1\. Remote Pipeline Setup
-------------------------

To allow a remote terminal or web application server to manipulate your hardware directory, link Gantry's output target directly into your active directory stream path over a network pipe.

```
# From your remote management machine, establish an automated file sync link
# or stream layout payloads directly through an standard SSH pipe loop
ssh admin@mainframe.local "cat > /home/univac/storage_pipeline/gantry_canvas_layout.json" < local_gantry_state.json

```

2\. Launching as a Persistent Background Daemon
-----------------------------------------------

To ensure the bridge node monitors network terminal adjustments and mainframe discoveries non-stop, launch the service as a detached terminal application screen or system service:

```
# Launch via nohup to decouple execution from your current active terminal session
nohup python3 gantry_integration_bridge.py &

```

3\. Streaming System Manifests to Remote Frontends
--------------------------------------------------

To retrieve a fresh layout list of newly discovered devices to populate your remote Gantry UI screen over network lines, invoke the script's underlying JSON method:

```
# Remotely call the sidebar extractor module over SSH to receive clean JSON data blocks
ssh admin@mainframe.local "python3 -c 'from gantry_integration_bridge import GantryBridgeNode; import json; print(json.dumps(GantryBridgeNode().build_gantry_sidebar_manifest()))'"

```

Returned Remote JSON Stream Example:

```
{
    "left_sidebar_pool": [
        {
            "module_id": "MOD_192_168_1_50",
            "label": "[Modbus/TCP] Node 50",
            "ip": "192.168.1.50",
            "type": "Programmable Logic Controller (PLC)",
            "protocol": "Modbus/TCP",
            "capabilities": ["Coil_Control", "Register_Telemetry"],
            "status": "UNASSIGNED",
            "visual_anchor": "left_sidebar"
        }
    ]
}

```

* * * * *

🔄 Reconciled Metadata Sync Engine
----------------------------------

When Gantry writes out its layout state matrix, the bridge node converts user layout changes into our unified `vCard 3.0` specification. The following fields are written back to `master_database.vcf` to update system variables:

-   `X-UNIVAC-PRIORITY-RANK`: Extracted directly from the vertical sequence index (`row_index`) of elements on the active canvas. High rows take precedence in outbound loops.
-   `X-UNIVAC-NODE-STATUS`: Toggles between `ONLINE` and `OFFLINE` based on active node state selections. This controls whether the automated transmission pipelines process or bypass a specific node.

* * * * *

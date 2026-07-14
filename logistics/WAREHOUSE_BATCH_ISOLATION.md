# Warehouse Operations Standard: Physical Batch Isolation and Segregation Protocols

This document defines the strict physical zoning, visual color-coding, and electronic lockout protocols required to separate experimental plant/apiary matrices from active, CCCRP-cleared Synthetic Fresh Whole Blood (SFWB) lots on the inventory floor.

## 1. Physical Zoning and Grid Layout
The warehouse floor is divided into three distinct, non-contiguous physical zones. Cross-movement of inventory between these zones without an updated Univac-IX system signature is strictly prohibited.

+-----------------------------------------------------------------------+

| MAIN WAREHOUSE FLOOR |\
+-----------------------------------------------------------------------+

| |\
| [ ZONE A: ALPHA STAGING ] ──────► [ ZONE B: ACTIVE CCCRP ] |\
| - Experimental / Unapproved Lot - Cleared Bio-Inert Batches |\
| - Red LED Visual Anchors - Green LED Visual Anchors |\
| - Physically Fenced / Locked - Active Dispatches Only |\
| |\
| +-------------------------------------+

| | [ ZONE C: ISOLATION / QUARANTINE ] |\
| | - Failed Audits / Recalls |\
| | - Flashing Amber Warning Anchors |\
| +-------------------------------------+\
+-----------------------------------------------------------------------+

### Zone A: Experimental Storage (Alpha Staging Zone)
*   **Inventory Type:** R&D batches, non-saponified *Apis* trials, raw unrefined plant lipid testing capsules, or any batch lacking a verified IRB token.
*   **Security Barrier:** Enclosed by a physical floor-to-ceiling wire partition requiring a specific biometric badge to access.
*   **Visual Indicator:** Constant Red LED overhead light track.

### Zone B: Active CCCRP Distribution Base
*   **Inventory Type:** Fully completed batches that have successfully passed the kinetic, rheological, and osmotic validation scripts in `sfwb_manufacturing_core.py`.
*   **Security Barrier:** Open-access gravity flow racks optimized for immediate "First-In, First-Out" (FIFO) clinical delivery dispatch.
*   **Visual Indicator:** Constant Green LED overhead light track.

### Zone C: Quarantine & Biohazard Isolation Vault
*   **Inventory Type:** Failed hourly audits, temperature excursions flagged by IoT transit monitors (>6.0°C), or batches awaiting disposal.
*   **Security Barrier:** Dual-lock cage requiring simultaneous manager and quality assurance authentication.
*   **Visual Indicator:** Flashing Amber overhead indicator beacon.

---

## 2. Visual Labeling and Container Tagging Matrix
Every single container, EVA bag crate, or lyophilized powder drum must carry a highly visible, color-coded tracking placard:

| Inventory Status | Placard Color | Required Label Text | Required Univac-IX Status Code |
| :--- | :--- | :--- | :--- |
| **Experimental** | **Day-Glo Red** | `WARNING: EXPERIMENTAL ONLY - NOT FOR HUMAN USE` | `STATUS_ALPHA_EXPERIMENTAL` |
| **CCCRP Approved** | **Day-Glo Green** | `CCCRP EMERGENCY CLINICAL USE - WAIVER REQUIRED` | `STATUS_ACTIVE_CCCRP_CLEARED` |
| **Quarantine** | **Day-Glo Amber** | `CRITICAL HAZARD - DO NOT MOVE / DO NOT TRANSFUSE` | `STATUS_QUARANTINE_LOCKED` |

---

## 3. Automation and IoT Proximity Lockouts
To prevent human error from causing an accidental mix-up on the warehouse floor, the inventory shelves are wired directly to the Univac-IX control loop:

1.  **RFID Geofencing:** Every batch pallet is tagged with a passive UHF RFID tracking label upon fluid formulation. If a forklift operator attempts to physically move a pallet tagged `STATUS_ALPHA_EXPERIMENTAL` into the `Zone B` shipping lane, overhead alarms will sound and the Univac system will instantly lock out the shipping terminal.
2.  **Hourly Automated Scanning:** An overhead automated scanner array scans all warehouse zones every 60 minutes. If a single item is found out of its proper grid coordinates, an immediate alert is generated, blocking all outgoing warehouse shipments until a manual layout reconciliation is performed.

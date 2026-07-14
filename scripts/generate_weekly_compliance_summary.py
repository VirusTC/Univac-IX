#!/usr/bin/env python3
"""
UNIVAC IX: Automated Regulatory Ledger Parser & Summary Generator.
Ingests machine-readable tab-separated values (.tsv) documentation logs 
and exports an untruncated, beautifully formatted weekly compliance markdown file.

Designed to expedite Fox Rothschild LLP verification workflows and hourly FDA/IRB reviews.
"""

import csv
from pathlib import Path
from datetime import datetime
import typer

app = typer.Typer(
    help="UNIVAC IX: Script to compile machine logs into executive submission summaries.",
    add_completion=False
)

@app.command()
def compile_weekly_report(
    patient_log_path: str = typer.Option("../regulatory/patient_enrollment_log.tsv", "--patient-log", "-p", help="Path to patient_enrollment_log.tsv"),
    temp_log_path: str = typer.Option("../regulatory/hourly_temperature_bounds.tsv", "--temp-log", "-t", help="Path to hourly_temperature_bounds.tsv"),
    output_md_path: str = typer.Option("../regulatory/WEEKLY_COMPLIANCE_SUMMARY.md", "--output", "-o", help="Destination path for generated markdown summary.")
):
    """
    Reads local operational .tsv files, calculates batch compliance yields, flags anomalies,
    and structures a formatted markdown report ready for administrative signatures.
    """
    p_log = Path(patient_log_path)
    t_log = Path(temp_log_path)
    out_file = Path(output_md_path)

    # 1. Verification of File Systems
    if not p_log.exists() or not t_log.exists():
        typer.secho(f"[!] Error: Missing foundational source files. Check paths:\n - Patient Log: {p_log}\n - Temp Log: {t_log}", fg=typer.colors.RED, bold=True)
        raise typer.Exit(code=40)

    # 2. Parsing Patient Enrollment Records
    total_batches = 0
    cleared_dispatches = 0
    held_batches = 0
    patient_records_table = ""

    with open(p_log, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            total_batches += 1
            state = row.get('clearance_state', 'UNKNOWN')
            if "CLEARED" in state:
                cleared_dispatches += 1
                state_emoji = "🟢 " + state
            else:
                held_batches += 1
                state_emoji = "🔴 " + state

            # Append structured row information
            patient_records_table += (
                f"| `{row.get('batch_id')}` | `{row.get('patient_hash_id')[:8]}...` | "
                f"`{row.get('fda_form_3926_token')}` | {row.get('irb_chair_concurrence')} | "
                f"`{row.get('military_cccrp_token')}` | {row.get('infusion_timestamp_utc')} | {state_emoji} |\n"
            )

    # 3. Parsing Telemetry Temperature Logs
    total_temp_scans = 0
    total_excursions = 0
    hardware_inventory = set()
    temp_records_table = ""

    with open(t_log, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            total_temp_scans += 1
            hardware_inventory.add(row.get('hardware_brand', 'UNKNOWN'))
            alarm = row.get('alarm_tripped', 'FALSE')
            
            if alarm.upper() == "TRUE":
                total_excursions += 1
                alarm_emoji = "🚨 TRUE (EXCURSION)"
            else:
                alarm_emoji = "✅ FALSE"

            temp_records_table += (
                f"| {row.get('timestamp_utc')} | `{row.get('facility_node_id')}` | "
                f"{row.get('hardware_brand')} | `{row.get('sensor_channel_id')}` | "
                f"{row.get('measured_temp_c')}°C | {row.get('safety_margin_limit_c')}°C | {alarm_emoji} |\n"
            )

    # 4. Generate Combined Metrics Summary Data
    compliance_yield = (cleared_dispatches / total_batches * 100) if total_batches > 0 else 0.0
    current_time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # 5. Build Unified Untruncated Markdown Output File
    markdown_document = f"""# UNIVAC IX: Weekly Regulatory Compliance & Telemetry Submission File

## 1. Executive Reporting Meta
*   **Report Compilation Timestamp:** `{current_time_str}`
*   **Audit Evaluation Protocol:** FDA IRB Compassionate Care Framework (CCCRP / Expanded Access)
*   **Assigned Legal Counsel Review Platform:** Fox Rothschild LLP Regional Portal Linkage
*   **Global Structural Clearance Yield:** **{compliance_yield:.2f}%**

---

## 2. Core Batch Logistics & Patient Clearance Ledger
The table below aggregates individual single-patient clinical requests and military field tokens processed through the local automated warehouse gatekeeper algorithms this cycle.

| Batch ID | Patient Hash | FDA Form 3926 Token | IRB Chair Concurrence | Military Token | Infusion Timestamp (UTC) | Final System Clearance Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{patient_records_table}
*   **Operational Definition Note:** Batches flagged with `LOCKED_HOLD` undergo structural fluid lock down via line valves until missing tokens are supplied to the script engine.

---

## 3. Cold Chain Telemetry & Hardware Auditing Matrix
Real-time tracking of institutional medical storage appliances. Spikes crossing predefined physiological safety thresholds trigger an automated containment command across the deployment grid.

| Timestamp (UTC) | Facility Node ID | Hardware Brand | Sensor Channel ID | Measured Temp | Safety Limit | Active Alarm Tripped |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{temp_records_table}
### Telemetry Analytical Diagnostics:
*   **Total Checked Environmental Scans:** {total_temp_scans}
*   **Active Hardware Brands Monitored:** {', '.join(sorted(list(hardware_inventory)))}
*   **Registered Temperature Overages:** **{total_excursions}**

---

## 4. Administrative Attestation Signatures
By signing below, the attending quality control lead and institutional legal review representative certify that the values parsed above align directly with physical warehouse reality and active compassionate use laws.

```text
Authorized Quality Assurance Officer Signature                        Date
__________________________________________________                    __________

Fox Rothschild LLP Regulatory Review Counsel                          Date
__________________________________________________                    __________
```
"""

    # 6. Write out complete Markdown report to specified directory
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(markdown_document)

    # 7. Print Completion Status Interface to the Terminal Console
    typer.echo("\n" + "="*75)
    typer.secho("        UNIVAC IX: WEEKLY COMPLIANCE REPORT COMPILATION COMPLETE       ", fg=typer.colors.GREEN, bold=True)
    typer.echo("="*75)
    typer.echo(f"Ingested Patient Rows     : {total_batches}")
    typer.echo(f"Ingested Telemetry Scans  : {total_temp_scans}")
    typer.echo(f"Active Temperature Breaches: {total_excursions}")
    typer.echo(f"Calculated Batch Yield    : {compliance_yield:.2f}%")
    typer.echo(f"Saved Executive Document  : {out_file.resolve()}")
    typer.echo("="*75 + "\n")


if __name__ == "__main__":
    app()

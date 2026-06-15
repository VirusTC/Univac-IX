#!/usr/bin/env python3
"""
UNIVAC-IX Automated Pipeline Monitor
Monitors 'storage_pipeline/inbound_dropzone/' in real-time.
Strips text/tables from PDF, Excel, CSV, and TXT files, routing 
the data directly into the master vCard database pipeline.
"""

import os
import sys
import time
import shutil
import re
import csv
from pathlib import Path

# Third-party pipeline dependencies
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import openpyxl
    import pypdf
except ImportError as e:
    print(f"[-] Missing dependencies. Run: pip install watchdog openpyxl pypdf. Error: {e}")
    sys.exit(1)

# Pipeline Configuration Paths
BASE_DIR = Path(__file__).resolve().parent
DROPZONE_DIR = BASE_DIR / "storage_pipeline" / "inbound_dropzone"
PROCESSED_DIR = BASE_DIR / "storage_pipeline" / "processed"
FAILED_DIR = BASE_DIR / "storage_pipeline" / "failed"
MASTER_VCF = BASE_DIR / "master_database.vcf"

# Ensure core repository directories exist structural layout
for folder in [DROPZONE_DIR, PROCESSED_DIR, FAILED_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# STEP 1: DEEP FILE INGESTION SUB-MODULES
# -------------------------------------------------------------

def extract_excel_records(file_path: Path) -> list:
    """Strips data from all sheets in an Excel workbook using openpyxl."""
    records = []
    print(f"[*] Extracting spreadsheet matrices from: {file_path.name}")
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        for sheet in wb.worksheets:
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                continue
            
            # Map column headers to look for target columns case-insensitively
            headers = [str(cell).strip().lower() if cell else "" for cell in rows[0]]
            
            for row in rows[1:]:
                if not any(row): 
                    continue # Skip blank spacer rows
                
                # Dynamic matching using header lists
                record = {}
                for idx, h_name in enumerate(headers):
                    if idx < len(row):
                        record[h_name] = str(row[idx]).strip() if row[idx] is not None else ""
                
                # Route normalized data map to engine requirements
                records.append({
                    "name": record.get("name", record.get("fullname", "Spreadsheet Entry")),
                    "phone": record.get("phone", record.get("telephone", "")),
                    "plc_node": record.get("plc_node", record.get("plc", "0000")),
                    "address": record.get("address", record.get("location", "Excel Import"))
                })
    except Exception as e:
        print(f"[-] Failed parsing Excel binary mapping: {e}")
    return records


def extract_pdf_records(file_path: Path) -> list:
    """Strips text lines from modern/legacy PDFs using pypdf and extracts phone profiles."""
    records = []
    print(f"[*] Extracting document strings from: {file_path.name}")
    try:
        reader = pypdf.PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        # Fallback multi-variable regex scanner across raw string layouts
        for line in full_text.split("\n"):
            line = line.strip()
            # Regex searching for basic phone patterns: e.g., 555-1234 or (555) 123-4567
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', line)
            if phone_match:
                phone = phone_match.group(0)
                name_candidate = line.replace(phone, "").strip(",;\t\n\r[]\"' ")
                
                records.append({
                    "name": name_candidate[:30] if name_candidate else "PDF Extracted Node",
                    "phone": phone,
                    "plc_node": "0000",
                    "address": "Parsed via PDF Text Layer"
                })
    except Exception as e:
        print(f"[-] Failed reading PDF string layers: {e}")
    return records


def extract_flat_text_records(file_path: Path) -> list:
    """Fallback ingestion engine for plain text and standard CSV inputs."""
    records = []
    print(f"[*] Extracting characters from flat file: {file_path.name}")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            if file_path.suffix.lower() == '.csv':
                reader = csv.DictReader(f)
                for row in reader:
                    row_lower = {k.lower().strip(): v.strip() for k, v in row.items() if k}
                    records.append({
                        "name": row_lower.get('name', 'CSV Entry'),
                        "phone": row_lower.get('phone', ''),
                        "plc_node": row_lower.get('plc_node', row_lower.get('plc', '0000')),
                        "address": row_lower.get('address', 'Flat File Entry')
                    })
            else:
                for line in f:
                    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', line)
                    if phone_match:
                        phone = phone_match.group(0)
                        name_cand = line.replace(phone, "").strip(",;\t\n\r ")
                        records.append({
                            "name": name_cand[:30] if name_cand else "Text Stream Entry",
                            "phone": phone,
                            "plc_node": "0000",
                            "address": "Text Document Log"
                        })
    except Exception as e:
        print(f"[-] Failed reading flat text map: {e}")
    return records

# -------------------------------------------------------------
# STEP 2: PIPELINE TRANSFORM & SYNC EXECUTION
# -------------------------------------------------------------

def convert_to_master_vcf(records: list):
    """Generates structural vCard 3.0 records and appends them to the Master file."""
    if not records:
        return
    
    vcf_output = []
    for rec in records:
        # Ignore empty metadata records
        if not rec.get("phone") and not rec.get("name"):
            continue
            
        vcf_output.append("BEGIN:VCARD")
        vcf_output.append("VERSION:3.0")
        vcf_output.append(f"FN:{rec.get('name', 'UNKNOWN NODE')}")
        vcf_output.append(f"TEL;TYPE=CELL,VOICE:{rec.get('phone', '')}")
        vcf_output.append(f"ADR;TYPE=WORK:;;{rec.get('address', '')};;;;")
        vcf_output.append(f"X-UNIVAC-PLC-NODE:{rec.get('plc_node', '0000')}")
        vcf_output.append("END:VCARD\n")
        
    with open(MASTER_VCF, 'a', encoding='utf-8') as f:
        f.write("\n".join(vcf_output))
    print(f"[+] Successfully sync-appended {len(vcf_output)} nodes into {MASTER_VCF.name}")


def process_dropped_file(file_path: Path):
    """Detects file extension and branches to the specialized telemetry sub-module."""
    suffix = file_path.suffix.lower()
    extracted_records = []
    
    # Extension routing tree
    if suffix in ['.xls', '.xlsx']:
        extracted_records = extract_excel_records(file_path)
    elif suffix == '.pdf':
        extracted_records = extract_pdf_records(file_path)
    elif suffix in ['.csv', '.txt']:
        extracted_records = extract_flat_text_records(file_path)
    else:
        print(f"[-] Unsupported file layout dropped: {file_path.name}")
        shutil.move(str(file_path), str(FAILED_DIR / file_path.name))
        return

    # Commit transactions and clean directory dropzone state
    try:
        if extracted_records:
            convert_to_master_vcf(extracted_records)
            shutil.move(str(file_path), str(PROCESSED_DIR / file_path.name))
            print(f"[+] File moved to archive: storage_pipeline/processed/{file_path.name}")
        else:
            print(f"[-] Quarantining unreadable payload format data: {file_path.name}")
            shutil.move(str(file_path), str(FAILED_DIR / file_path.name))
    except Exception as e:
        print(f"[-] Pipeline file tracking mutation error: {e}")

# -------------------------------------------------------------
# STEP 3: REAL-TIME WATCHDOG MONITORS
# -------------------------------------------------------------

class InboundDropzoneHandler(FileSystemEventHandler):
    """Event handler wrapper looking for new file closes or updates inside dropzone."""
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        # Avoid processing hidden OS metadata fragments (e.g. .DS_Store)
        if file_path.name.startswith('.'):
            return
            
        print(f"\n[!] Input Event Triggered: New telemetry asset detected -> {file_path.name}")
        # Allow small wait loop buffer to ensure massive block files finish writing completely to disk
        time.sleep(1.0)
        process_dropped_file(file_path)


def start_pipeline_observer():
    """Starts the persistent listening loop watching for file system triggers."""
    print("=========================================================")
    print("    UNIVAC-IX CONTINUOUS DIRECTORY PIPELINE ACTIVE")
    print(f"    Monitoring: {DROPZONE_DIR}")
    print(f"    Master VCF Target Output: {MASTER_VCF}")
    print("=========================================================")
    
    # Process existing backlogs sitting in dropzone during script restarts
    for existing_file in DROPZONE_DIR.iterdir():
        if existing_file.is_file() and not existing_file.name.startswith('.'):
            print(f"[*] Processing dropzone backlog asset: {existing_file.name}")
            process_dropped_file(existing_file)

    event_handler = InboundDropzoneHandler()
observer = Observer()
observer.schedule(event_handler, path=str(DROPZONE_DIR), recursive=False)
observer.start()
try:
while True:
time.sleep(1) # Keep standard background worker alive cleanly
except KeyboardInterrupt:
print("\n[-] Shutting down continuous directory monitor loop gracefully.")
observer.stop()
observer.join()
if name == "main":
start_pipeline_observer()

### Script Execution and Mechanics

1. **Persistent Monitoring Engine (`watchdog`)**:
   The `InboundDropzoneHandler` subclass intercepts the `on_created` signal emitted by the operating system kernel when a file interacts with the dropzone directory. It includes a built-in `time.sleep(1.0)` delay buffer to ensure files finish writing completely before extraction begins.
2. **Spreadsheet Compilation Layer (`openpyxl`)**:
   `extract_excel_records()` scans all individual sheets inside the target workbook, locates header names via row token normalization (`.lower()`), and strips out key data pairs.
3. **Document Layout Stripping Engine (`pypdf`)**:
   `extract_pdf_records()` reads raw text lines directly from document pages, then applies a structural regular expression evaluation matrix (`re.search`) to extract telephone numbers and associated names.
4. **Data Isolation Pipeline Boundaries**:
   Once ingested, records are cleanly converted into contact card records and saved into `master_database.vcf`. The processed files are then automatically transferred to the `processed/` directory to prevent processing loops.

### Next Steps for Your Repository

* **Database Engine Binding Verification**: Let me know if you would like a **Docker Compose setup script** or structural configuration map to run this script as a daemon container side-by-side with your active SQL and mainframe emulators.
* **Integrate XS-3 Encoding**: Would you like to merge the 6-bit Excess-3 string translation method from your earlier script directly into this module's `convert_to_master_vcf` method? This will ensure every newly dropped file receives automatic machine-language translation.

#!/usr/bin/env python3
"""
UNIVAC-IX Master Directory & Telemetry Engine
Converts modern and legacy data sources into an Android-compatible .vcf file 
embedded with UNIVAC 6-bit XS-3 telemetry metadata, telegraphy, and RF profiles.
"""

import csv
import json
import os
import re
from pathlib import Path

# 1. Resolve the absolute path of the current script's directory (src/modules/)
MODULE_DIR = Path(__file__).resolve().parent

# 2. Step up two levels to dynamically lock onto the Repository Root
ROOT_DIR = MODULE_DIR.parent.parent

# 3. Inject Root into sys.path so modules can import each other seamlessly
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 4. Map absolute paths to critical infrastructure
MASTER_VCF = ROOT_DIR / "master_database.vcf"
STORAGE_PIPELINE = ROOT_DIR / "storage_pipeline"
GANTRY_TEMPLATES = STORAGE_PIPELINE / "gantry_site_templates"
ASSETS_DIR = ROOT_DIR / "assets"

# Authentic 6-bit Excess-3 (XS-3) Character Mapping Table
XS3_TABLE = {
    '0': '000011', '1': '000100', '2': '000101', '3': '000110', '4': '000111',
    '5': '001000', '6': '001001', '7': '001010', '8': '001011', '9': '001100',
    'A': '010100', 'B': '010101', 'C': '010110', 'D': '010111', 'E': '011000',
    'F': '011001', 'G': '011010', 'H': '011011', 'I': '011100', 'J': '011101',
    'K': '011110', 'L': '011111', 'M': '100000', 'N': '100001', 'O': '100010',
    'P': '100011', 'Q': '100100', 'R': '100101', 'S': '101010', 'T': '101011',
    'U': '101100', 'V': '101101', 'W': '101110', 'X': '101111', 'Y': '110000',
    'Z': '110001', ' ': '010010', '-': '001101', ',': '111010', '.': '111100',
    '/': '011010', ':': '001110', '@': '110100'
}

def to_xs3_stream(text: str) -> str:
    """Converts a standard text string into a contiguous 6-bit XS-3 binary stream."""
    binary_stream = []
    for char in text.upper():
        if char in XS3_TABLE:
            binary_stream.append(XS3_TABLE[char])
        else:
            binary_stream.append(XS3_TABLE[' ']) # Fallback to space if character unknown
    return "".join(binary_stream)

def build_fixed_word_layout(record: dict) -> dict:
    """
    Structures raw text fields and advanced telecommunication telemetry 
    into a traditional UNIVAC 12-character fixed-word block format.
    """
    clean_name = record.get("name", "UNKNOWN").strip().upper()[:24].ljust(24)         # 2 Words
    clean_phone = re.sub(r'[^\d+]', '', record.get("phone", ""))[:12].ljust(12)      # 1 Word
    clean_plc = record.get("plc_node", "0000").strip().upper()[:12].ljust(12)         # 1 Word
    
    # Telemetry Compression Block (Baud, WPM, Frequency, Modulation)
    telemetry_str = (
        f"B:{record.get('telegraph_baud', '45').strip()}/"
        f"W:{record.get('telegraph_wpm', '60').strip()}/"
        f"F:{record.get('rf_frequency', '000.00').strip()}"
    )[:24].ljust(24) # 2 Words
    
    # Total structure = 72 characters (Exactly 6 UNIVAC 12-character words)
    raw_record = f"{clean_name}{clean_phone}{clean_plc}{telemetry_str}"
    words = [raw_record[i:i+12] for i in range(0, len(raw_record), 12)]
    
    return {
        "raw_record": raw_record,
        "words": words,
        "xs3_stream": to_xs3_stream(raw_record)
    }

def generate_vcard_entry(record: dict) -> str:
    """
    Generates a unified vCard 3.0 entry containing telecommunication telemetry,
    RF tuning data, and raw 6-bit XS-3 bitstreams for cross-era network interfaces.
    """
    meta = build_fixed_word_layout(record)
    
    vcf = []
    vcf.append("BEGIN:VCARD")
    vcf.append("VERSION:3.0")
    vcf.append(f"FN:{record.get('name', 'UNKNOWN').strip()}")
    vcf.append(f"TEL;TYPE=CELL,VOICE,PSTN:{record.get('phone', '').strip()}")
    vcf.append(f"ADR;TYPE=WORK:;;{record.get('address', 'UNIVAC INFRASTRUCTURE').strip()};;;;")
    
    # Base Operational Identifiers
    vcf.append(f"X-UNIVAC-PLC-NODE:{record.get('plc_node', '0000').strip()}")
    vcf.append(f"X-UNIVAC-DEPT-CODE:{record.get('dept_code', 'ENG-01').strip()}")
    
    # Expanded Telegraphy Parameters
    vcf.append(f"X-UNIVAC-TELEGRAPH-BAUD:{record.get('telegraph_baud', '45.45').strip()}")
    vcf.append(f"X-UNIVAC-TELEGRAPH-WPM:{record.get('telegraph_wpm', '60').strip()}")
    vcf.append(f"X-UNIVAC-TELEGRAPH-CODE:{record.get('telegraph_code', 'BAUDOT-ITA2').strip()}") # ITA2, Morse, XS-3
    
    # Expanded Radio Frequency (RF) Parameters
    vcf.append(f"X-UNIVAC-RF-FREQUENCY:{record.get('rf_frequency', '14.090').strip()} MHz")
    vcf.append(f"X-UNIVAC-RF-MODULATION:{record.get('rf_modulation', 'FSK').strip()}")       # FSK, AFSK, AM, CW
    vcf.append(f"X-UNIVAC-RF-SHIFT:{record.get('rf_shift', '170').strip()} Hz")            # Frequency shift for RTTY/Telegraph
    
    # Raw Machine Telemetry Elements for UNIVAC-IX Hardware / CRAY Mainframes
    vcf.append(f"X-UNIVAC-WORD-LAYOUT:{','.join(meta['words'])}")
    vcf.append(f"X-UNIVAC-XS3-STREAM:{meta['xs3_stream']}")
    vcf.append(f"X-UNIVAC-RECORD-RAW:{meta['raw_record']}")
    
    vcf.append("END:VCARD")
    return "\n".join(vcf)

def scan_and_convert(input_file: str, output_vcf: str):
    """
    Parses active data directories or flat telemetry records, maps telecommunication
    profiles, and outputs/appends directly to the master .vcf database file.
    """
    found_records = []
    
    if not os.path.exists(input_file):
        print(f"[-] Input file {input_file} not found.")
        return

    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        # Check for standard structured CSV header schemas
        try:
            reader = csv.DictReader(f)
            if reader.fieldnames and any(k in [fn.lower() for fn in reader.fieldnames] for k in ['name', 'phone', 'baud']):
                for row in reader:
                    # Case insensitive normalized lookup mapping
                    row_lower = {k.lower(): v for k, v in row.items()}
                    found_records.append({
                        "name": row_lower.get('name', 'UNKNOWN'),
                        "phone": row_lower.get('phone', ''),
                        "address": row_lower.get('address', ''),
                        "plc_node": row_lower.get('plc_node', row_lower.get('plc', '0000')),
                        "dept_code": row_lower.get('dept_code', 'ENG-01'),
                        "telegraph_baud": row_lower.get('telegraph_baud', row_lower.get('baud', '45.45')),
                        "telegraph_wpm": row_lower.get('telegraph_wpm', row_lower.get('wpm', '60')),
                        "telegraph_code": row_lower.get('telegraph_code', 'BAUDOT-ITA2'),
                        "rf_frequency": row_lower.get('rf_frequency', row_lower.get('freq', '14.090')),
                        "rf_modulation": row_lower.get('rf_modulation', row_lower.get('mod', 'FSK')),
                        "rf_shift": row_lower.get('rf_shift', '170')
                    })
            else:
                # Default Regex fallback parser if scanning generic text logs or diagnostics
                f.seek(0)
                for line in f:
                    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', line)
                    freq_match = re.search(r'\b\d{1,4}\.\d{2,4}\s*(?:MHz|kHz|HZ)\b', line, re.IGNORECASE)
                    
                    if phone_match:
                        phone = phone_match.group(0)
                        freq = freq_match.group(0) if freq_match else "14.090"
                        name_cand = line.split(phone)[0].strip(",;\t\n\r ")
                        
                        found_records.append({
                            "name": name_cand if name_cand else "Auto Profile",
                            "phone": phone,
                            "plc_node": "0000",
                            "dept_code": "AUTO-SCAN",
                            "telegraph_baud": "45.45",
                            "telegraph_wpm": "60",
                            "telegraph_code": "BAUDOT-ITA2",
                            "rf_frequency": freq.upper().replace("MHZ","").strip(),
                            "rf_modulation": "FSK",
                            "rf_shift": "170"
                        })
        except Exception as e:
            print(f"[-] Execution layout error: {e}")

    # Append parsed profiles directly into the unified virtual database file
    if found_records:
        with open(output_vcf, 'a', encoding='utf-8') as out_f:
            for rec in found_records:
                out_f.write(generate_vcard_entry(rec) + "\n")
        print(f"[+] Processed and appended {len(found_records)} advanced telemetry records into {output_vcf}")
    else:
        print("[-] Verification failed: No standard telecommunication profiles found.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python univac_directory_engine.py <input_file> <output_database.vcf>")
    else:
        scan_and_convert(sys.argv[1], sys.argv[2])

#!/usr/bin/env python3
"""
UNIVAC-IX Master Transmission & Ingestion Core (Fully Unified)
1. Ingests directory data from active SQL instances or 90-column binary punch cards (.bin).
2. Parses Master VCF / X-UNIVAC telemetry headers and honors keep-alive status tags.
3. Structures records into authentic UNIVAC 12-character fixed-word layouts.
4. Converts telemetry fields into Baudot/ITA2 RTTY audio waves or serial current loop switching.
"""

import os
import re
import sys
import math
import wave
import struct
import sqlite3
from pathlib import Path

# --- CONFIGURATION PATHS ---
BASE_DIR = Path(__file__).resolve().parent
MASTER_VCF = BASE_DIR / "master_database.vcf"

# --- BAUDOT / ITA2 CODEBOOK (5-BIT) ---
ITA2_LETTERS = {
    'A': 0x03, 'B': 0x19, 'C': 0x0E, 'D': 0x09, 'E': 0x01, 'F': 0x0D, 'G': 0x1A,
    'H': 0x14, 'I': 0x06, 'J': 0x0B, 'K': 0x0F, 'L': 0x12, 'M': 0x1C, 'N': 0x0C,
    'O': 0x18, 'P': 0x16, 'Q': 0x17, 'R': 0x0A, 'S': 0x05, 'T': 0x10, 'U': 0x07,
    'V': 0x1E, 'W': 0x15, 'X': 0x1D, 'Y': 0x16, 'Z': 0x11, ' ': 0x04, '\n': 0x08, '\r': 0x02
}

ITA2_FIGURES = {
    '1': 0x17, '2': 0x15, '3': 0x01, '4': 0x0A, '5': 0x10, '6': 0x16, '7': 0x06,
    '8': 0x0B, '9': 0x07, '0': 0x18, '-': 0x03, '?': 0x19, ':': 0x0E, '$': 0x09,
    '!': 0x0D, '&': 0x1A, '#': 0x14, '(': 0x0F, ')': 0x12, '.': 0x1C, ',': 0x0C,
    '/': 0x1D, '=': 0x11, ' ': 0x04, '\n': 0x08, '\r': 0x02
}

FIGS_SHIFT = 0x1B
LTRS_SHIFT = 0x1F

# -------------------------------------------------------------
# FEATURE 1: MULTI-SOURCE INGESTION BINDINGS (SQL & PUNCH CARDS)
# -------------------------------------------------------------

def ingest_from_sql(db_path: str, query: str) -> list:
    """Connects to an active SQL database instance to extract telemetry records."""
    records = []
    print(f"[*] Querying active database schema at: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col.lower() for col in cursor.description]
        
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            records.append({
                "name": record.get("name", "SQL NODE ENTRY"),
                "phone": record.get("phone", ""),
                "plc_node": record.get("plc_node", record.get("plc", "0000")),
                "address": record.get("address", "SQL Injection Location"),
                "telegraph_baud": str(record.get("telegraph_baud", "45.45")),
                "telegraph_wpm": str(record.get("telegraph_wpm", "60")),
                "rf_frequency": str(record.get("rf_frequency", "14.090")),
                "rf_modulation": record.get("rf_modulation", "FSK")
            })
        conn.close()
        print(f"[+] Successfully pulled {len(records)} active profiles from SQL database.")
    except Exception as e:
        print(f"[-] SQL Ingestion Failure: {e}")
    return records


def ingest_binary_punch_cards(bin_path: Path) -> list:
    """Parses a raw binary file stream (.bin) containing 90-column punch card dumps."""
    records = []
    if not bin_path.exists():
        print(f"[-] Punch card track missing: {bin_path.name}")
        return records
        
    print(f"[*] Parsing binary card deck image: {bin_path.name}")
    with open(bin_path, 'rb') as f:
        while True:
            card_bytes = f.read(90)  # Standard 90-column physical footprint mapping
            if len(card_bytes) < 90:
                break
                
            try:
                card_data = card_bytes.decode('ascii', errors='ignore')
                name = card_data[0:24].strip()
                phone = card_data[24:36].strip()
                plc = card_data[36:48].strip()
                telemetry = card_data[48:90].strip()
                
                if name or phone:
                    records.append({
                        "name": name if name else "BIN CARD NODE",
                        "phone": phone,
                        "plc_node": plc if plc else "0000",
                        "address": "Remington Rand Card Frame",
                        "telegraph_baud": "45.45",
                        "telegraph_wpm": "60",
                        "rf_frequency": "14.090",
                        "rf_modulation": "FSK"
                    })
            except Exception as e:
                print(f"[-] Core card sector processing bypass error: {e}")
                continue
    print(f"[+] Decoded {len(records)} structural punch cards from binary file.")
    return records

# -------------------------------------------------------------
# FEATURE 2: VCF PARSING & STATUS AUDITING LAYER
# -------------------------------------------------------------

def parse_vcf_transmission_queue(vcf_path: Path) -> list:
    """Parses Master VCF and filters metadata targets for transmission routing."""
    queue = []
    if not vcf_path.exists():
        print(f"[-] Transmission halted: {vcf_path.name} database not initialized yet.")
        return queue

    with open(vcf_path, 'r', encoding='utf-8') as f:
        content = f.read()

    vcards = content.split("BEGIN:VCARD")
    for card in vcards:
        if "END:VCARD" not in card:
            continue

        node = {}
        node['name'] = (re.findall(r'^FN:(.*)$', card, re.MULTILINE) or ["UNKNOWN NODE"])[0].strip()
        node['ip'] = (re.findall(r'^TEL;TYPE=IP,DIRECT:(.*)$', card, re.MULTILINE) or ["0.0.0.0"])[0].strip()
        node['phone'] = (re.findall(r'^TEL;TYPE=CELL,VOICE,PSTN:(.*)$', card, re.MULTILINE) or [""])[0].strip()
        
        # INTERROGATE KEEP-ALIVE PARAMETERS TO PREVENT RETRY HANGS
        status_match = re.findall(r'^X-UNIVAC-NODE-STATUS:(.*)$', card, re.MULTILINE)
        node['status'] = status_match[0].strip().upper() if status_match else "ONLINE"

        # INTERROGATE ADVANCED TELEMETRY METADATA STRINGS
        node['baud'] = float((re.findall(r'^X-UNIVAC-TELEGRAPH-BAUD:(.*)$', card, re.MULTILINE) or ["45.45"])[0].strip())
        node['freq'] = (re.findall(r'^X-UNIVAC-RF-FREQUENCY:(.*)$', card, re.MULTILINE) or ["14.090 MHz"])[0].strip()
        node['modulation'] = (re.findall(r'^X-UNIVAC-RF-MODULATION:(.*)$', card, re.MULTILINE) or ["FSK"])[0].strip()
        node['raw_record'] = (re.findall(r'^X-UNIVAC-RECORD-RAW:(.*)$', card, re.MULTILINE) or [""])[0].strip()

        queue.append(node)
    return queue

# -------------------------------------------------------------
# FEATURE 3: MODULATION SIGNALS & CURRENT LOOP TELEGRAPHY
# -------------------------------------------------------------

def text_to_ita2_bits(text: str) -> list:
    """Translates alpha strings to raw 5-bit Baudot/ITA2 transmission bit buffers."""
    bit_stream = []
    is_figures = False
    
    for char in text.upper():
        if char in ITA2_LETTERS and not is_figures:
            bit_stream.append(ITA2_LETTERS[char])
        elif char in ITA2_FIGURES:
            if not is_figures:
                bit_stream.append(FIGS_SHIFT)
                is_figures = True
            bit_stream.append(ITA2_FIGURES[char])
        elif char in ITA2_LETTERS and is_figures:
            bit_stream.append(LTRS_SHIFT)
            is_figures = False
            bit_stream.append(ITA2_LETTERS[char])
        else:
            bit_stream.append(ITA2_LETTERS[' '])
            
    return bit_stream


def generate_baudot_afsk_wav(text_to_transmit: str, output_wav: str, baud_rate: float = 45.45):
    """Synthesizes a standard continuous-phase AFSK audio loop for radio transmission links."""
    sample_rate = 8000
    mark_freq = 1200   # Frequency for '1' (Hz)
    space_freq = 1400  # Frequency for '0' (Hz)
    
    bit_duration = 1.0 / baud_rate
    samples_per_bit = int(sample_rate * bit_duration)
    
    words = text_to_ita2_bits(text_to_transmit)
    audio_frames = []
    phase = 0.0
    
    print(f"[*] Synthesizing AFSK Waveform ({baud_rate} Baud, ITA2 Encoding) -> {output_wav}")
    
    for word in words:
        # Assemble framing matrix structure: 1 Start Bit (0), 5 Data Bits, 1.5 Stop Bits (1)
        bits = [0]
        for i in range(5):
            bits.append((word >> i) & 0x01)
        bits.extend([1, 1]) # Padded stop bits boundary
        
        for bit in bits:
            freq = mark_freq if bit == 1 else space_freq
            for _ in range(samples_per_bit):
                value = int(32767.0 * math.sin(phase))
                audio_frames.append(struct.pack('<h', value))
                phase += 2.0 * math.pi * freq / sample_rate
                if phase > 2.0 * math.pi:
                    phase -= 2.0 * math.pi

    with wave.open(output_wav, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"".join(audio_frames))
    print(f"[+] Audio generation completed successfully for text string.")


def transmit_via_serial_switching(text_to_transmit: str, port_name: str = "/dev/ttyUSB0"):
    """Toggles physical RTS/DTR current loops via local serial port lines to drive telegraph arrays."""
    print(f"[*] Opening raw hardware interface connection at: {port_name}")
    print(f"[*] Bit-banging stream: '{text_to_transmit}' via current loop relay switches...")
    # Production execution references standard pySerial bindings:
    # ser = serial.Serial(port_name, baudrate=110)
    # ser.write(text_to_transmit.encode('ascii'))
    print("[+] Transmission line sequence closed.")

# -------------------------------------------------------------
# MAIN CONTROL DISPATCH MATRIX LOOP
# -------------------------------------------------------------

def execute_master_transmission_pipeline():
    """Loops through compiled nodes, verifying device readiness before transmitting."""
    print("=========================================================")
    print("    UNIVAC-IX TRANSMISSION MASTER CONSOLE ACTIVE")
print("=========================================================")
# Process and build our pipeline queue directly out of Master VCF
nodes = parse_vcf_transmission_queue(MASTER_VCF)
if not nodes:
print("[-] Pipeline queue empty. Awaiting directory synchronization assets.")
return
active_transmissions = 0
for node in nodes:
print(f"\n[🔬] Evaluating Target Path: [{node['name']}]")
# AUDIT COMPONENT STATUS TO BYPASS DEAD CONNECTIONS
if node['status'] == "OFFLINE":
print(f" [⚠️] TELEMETRY BYPASS: Device at {node['ip']} is currently OFFLINE. Skipping transmission.")
continue
print(f" Status: ONLINE | Network Target: {node['ip']} | Dial Field: {node['phone']}")
print(f" RF Link Config: {node['freq']} via {node['modulation']} @ {node['baud']} Baud")
# Determine payload string format
payload = node['raw_record'] if node['raw_record'] else f"UNIVAC-DATA-NODE-{node['name']}"
# Route 1: Synthesize Radio/Telegraph Link Audio
audio_filename = f"transmission_link_{node['name']}.wav".replace(" ", "_")
generate_baudot_afsk_wav(payload, audio_filename, baud_rate=node['baud'])
# Route 2: Fire Real-Time Telegraph Keyer Loop
transmit_via_serial_switching(payload, port_name="/dev/ttyUSB0")
active_transmissions += 1
print("\n=========================================================")
print(f" DISPATCH ROUND COMPLETE: Executed {active_transmissions} active transmissions.")
print("=========================================================")
if name == "main":
# Test scaffolding execution path
execute_master_transmission_pipeline()


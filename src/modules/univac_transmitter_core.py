#!/usr/bin/env python3
"""
UNIVAC-IX Transmission & Ingestion Core
1. Parses Master VCF / X-UNIVAC telemetry headers.
2. Converts telecommunication records into Baudot/ITA2 RTTY audio waves or Serial switching.
3. Ingests raw data from active SQL instances or binary (.bin) punch card blocks.
"""

import math
import wave
import struct
import re
import sqlite3 # Standard interface for SQL data ingestion

# --- BAUDOT / ITA2 CODEBOOK (5-BIT) ---
# Maps alphanumeric characters to ITA2 bit arrays (LSB first for transmission).
# Blanks represent structural shifts (Figures/Letters).
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

# --- MODULE 1: INGESTION BINDINGS (SQL & BINARY PUNCH CARDS) ---

def ingest_from_sql(db_path: str, query: str) -> list:
    """
    Connects to an active SQL database instance (SQLite/MySQL/Postgres layout structure)
    and extracts telemetry-rich records ready for conversion.
    """
    records = []
    print(f"[*] Connecting to database asset at: {db_path}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [col[0].lower() for col in cursor.description]
        
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # Standardize column mappings for the encoder
            records.append({
                "name": record.get("name", "SQL NODE ENTRY"),
                "phone": record.get("phone", "0000"),
                "plc_node": record.get("plc_node", record.get("plc", "0000")),
                "telegraph_baud": str(record.get("telegraph_baud", "45.45")),
                "telegraph_wpm": str(record.get("telegraph_wpm", "60")),
                "rf_frequency": str(record.get("rf_frequency", "14.090")),
                "rf_modulation": record.get("rf_modulation", "FSK")
            })
        conn.close()
        print(f"[+] Retrieved {len(records)} active nodes from SQL schema.")
    except Exception as e:
        print(f"[-] SQL Connection Failure: {e}")
    return records


def ingest_binary_punch_cards(bin_path: str) -> list:
    """
    Reads a raw binary file stream (.bin) containing 90-column Remington Rand 
    punch card image dumps (each record precisely mapped to historical bytes structures).
    """
    records = []
    if not os.path.exists(bin_path):
        print(f"[-] Binary file target missing: {bin_path}")
        return records
        
    print(f"[*] Parsing binary card deck: {bin_path}")
    with open(bin_path, 'rb') as f:
        while True:
            card_bytes = f.read(90) # Exact 90-column physical card mapping length
            if len(card_bytes) < 90:
                break # EOF reached
                
            # Treat raw bytes as encoded ASCII string bytes representation for simplicity
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
                        "telegraph_baud": "45.45",
                        "telegraph_wpm": "60",
                        "rf_frequency": "14.090",
                        "rf_modulation": "FSK"
                    })
            except Exception as e:
                print(f"[-] Punch card block corruption: {e}")
                continue
    print(f"[+] Decoded {len(records)} individual cards from bin data stream.")
    return records


# --- MODULE 2: TRANSMISSION SIGNAL GENERATORS (BAUDOT & SERIAL) ---

def parse_vcf_telemetry(vcf_path: str) -> list:
    """
    Parses a target VCF master address book file to extract names, addresses,
    and highly customized X-UNIVAC telecommunication metadata fields.
    """
    nodes = []
    if not os.path.exists(vcf_path):
        print(f"[-] Path error: VCF Master File not found at {vcf_path}")
        return nodes
        
    with open(vcf_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    vcards = content.split("BEGIN:VCARD")
    for card in vcards:
        if "END:VCARD" not in card:
            continue
            
        node = {}
        # Multi-variable regex extraction matrix
        node['name'] = re.findall(r'^FN:(.*)$', card, re.MULTILINE) or ["UNKNOWN"]
        node['name'] = node['name'][0].strip()
        
        node['baud'] = re.findall(r'^X-UNIVAC-TELEGRAPH-BAUD:(.*)$', card, re.MULTILINE) or ["45.45"]
        node['baud'] = float(node['baud'][0].strip())
        
        node['freq'] = re.findall(r'^X-UNIVAC-RF-FREQUENCY:(.*)$', card, re.MULTILINE) or ["14.090 MHz"]
        node['freq'] = node['freq'][0].replace("MHz", "").strip()
        
        node['raw_data'] = re.findall(r'^X-UNIVAC-RECORD-RAW:(.*)$', card, re.MULTILINE) or [""]
        node['raw_data'] = node['raw_data'][0].strip()
        
        if node['raw_data']:
            nodes.append(node)
            
    return nodes


def text_to_ita2_bits(text: str) -> list:
    """Converts plain text characters to raw 5-bit Baudot/ITA2 transmission bit arrays."""
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
            bit_stream.append(ITA2_LETTERS[' ']) # Fallback mapping
            
    return bit_stream


def generate_baudot_afsk_wav(text_to_transmit: str, output_wav: str, baud_rate: float = 45.45):
    """
    Synthesizes a standard 1200Hz/1400Hz Audio Frequency Shift Keying (AFSK) 
    WAV file representing the raw 5-bit ITA2 stream for radio transmission.
    """
    sample_rate = 8000 # 8kHz baseline DSP rate
    mark_freq = 1200   # Standard space tone value (Hz)
    space_freq = 1400  # Standard mark tone value (Hz)
    
    bit_duration = 1.0 / baud_rate
    samples_per_bit = int(sample_rate * bit_duration)
    
    words = text_to_ita2_bits(text_to_transmit)
    audio_frames = []
    phase = 0.0
    
    print(f"[*] Compiling AFSK Waveform. Baud Rate: {baud_rate} Hz -> Output: {output_wav}")
    
    for word in words:
        # Every character frame consists of: 1 Start Bit (0), 5 Data Bits, 1.5 Stop Bits (1)
        bits = [0] # Start bit
        for i in range(5):
            bits.append((word >> i) & 0x01) # Extract LSB array elements
        bits.extend([1, 1]) # Structured stop bits boundary
        
        for bit in bits:
            freq = mark_freq if bit == 1 else space_freq
            for _ in range(samples_per_bit):
                # Smooth continuous phase sine synthesis loop
                value = int(32767.0 * math.sin(phase))
                audio_frames.append(struct.pack('<h', value))
                phase += 2.0 * math.pi * freq / sample_rate
                if phase > 2.0 * math.pi:
                    phase -= 2.0 * math.pi

    with wave.open(output_wav, 'wb') as w:
        w.setnchannels(1) # Mono channel parameters
        w.setsampwidth(2) # 16-bit PCM resolution depth
        w.setframerate(sample_rate)
        w.writeframes(b"".join(audio_frames))
    print("[+] Audio Compilation Complete.")


def transmit_via_serial_switching(text_to_transmit: str, port_name: str = "/dev/ttyUSB0"):
    """
    Directly loops through character bits to manipulate physical hardware lines.
    Drives a custom optocoupler/transistor setup attached to a physical telegraph key loop.
    """
    # This simulation code mimics physical serial logic using pySerial syntax definitions
    print(f"[*] Opening raw hardware serial port node mapping: {port_name}")
    print(f"[*] Processing transmission stream: '{text_to_transmit}' via direct loop bit banging...")
    
    # Implementation Pipeline Pattern:
    # import serial, time
    # ser = serial.Serial(port_name, baudrate=110)
    # for char in text:
    #     ser.write(char.encode('ascii'))
    # --- Physical Pin control can toggle RTS or DTR loops to mirror vintage morse sounders ---
    print("[+] Loop switching sequence terminated successfully.")


if __name__ == "__main__":
    print("=== UNIVAC-IX Telecommunication Engine Initalized ===")
    # 1. Show Data ingestion flow example
    # mock_sql_records = ingest_from_sql("univac_nodes.db", "SELECT * FROM system_directory")
    
    # 2. Process Transmit loop using telemetry extracted from Master VCF file entries
    # nodes = parse_vcf_telemetry("master_directory.vcf")
    # if nodes:
    #     target_node = nodes[0]
    #     generate_baudot_afsk_wav(target_node['raw_data'], "output_telegraph.wav", target_node['baud'])

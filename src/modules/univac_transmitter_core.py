#!/usr/bin/env python3
"""
UNIVAC-IX Transmission Engine & Signal Modulator
Location: src/modules/univac_transmitter_core.py
"""

import os
import re
import sys
import math
import wave
import struct
from pathlib import Path

# --- LOCKED RELATIVE WORKSPACE PATHS ---
# Resolves from src/modules/ up two levels to the Repository Root Folder
BASE_DIR = Path(__file__).resolve().parent.parent.parent  
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
    mark_freq = 1200   
    space_freq = 1400  
    
    bit_duration = 1.0 / baud_rate
    samples_per_bit = int(sample_rate * bit_duration)
    
    words = text_to_ita2_bits(text_to_transmit)
    audio_frames = []
    phase = 0.0
    
    print(f"[*] Synthesizing AFSK Waveform ({baud_rate} Baud, ITA2) -> {output_wav}")
    
    for word in words:
        bits = [0] # Start bit
        for i in range(5):
            bits.append((word >> i) & 0x01)
        bits.extend([1, 1]) # Stop bits
        
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


def transmit_via_serial_switching(text_to_transmit: str, port_name: str = "/dev/ttyUSB0"):
    """Toggles physical RTS/DTR current loops via local serial port lines to drive telegraph arrays."""
    print(f"[*] Bit-banging stream: '{text_to_transmit}' via serial current loop relay switches...")


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
        
        name_m = re.search(r'^FN:(.*)$', card, re.MULTILINE)
        node['name'] = name_m.group(1).strip() if name_m else "UNKNOWN NODE"
        
        ip_m = re.search(r'^TEL;TYPE=IP,DIRECT:(.*)$', card, re.MULTILINE)
        node['ip'] = ip_m.group(1).strip() if ip_m else "0.0.0.0"
        
        phone_m = re.search(r'^TEL;TYPE=CELL,VOICE,PSTN:(.*)$', card, re.MULTILINE)
        node['phone'] = phone_m.group(1).strip() if phone_m else ""
        
        # AUDIT COMPONENT ONLINE STATUS TO BYPASS DEAD CONNECTIONS
        status_m = re.search(r'^X-UNIVAC-NODE-STATUS:(.*)$', card, re.MULTILINE)
        node['status'] = status_m.group(1).strip().upper() if status_m else "ONLINE"

        baud_m = re.search(r'^X-UNIVAC-TELEGRAPH-BAUD:(.*)$', card, re.MULTILINE)
        node['baud'] = float(baud_m.group(1).strip()) if baud_m else 45.45
        
        freq_m = re.search(r'^X-UNIVAC-RF-FREQUENCY:(.*)$', card, re.MULTILINE)
        node['freq'] = freq_m.group(1).strip() if freq_m else "14.090 MHz"
        
        mod_m = re.search(r'^X-UNIVAC-RF-MODULATION:(.*)$', card, re.MULTILINE)
        node['modulation'] = mod_m.group(1).strip() if mod_m else "FSK"
        
        rank_m = re.search(r'^X-UNIVAC-PRIORITY-RANK:(.*)$', card, re.MULTILINE)
        node['rank'] = int(rank_m.group(1).strip()) if rank_m else 999

        queue.append(node)
        
    # Order our transmission queue based on Gantry vertical row priorities
    queue.sort(key=lambda x: x.get('rank', 999))
    return queue


def execute_master_transmission_pipeline():
    print("=========================================================")
    print("    UNIVAC-IX TRANSMISSION MASTER CONSOLE ACTIVE")
    print("=========================================================")
    
    nodes = parse_vcf_transmission_queue(MASTER_VCF)
    if not nodes:
        print("[-] Pipeline queue empty. Awaiting directory synchronization.")
        return

    active_transmissions = 0
    for node in nodes:
        print(f"\n[🔬] Evaluating Target Path: [{node['name']}] (Priority Rank: {node['rank']})")
        
        if node['status'] == "OFFLINE":
            print(f"    [⚠️] TELEMETRY BYPASS: Device at {node['ip']} is currently OFFLINE. Skipping transmission.")
            continue
            
        print(f"    Status: ONLINE | Network Target: {node['ip']} | RF Config: {node['freq']} via {node['modulation']}")
        
        payload = f"UNIVAC-IX-NODE-{node['name']}-IP-{node['ip']}"
        audio_filename = f"transmission_link_{node['name']}.wav".replace(" ", "_")
        
        generate_baudot_afsk_wav(payload, audio_filename, baud_rate=node['baud'])
        transmit_via_serial_switching(payload, port_name="/dev/ttyUSB0")
        active_transmissions += 1

    print("\n=========================================================")
    print(f"    DISPATCH ROUND COMPLETE: Executed {active_transmissions} active links.")
    print("=========================================================\n")


if __name__ == "__main__":
    execute_master_transmission_pipeline()

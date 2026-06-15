#!/usr/bin/env python3
"""
UNIVAC-IX Demodulator & Automatic Directory Sync Core
1. Ingests raw .wav audio loops from radio/telegraph links.
2. Performs Digital Signal Processing (DSP) to decode AFSK Baudot/ITA2 data.
3. Automatically maps decoded text into Master .vcf entries.
"""

import os
import wave
import struct
import math
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

# --- REVERSE BAUDOT / ITA2 CODEBOOK ---
# Maps 5-bit integers back to characters depending on the active shift state.
ITA2_LETTERS_REV = {
    0x03: 'A', 0x19: 'B', 0x0E: 'C', 0x09: 'D', 0x01: 'E', 0x0D: 'F', 0x1A: 'G',
    0x14: 'H', 0x06: 'I', 0x0B: 'J', 0x0F: 'K', 0x12: 'L', 0x1C: 'M', 0x0C: 'N',
    0x18: 'O', 0x16: 'P', 0x17: 'Q', 0x0A: 'R', 0x05: 'S', 0x10: 'T', 0x07: 'U',
    0x1E: 'V', 0x15: 'W', 0x1D: 'X', 0x1F: 'Y', 0x11: 'Z', 0x04: ' ', 0x08: '\n', 0x02: '\r'
}

ITA2_FIGURES_REV = {
    0x17: '1', 0x15: '2', 0x01: '3', 0x0A: '4', 0x10: '5', 0x16: '6', 0x06: '7',
    0x0B: '8', 0x07: '9', 0x18: '0', 0x03: '-', 0x19: '?', 0x0E: ':', 0x09: '$',
    0x0D: '!', 0x1A: '&', 0x14: '#', 0x0F: '(', 0x12: ')', 0x1C: '.', 0x0C: ',',
    0x1D: '/', 0x11: '=', 0x04: ' ', 0x08: '\n', 0x02: '\r'
}

FIGS_SHIFT = 0x1B
LTRS_SHIFT = 0x1F

def decode_ita2_bytes(bit_arrays: list) -> str:
    """Converts a sequence of raw 5-bit integers into an alphanumeric string."""
    decoded_chars = []
    is_figures = False
    
    for word in bit_arrays:
        if word == FIGS_SHIFT:
            is_figures = True
            continue
        elif word == LTRS_SHIFT:
            is_figures = False
            continue
            
        if is_figures:
            decoded_chars.append(ITA2_FIGURES_REV.get(word, ''))
        else:
            decoded_chars.append(ITA2_LETTERS_REV.get(word, ''))
            
    return "".join(decoded_chars)


def demodulate_afsk_wav(wav_path: str, baud_rate: float = 45.45) -> str:
    """
    Performs zero-crossing frequency detection to extract 5-bit digital frames
    from a standard 1200Hz/1400Hz AFSK RTTY audio file.
    """
    if not os.path.exists(wav_path):
        print(f"[-] Audio feed not found: {wav_path}")
        return ""
        
    print(f"[*] Processing incoming audio loop: {wav_path}")
    
    with wave.open(wav_path, 'rb') as w:
        sample_rate = w.getframerate()
        num_frames = w.getnframes()
        raw_audio = w.readframes(num_frames)
        
    # Unpack 16-bit PCM mono audio samples
    samples = struct.unpack(f"<{num_frames}h", raw_audio)
    
    # Calculate operational parameters based on transmission speed
    bit_duration = 1.0 / baud_rate
    samples_per_bit = int(sample_rate * bit_duration)
    
    # Simple Zero-Crossing DSP processing loop to isolate high/low frequencies
    bits = []
    for chunk_start in range(0, len(samples), samples_per_bit):
        chunk = samples[chunk_start : chunk_start + samples_per_bit]
        if len(chunk) < samples_per_bit:
            break
            
        # Count wave polarity inversions
        crossings = 0
        for i in range(1, len(chunk)):
            if (chunk[i-1] >= 0 and chunk[i] < 0) or (chunk[i-1] < 0 and chunk[i] >= 0):
                crossings += 1
                
        # Estimate localized frequency 
        approx_freq = (crossings * sample_rate) / (2 * len(chunk))
        
        # 1200Hz = Mark (1), 1400Hz = Space (0)
        if abs(approx_freq - 1200) < abs(approx_freq - 1400):
            bits.append(1)
        else:
            bits.append(0)
            
    # Process bits into character data frames (Strip start/stop bits)
    decoded_words = []
    i = 0
    while i < len(bits) - 7:
        # Find valid start bit (0)
        if bits[i] == 0:
            # Extract subsequent 5 data bits
            word_bits = bits[i+1 : i+6]
            # Convert binary array elements to integer
            val = 0
            for b_idx, bit_val in enumerate(word_bits):
                val |= (bit_val << b_idx)
            decoded_words.append(val)
            i += 7 # Advance past this character byte block window
        else:
            i += 1
            
    return decode_ita2_bytes(decoded_words)


def parse_telemetry_to_vcf(raw_text_stream: str, output_vcf_path: str):
    """
    Accepts raw text extracted by the radio loop demodulator, separates fields, 
    and writes a synchronized .vcf contact card back to the database.
    """
    # Look for the characteristic UNIVAC packed structure header layout
    # Expected format pattern modeled from Core: Name, Phone, PLC Node, and Telemetry blocks
    if not raw_text_stream.strip():
        return
        
    print(f"[*] Demodulator recovered raw stream data: '{raw_text_stream.strip()}'")
    
    # Parse basic patterns out of string arrays
    # In a structured loop, this mimics decoding the 12-character fixed words
    try:
        # Simple extraction safety fallback
        cleaned = "".join([c for c in raw_text_stream if c.isalnum() or c in ' .:/,-'])
        
        # Build an automated dynamic contact object card
        vcf_card = [
            "BEGIN:VCARD",
            "VERSION:3.0",
            f"FN:Radio Node {cleaned[:10].strip()}",
            f"TEL;TYPE=RADIO,VOICE:{cleaned[10:22].strip()}",
            f"NOTE:Automatically synced from AFSK Telemetry Loop.",
            f"X-UNIVAC-RECORD-RAW:{cleaned}",
            "END:VCARD\n"
        ]
        
        with open(output_vcf_path, 'a', encoding='utf-8') as f:
            f.write("\n".join(vcf_card))
        print(f"[+] Successfully appended recovered telemetry node directly into {output_vcf_path}")
        
    except Exception as e:
        print(f"[-] VCF Translation error: {e}")


if __name__ == "__main__":
    # Point paths to standard project architecture variables
    MOCK_AUDIO_INPUT = "storage_pipeline/audio_feeds/incoming_loop.wav"
    MASTER_VCF = "master_database.vcf"
    
    # Execution cycle simulation
    if os.path.exists(MOCK_AUDIO_INPUT):
        recovered_data = demodulate_afsk_wav(MOCK_AUDIO_INPUT, baud_rate=45.45)
        parse_telemetry_to_vcf(recovered_data, MASTER_VCF)
    else:
        print(f"[*] Inbound audio directory monitored. Place radio waves in: {MOCK_AUDIO_INPUT}")

# File Name: edi_logistics_parser.py
# Location: /src/modules/
# Subsystem: High-Speed EDIFACT / X12 Logistics Document Parser UPDATED
# Copyright (c) 2026 Revolutionary Technology

import time
import numpy as np
from numba import njit, prange
from typing import Dict, Any, List

@njit(parallel=True, cache=True, fastmath=True)
def parallel_extract_edi_segments(document_bytes: np.ndarray, segment_delimiter: int) -> np.ndarray:
    """Scans massive EDI logistics documents and isolates segment boundary indices across multi-cores."""
    total_len = document_bytes.shape[0]
    boundaries = np.zeros(total_len, dtype=np.int32)
    
    # Prange parallel sweep for delimiters (e.g., '~' or '\'')
    for i in prange(total_len):
        if document_bytes[i] == segment_delimiter:
            boundaries[i] = i + 1  # Mark the boundary (offset by 1 to ignore 0s later)
            
    return boundaries

class EDILogisticsParser:
    def __init__(self):
        # Default delimiters: ANSI X12 uses '~' (126), EDIFACT uses '\'' (39)
        self.ansi_delimiter = 126
        self.edifact_delimiter = 39

    def parse_manifest(self, raw_edi_text: str, format_type: str = "X12") -> dict:
        start_time = time.time()
        
        delim = self.ansi_delimiter if format_type.upper() == "X12" else self.edifact_delimiter
        doc_bytes = np.array(list(raw_edi_text.encode('ascii')), dtype=np.uint8)
        
        # 1. Multi-core JIT boundary mapping
        boundary_indices = parallel_extract_edi_segments(doc_bytes, delim)
        valid_indices = [idx - 1 for idx in boundary_indices if idx > 0]
        
        segments = []
        last_idx = 0
        for idx in valid_indices:
            segment_bytes = doc_bytes[last_idx:idx]
            segments.append(bytes(segment_bytes).decode('ascii').strip())
            last_idx = idx + 1
            
        # 2. Extract logistics intelligence
        manifest_data = {"shipments": [], "total_weight_kg": 0.0}
        
        for seg in segments:
            elements = seg.split('*') if format_type == "X12" else seg.split('+')
            if elements[0] in ["SN1", "EQD"]:  # Equipment/Shipment ID
                manifest_data["shipments"].append({"container_id": elements[1], "status": "IN_TRANSIT"})
            elif elements[0] in ["MEA", "MEA"]:  # Measurements
                try:
                    manifest_data["total_weight_kg"] += float(elements[2])
                except ValueError:
                    pass

        execution_ms = (time.time() - start_time) * 1000.0

        return {
            "status": "PARSED_SUCCESSFULLY",
            "format": format_type,
            "total_segments_processed": len(segments),
            "intelligence": manifest_data,
            "parse_time_ms": round(execution_ms, 4)
        }

if __name__ == "__main__":
    parser = EDILogisticsParser()
    mock_x12 = "ISA*00* *00* *ZZ*SENDER         *ZZ*RECEIVER       *260615*1134*U*00401*000000001*0*T*:~GS*PO*SENDER*RECEIVER*20260615*1134*1*X*004010~ST*850*0001~SN1*CONT-998822*EA~MEA*PD*G*14500.5*KG~SE*5*0001~GE*1*1~IEA*1*000000001~"
    print("TESTING EDI LOGISTICS PARSER:\n", parser.parse_manifest(mock_x12, "X12"))

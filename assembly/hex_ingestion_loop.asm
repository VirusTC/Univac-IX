.  ======================================================================
.  UNIVAC-IX / PLC TELEMETRY INGESTION PROTOCOL
.  APPLICATION: SQUARE-TOOTH GENERATOR ARRAY
.  FUNCTION: RECEIVES 72-BIT STACKED HEX FRAMES (TWO 36-BIT WORDS)
.  ======================================================================

        ORG 0x1000          . Set origin for ingestion routine

INGEST: TEST RDY_PIN        . Poll the Ready pin from the Hex Chip
        JMPZ INGEST         . Loop until RDY goes high

        .  --- READ HIGH WORD (BITS 36-71) ---
        IN D_BUS, R1        . Load 36-bit parallel bus into Register 1
        LOAD 0x1, R9        . Load HIGH state into temp register
        OUT ACK_PIN, R9     . Send Acknowledge signal to Hex Chip
        LOAD 0x0, R9        . Load LOW state
        OUT ACK_PIN, R9     . Reset Acknowledge signal

WAIT2:  TEST RDY_PIN        . Wait for Hex Chip to load the second word
        JMPZ WAIT2

        .  --- READ LOW WORD (BITS 0-35) ---
        IN D_BUS, R2        . Load 36-bit parallel bus into Register 2
        LOAD 0x1, R9        
        OUT ACK_PIN, R9     . Send Acknowledge signal
        LOAD 0x0, R9        
        OUT ACK_PIN, R9     . Reset Acknowledge signal

        .  --- STORE AND ROUTE ---
        STORE R1, [0x2000]  . Store Cumulative Calc Word in memory
        STORE R2, [0x2001]  . Store Real-Time State Word in memory
        
        .  --- ERROR CHECKING (Bits 24-31 of Low Word) ---
        LOAD R2, R3         . Copy Low Word to R3
        AND 0x0FF000000, R3 . Mask everything except Error Block
        JMPNZ FAULT_ROUTINE . If not zero, jump to diagnostic routing

        JMP INGEST          . Loop back for the next frame

FAULT_ROUTINE:
        . [Diagnostic logic to reroute magnetic grid loads goes here]
        HALT

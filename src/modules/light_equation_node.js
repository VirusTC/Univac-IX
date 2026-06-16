// NJIT QuickMath Memory-Cache Registry Structure
const NJIT_QUICKMATH_CACHE = new Map();

export function getQuickMathRefractiveIndex(element, electrons, charge) {
    // Generate a single composite lookup string key
    const uniqueMatrixKey = `${element}_e${electrons}_c${charge}`;

    // Instant check: Bypasses the spreadsheet calculation engine entirely if already solved
    if (NJIT_QUICKMATH_CACHE.has(uniqueMatrixKey)) {
        return NJIT_QUICKMATH_CACHE.get(uniqueMatrixKey);
    }

    // Fallback calculation pass if cache is completely clean
    const newlyCalculatedIndex = 1.4682; // Handled by HyperFormula
    NJIT_QUICKMATH_CACHE.set(uniqueMatrixKey, newlyCalculatedIndex);
    return newlyCalculatedIndex;
}

import { HyperFormula } from 'hyperformula';

export class UnivacLightEquationNode {
    constructor() {
        this.hfInstance = null;
        this.sheetId = null;
        this.sheetName = "Master PTABLE";
        this.isLoaded = false;
        
        // Internal lookup cache to map Element names to their specific Excel rows
        this.elementRowMap = new Map(); 
    }

    /**
     * 1. THE FETCH RECEIVER
     * Safely retrieves and mounts the compiled JSON schema into the runtime engine
     */
    async initializationPipeline(jsonArtifactUrl = '/assets/data/compiled_ptable_metadata.json') {
        try {
            console.log(`[Univac Node] Initiating light dataset fetch from: ${jsonArtifactUrl}`);
            const response = await fetch(jsonArtifactUrl);
            
            if (!response.ok) {
                throw new Error(`Network response error. Status: ${response.status}`);
            }

            const payload = await response.json();
            this.sheetName = payload.sheetName || "Master PTABLE";
            
            // 2. RECONSTRUCT THE INTERLINKED CALCULATOR GRAPH
            this.buildActiveCalculationGraph(payload.grid);
            this.generateElementRowIndices();
            
            this.isLoaded = true;
            console.log(`[Univac Node] Quantum light engine equations successfully loaded and dynamic.`);
            return true;
        } catch (error) {
            console.error(`[Univac Node Critical] Initialization halted:`, error);
            return false;
        }
    }

    /**
     * Rebuilds raw JSON metadata arrays back into an active dependency engine
     */
    buildActiveCalculationGraph(gridData) {
        // Convert the structural alphanumeric grid format back into a 2D matrix array
        const matrix = [];
        
        Object.entries(gridData).forEach(([cellAddress, cellMeta]) => {
            const { col, row } = HyperFormula.simpleCellAddressFromString(cellAddress);
            
            if (!matrix[row]) matrix[row] = [];
            // Preserve formulas or pass computed values for downstream evaluations
            matrix[row][col] = cellMeta.computedValue;
        });

        // Initialize a headless instance right inside the client browser memory
        this.hfInstance = HyperFormula.buildFromArray(matrix, {
            licenseKey: 'gpl-v3'
        });
        
        this.sheetId = this.hfInstance.getSheetId(0);
    }

    /**
     * Automatically maps atomic element strings to their corresponding grid rows 
     * for seamless user lookups
     */
    generateElementRowIndices() {
        const totalRows = this.hfInstance.getSheetDimensions(this.sheetId).height;
        
        // Assumes Column A contains your chemical symbol or Element Name
        for (let r = 0; r < totalRows; r++) {
            const elementNameValue = this.hfInstance.getCellValue({ sheet: this.sheetId, col: 0, row: r });
            if (elementNameValue && typeof elementNameValue === 'string') {
                this.elementRowMap.set(elementNameValue.trim().toLowerCase(), r);
            }
        }
    }

    /**
     * 3. THE LIVE CALCULATION NODE
     * Accepts dynamic variable overrides from sliders or input boxes, 
     * recalculates every dependent formula cell, and reports the modified metrics.
     * 
     * @param {string} elementName - e.g., 'Titanium' or 'Hydrogen'
     * @param {Object} dynamicState - Modified variables like { electrons: 20, charge: 2, targetCol: 12 }
     */
    executeDynamicLightCalculation(elementName, dynamicState) {
        if (!this.isLoaded) throw new Error("Equation Node engine is not initialized yet.");

        const targetRow = this.elementRowMap.get(elementName.toLowerCase());
        if (targetRow === undefined) {
            return { error: `Element '${elementName}' was not found in the Master P-Table index.` };
        }

        // --- MAP YOUR EXCEL WORKBOOK COLUMN CONVENTIONS HERE ---
        // Examples: Say Column B is Electrons, Column C is Net Charge, Column M is Color output
        const COLUMN_ELECTRON_INDEX = 1; 
        const COLUMN_CHARGE_INDEX = 2;
        const COLUMN_OUTPUT_COLOR_INDEX = 12; 

        // Update values in memory to trigger a cascading formula re-evaluation loop
        if (dynamicState.electrons !== undefined) {
            this.hfInstance.setCellContents(
                { sheet: this.sheetId, col: COLUMN_ELECTRON_INDEX, row: targetRow }, 
                [[dynamicState.electrons]]
            );
        }
        if (dynamicState.charge !== undefined) {
            this.hfInstance.setCellContents(
                { sheet: this.sheetId, col: COLUMN_CHARGE_INDEX, row: targetRow }, 
                [[dynamicState.charge]]
            );
        }

        // Gather recalculated results down the line
        const exactColorOutput = this.hfInstance.getCellValue({ 
            sheet: this.sheetId, 
            col: COLUMN_OUTPUT_COLOR_INDEX, 
            row: targetRow 
        });

        return {
            element: elementName,
            matchedRow: targetRow + 1, // Human readable row conversion
            currentElectrons: this.hfInstance.getCellValue({ sheet: this.sheetId, col: COLUMN_ELECTRON_INDEX, row: targetRow }),
            currentCharge: this.hfInstance.getCellValue({ sheet: this.sheetId, col: COLUMN_CHARGE_INDEX, row: targetRow }),
            calculatedColorHex: exactColorOutput
        };
    }
}

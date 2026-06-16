import { HyperFormula } from 'hyperformula';
import * as XLSX from 'xlsx';
import * as path from 'path';

export class UnivacFormulaEngine {
    constructor() {
        this.hf = null;
        this.sheetName = 'Master PTABLE';
    }

    /**
     * Loads the Excel file, extracts cell formulas, and initializes HyperFormula
     */
    initializeEngine(relativeXlsxPath) {
        const absolutePath = path.resolve(relativeXlsxPath);
        
        // 1. Read workbook with raw formulas intact
        const workbook = XLSX.readFile(absolutePath, { cellFormula: true, cellNF: true });
        const worksheet = workbook.Sheets[workbook.SheetNames[0]]; // Loads your primary P-Table sheet
        this.sheetName = workbook.SheetNames[0];

        // 2. Convert worksheet to a 2D array of values and formulas for HyperFormula
        const sheetData = XLSX.utils.sheet_to_json(worksheet, { header: 1, raw: false });

        // 3. Initialize HyperFormula with default configurations
        this.hf = HyperFormula.buildFromArray(sheetData, {
            licenseKey: 'gpl-v3'
        });

        console.log(`[Univac Engine] Interlinked dependency graph initialized for sheet: ${this.sheetName}`);
    }

    /**
     * Dynamically updates user inputs (e.g., changing Electrons or Charge)
     * @param {string} cellAddress - e.g., 'C5'
     * @param {any} newValue - New element state configuration value
     */
    updateCellState(cellAddress, newValue) {
        const sheetId = this.hf.getSheetId(this.sheetName);
        const { col, row } = this.hf.simpleCellAddressFromString(cellAddress);

        // Update value and trigger instant recalculation across all dependent cells
        this.hf.setCellContents({ sheet: sheetId, col, row }, [[newValue]]);
    }

    /**
     * Retrieves the calculated output (e.g., the computed final color column value)
     * @param {string} cellAddress - e.g., 'Z5'
     */
    getCalculatedOutput(cellAddress) {
        const sheetId = this.hf.getSheetId(this.sheetName);
        const { col, row } = this.hf.simpleCellAddressFromString(cellAddress);
        
        // Returns evaluated math/physics result from the Excel formula graph
        return this.hf.getCellValue({ sheet: sheetId, col, row });
    }
}

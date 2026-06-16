import { HyperFormula } from 'hyperformula';
import * as XLSX from 'xlsx';
import * as path from 'path';

function validateExcelFormulas() {
    // Exact path matching your updated repository link
    const xlsxPath = path.resolve('./assets/data/elements_period_table_index.xlsx');
    
    console.log(`[Validation] Loading spreadsheet from: ${xlsxPath}`);
    
    // 1. Read workbook keeping raw formulas intact
    const workbook = XLSX.readFile(xlsxPath, { cellFormula: true });
    const sheetName = workbook.SheetNames[0]; // Parses the primary table sheet
    const worksheet = workbook.Sheets[sheetName];

    // 2. Transform to a 2D array matrix for HyperFormula
    const sheetData = XLSX.utils.sheet_to_json(worksheet, { header: 1, raw: false });

    // 3. Initialize the compilation engine
    const hf = HyperFormula.buildFromArray(sheetData, {
        licenseKey: 'gpl-v3'
    });

    const sheetId = hf.getSheetId(sheetName);
    let errorCount = 0;

    console.log(`[Validation] Scanning compilation graph for sheet: "${sheetName}"...`);

    // 4. Iterate over every cell in the data grid to verify calculations
    for (let r = 0; r < sheetData.length; r++) {
        if (!sheetData[r]) continue;
        for (let c = 0; c < sheetData[r].length; c++) {
            const cellValue = hf.getCellValue({ sheet: sheetId, col: c, row: r });

            // Detect if HyperFormula flags an unresolvable Excel reference or execution error
            if (cellValue && typeof cellValue === 'object' && cellValue.type) {
                const cellAddress = hf.simpleCellAddressToString({ sheet: sheetId, col: c, row: r });
                console.error(`❌ Formula Error Found at ${cellAddress}: ${cellValue.type} (Message: ${cellValue.message || 'None'})`);
                errorCount++;
            }
        }
    }

    // 5. Enforce Build Pass/Fail
    if (errorCount > 0) {
        console.error(`\n[Validation Failed] Found ${errorCount} unresolvable formula dependency error(s) in elements_period_table_index.xlsx.`);
        process.exit(1); 
    } else {
        console.log(`\n✅ [Validation Passed] All interlinked formulas compiled flawlessly across the grid!`);
        process.exit(0);
    }
}

validateExcelFormulas();

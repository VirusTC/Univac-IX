import { HyperFormula } from 'hyperformula';
import * as XLSX from 'xlsx';
import * as path from 'path';
import * as fs from 'fs';

function validateAndExportExcel() {
    // Target location matching your repository folder path
    const xlsxPath = path.resolve('./assets/data/elements_period_table_index.xlsx');
    const outputPath = path.resolve('./assets/data/compiled_ptable_metadata.json');
    
    console.log(`[Processor] Processing workbook from: ${xlsxPath}`);
    
    // 1. Read the Excel data matrix with formulas preserved
    const workbook = XLSX.readFile(xlsxPath, { cellFormula: true });
    const sheetName = workbook.SheetNames[0]; 
    const worksheet = workbook.Sheets[sheetName];

    // 2. Parse into a raw 2D array representation
    const sheetData = XLSX.utils.sheet_to_json(worksheet, { header: 1, raw: false });

    // 3. Build HyperFormula dependency instance
    const hf = HyperFormula.buildFromArray(sheetData, {
        licenseKey: 'gpl-v3'
    });

    const sheetId = hf.getSheetId(sheetName);
    let errorCount = 0;
    
    // The structured export payload for your frontend or UI engine
    const exportPayload = {
        sheetName: sheetName,
        generatedAt: new Date().toISOString(),
        grid: {}
    };

    console.log(`[Processor] Evaluating matrix cells and dependency calculations...`);

    // 4. Scan data structure and collect structural data
    for (let r = 0; r < sheetData.length; r++) {
        if (!sheetData[r]) continue;
        for (let c = 0; c < sheetData[r].length; c++) {
            const cellValue = hf.getCellValue({ sheet: sheetId, col: c, row: r });
            const cellAddress = hf.simpleCellAddressToString({ sheet: sheetId, col: c, row: r });

            // Detect broken dependency math/references
            if (cellValue && typeof cellValue === 'object' && cellValue.type) {
                console.error(`❌ Formula Defect found at ${cellAddress}: ${cellValue.type}`);
                errorCount++;
            }

            // Append verified computed cells into the export dataset
            if (sheetData[r][c] !== undefined) {
                exportPayload.grid[cellAddress] = {
                    computedValue: cellValue,
                    dataType: typeof cellValue,
                    isFormula: typeof sheetData[r][c] === 'string' && sheetData[r][c].startsWith('=')
                };
            }
        }
    }

    if (errorCount > 0) {
        console.error(`\n[Process Failed] Halted due to ${errorCount} unresolvable calculation errors.`);
        process.exit(1); 
    }

    // 5. Serialize target schema out to disk
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.writeFileSync(outputPath, JSON.stringify(exportPayload, null, 2), 'utf-8');
    console.log(`\n✅ [Export Success] Dynamic dependency matrix generated at: ${outputPath}`);
    process.exit(0);
}

validateAndExportExcel();

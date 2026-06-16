// src/modules/tusk-trunk/autodin-logger.js
const fs = require('fs');
const path = require('path');

class AutodinLogger {
  /**
   * Generates an AUTODIN-style console terminal readout and logs it to a file.
   * @param {Object} callData - Metadata collected by the signaling stack
   */
  static generateAndSaveLog(callData) {
    const rawDate = new Date();
    const isoString = rawDate.toISOString();
    const timestamp = isoString.replace(/[-:]/g, '').split('.')[0] + 'Z';
    const dateStamp = isoString.split('T')[0]; // Format: YYYY-MM-DD
    const sequenceNum = Math.floor(1000 + Math.random() * 9000);
    
    // Map precedence
    let precedenceChar = 'R';
    let precedenceText = 'ROUTINE';
    
    if (callData.priorityFlash) {
      precedenceChar = 'Z';
      precedenceText = 'FLASH OVERRIDE (NATIONAL COMMAND AUTHORITY)';
    } else if (callData.priorityLevel === 'immediate') {
      precedenceChar = 'O';
      precedenceText = 'IMMEDIATE';
    } else if (callData.priorityLevel === 'priority') {
      precedenceChar = 'P';
      precedenceText = 'PRIORITY';
    }

    const routingIndicatorSource = 'RUWJALA'; 
    const routingIndicatorDest   = 'RUEADWW';

    // 1. Construct terminal-formatted text with ANSI colors
    const terminalLog = [
      `\x1b[36m┌─── [UNIVAC-IX COMM CENTER] ──────────────────────────────────────────┐\x1b[0m`,
      `\x1b[33m  AUTODIN SWITCHING NODE: ASC-04 // TRUNK ROUTE ENGAGED              \x1b[0m`,
      `  ZCZC ${precedenceChar}${precedenceChar}A${sequenceNum}  Reference ID: TUSK-CONN-${sequenceNum}`,
      `  DE ${routingIndicatorSource} #0001 ${timestamp}`,
      `  ${precedenceChar} ${timestamp}`,
      `  FM TUSK INFANTRY INT-TERM // REAR RIGHT BRACKET`,
      `  TO UNIVAC MAIN CENTRAL PROCESSING UNIT / DATA REGISTER`,
      `  INFO ${routingIndicatorDest}`,
      `  BT`,
      `  \x1b[1;31mUNCLASSIFIED // UNIFIED COMMUNICATIONS LINK ACTIVATED\x1b[0m`,
      `  OPERATIONAL PRECEDENCE: [${precedenceText}]`,
      `  CIRCUIT VOLTAGE: ${callData.voltage || '12'}VDC  |  LOOP CURRENT: ${callData.loopCurrent || '24mA'}`,
      `  I/O CHANNEL REASSIGNMENT STATUS: COMPLETE (PRIORITY INTERRUPT FORCE)`,
      `  BT`,
      `  NNNN`,
      `\x1b[36m└─── [TRANSMISSION PROCESSED] ────────────────────────────────────────┘\x1b[0m`
    ].join('\n');

    // 2. Create a clean plain-text copy for the log file (Strips out the \x1b color tags)
    const plainTextLog = terminalLog.replace(/\x1b\[[0-9;]*m/g, '');

    // 3. Write asynchronously to the disk target
    AutodinLogger.saveToFile(dateStamp, plainTextLog);

    // Return the colorful one for console printing
    return terminalLog;
  }

  /**
   * Safe asynchronous file persistent storage system
   */
  static saveToFile(dateStamp, textContent) {
    // Resolve location to the absolute root directory of your project: /logs/autodin/
    const targetDir = path.resolve(__dirname, '../../..', 'logs', 'autodin');
    const targetFile = path.join(targetDir, `${dateStamp}.log`);

    // Ensure the entire path folders tree exist before appending data
    fs.mkdir(targetDir, { recursive: true }, (dirError) => {
      if (dirError) {
        console.error(`[File System Error] Failed to prepare AUTODIN directory structure: ${dirError.message}`);
        return;
      }

      // Append transmission block with trailing newlines for separation spacing
      fs.appendFile(targetFile, textContent + '\n\n', 'utf8', (writeError) => {
        if (writeError) {
          console.error(`[File System Error] Failed to write message data log file: ${writeError.message}`);
        }
      });
    });
  }
}

module.exports = AutodinLogger;
// src/modules/tusk-trunk/autodin-logger.js

class AutodinLogger {
  /**
   * Generates a vintage 1970s AUTODIN-style console terminal readout
   * @param {Object} callData - Metadata collected by the signaling stack
   * @returns {string} Fully formatted ASCII teletype-style log string
   */
  static generateLog(callData) {
    const timestamp = new Date().toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
    const sequenceNum = Math.floor(1000 + Math.random() * 9000);
    
    // Map modern variables to historical MIL-SPEC precedence characters
    let precedenceChar = 'R'; // Routine default
    let precedenceText = 'ROUTINE';
    
    if (callData.priorityFlash) {
      precedenceChar = 'Z';
      precedenceText = 'FLASH OVERRIDE (NATIONAL COMMAND AUTHORITY)';
    } else if (callData.priorityLevel === 'immediate') {
      precedenceChar = 'O';
      precedenceText = 'IMMEDIATE';
    } else if (callData.priorityLevel === 'priority') {
      precedenceChar = 'P';
      precedenceText = 'PRIORITY';
    }

    const routingIndicatorSource = 'RUWJALA'; // Fixed sample Pentagon Command Switch node
    const routingIndicatorDest   = 'RUEADWW'; // Fixed sample White House Communications Agency node

    // Constructing a historically accurate ACP 127 / JANAP 128 Message Format
    return [
      `\x1b[36m┌─── [UNIVAC-IX COMM CENTER] ──────────────────────────────────────────┐\x1b[0m`,
      `\x1b[33m  AUTODIN SWITCHING NODE: ASC-04 // TRUNK ROUTE ENGAGED              \x1b[0m`,
      `  ZCZC ${precedenceChar}${precedenceChar}A${sequenceNum}  Reference ID: TUSK-CONN-${sequenceNum}`,
      `  DE ${routingIndicatorSource} #0001 ${timestamp}`,
      `  ${precedenceChar} ${timestamp}`,
      `  FM TUSK INFANTRY INT-TERM // REAR RIGHT BRACKET`,
      `  TO UNIVAC MAIN CENTRAL PROCESSING UNIT / DATA REGISTER`,
      `  INFO ${routingIndicatorDest}`,
      `  BT`,
      `  \x1b[1;31mUNCLASSIFIED // UNIFIED COMMUNICATIONS LINK ACTIVATED\x1b[0m`,
      `  OPERATIONAL PRECEDENCE: [${precedenceText}]`,
      `  CIRCUIT VOLTAGE: ${callData.voltage || '12'}VDC  |  LOOP CURRENT: ${callData.loopCurrent || '24mA'}`,
      `  I/O CHANNEL REASSIGNMENT STATUS: COMPLETE (PRIORITY INTERRUPT FORCE)`,
      `  BT`,
      `  NNNN`,
      `\x1b[36m└─── [TRANSMISSION PROCESSED] ────────────────────────────────────────┘\x1b[0m`
    ].join('\n');
  }
}

module.exports = AutodinLogger;

import { Worker } from 'worker_threads';
import * as path from 'path';

const workerPath = path.resolve('./src/modules/light_app/light_worker.js');
const telecomWorker = new Worker(workerPath);

// Default fiber configuration using Glass/Silica base indices mapped in your sheet
let linkConfiguration = {
    coreMaterial: "Glass_Silica",
    electrons: 14,
    charge: 0
};

/**
 * Mainframe Core Boot Sequence
 */
(() => {
    // Initial load path targeting your Excel compiler artifact folder 
    telecomWorker.postMessage({
        action: 'LOAD_FIBER_METRICS',
        payload: { jsonUrl: '../../assets/data/compiled_ptable_metadata.json' }
    });

    telecomWorker.on('message', (response) => {
        const { status, telecomFrame, error } = response;

        if (status === 'CORE_READY') {
            // Begins internal computation sequences immediately without interface halts
            beginTelemetryIngestion();
        }

        if (status === 'COMPUTATION_SUCCESS') {
            // Write the pure JSON directly to standard output for your external KVM bridge system
            process.stdout.write(JSON.stringify(telecomFrame) + "\n");
        }

        if (status === 'CORE_FAULT') {
            process.stderr.write(`[MAINFRAME EXCEPTION] ${error}\n`);
        }
    });
})();

/**
 * Real-Time Hardware Processing Simulation Loop
 */
function beginTelemetryIngestion() {
    setInterval(() => {
        // Fetch raw physical track signal input array (e.g., length 128 indices)
        const rawOtdrBuffer = sampleOtdrHardwareTracks();

        telecomWorker.postMessage({
            action: 'PROCESS_TELECOM_TRACE',
            payload: {
                rawTraceBuffer: rawOtdrBuffer,
                sampleRateHz: 5000000, // 5 MHz instrumentation processing sample window
                linkConfig: linkConfiguration
            }
        });
    }, 15); // Dispatches computation cycles continually at high speeds
}

/**
 * Changes runtime equations target variables (can be called by your wrapper apps)
 */
export function reconfigureCoreSubstance(coreMaterial, electrons, charge) {
    linkConfiguration = { coreMaterial, electrons, charge };
}

/**
 * Mock OTDR Reflection Waveform Data Intake Generator
 */
function sampleOtdrHardwareTracks(length = 64) {
    const track = new Float32Array(length);
    for (let i = 0; i < length; i++) {
        let baseSignalDrop = 60 - (i * 0.5); // Standard fiber loss slope line
        
        if (i === 20) baseSignalDrop -= 1.5; // Simulate a standard splice drop event location
        if (i === 45) baseSignalDrop -= 5.0; // Simulate a severe air bubble cavity reflection trap
        
        const electronicNoiseFloor = Math.random() * 0.2;
        track[i] = Math.max(0, baseSignalDrop + electronicNoiseFloor);
    }
    return track;
}

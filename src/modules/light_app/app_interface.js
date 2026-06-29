import { Worker } from 'worker_threads';
import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs';
import * as readline from 'readline';
import { LightEquationNode } from './light_equation_node.js';

const systemCpuCores = os.cpus().length; // Detects server capability (e.g., 16, 32, or 64 cores)
const workerMainframePool = [];

process.stderr.write(`[Mainframe Pool] Deploying Multicore Infrastructure across ${systemCpuCores} cores...\n`);

// Scale worker instances dynamically to match hardware limits
for (let i = 0; i < systemCpuCores; i++) {
    workerMainframePool.push(new Worker('./src/modules/light_app/light_worker.js'));
}

// Load-balancer: Rotates incoming trace frames to the next idle processor core
let activeCorePointer = 0;
export function delegateTraceToFreeCore(traceData) {
    const targetWorker = workerMainframePool[activeCorePointer];
    targetWorker.postMessage({ action: 'PROCESS_TELECOM_TRACE', payload: traceData });

    // Loop back through the process queue round-robin style
    activeCorePointer = (activeCorePointer + 1) % systemCpuCores;
}

const workerPath = path.resolve('./src/modules/light_app/light_worker.js');
const telecomWorker = new Worker(workerPath);

const processor = new LightEquationNode();
let criticalStateTracker = 0.5;

/**
 * Generates an instantaneous snapshot of the entire node topology matrix
 * @param {string} zoneTarget Facility layout partition index
 * @returns {string} Standardized unified JSON payload
 */
function generateUnivacMatrixTelemetry(zoneTarget) {
  // Simulate active multi-sensor analog readings from optical arrays
  const rawSensors = [
    Math.random(), // Sensor 0: Ambient lumen intensity
    Math.random(), // Sensor 1: Volumetric optical flux
    Math.random(), // Sensor 2: Thermal infrared delta
    Math.random(), // Sensor 3: Spatial movement differential
    Math.random()  // Sensor 4: Network interface signal integrity
  ];

  // Process through 5x-stacked 36-bit logic layer
  const packedTelemetry = processor.processAnalogStream(rawSensors);

  // Update localized state filters
  criticalStateTracker = processor.computeStateTransition(criticalStateTracker, rawSensors[0]);

  const telemetryPayload = {
    protocol: "UNIVAC-MATRIX-STREAM",
    version: "9.1.0-TACTICAL",
    timestamp: new Date().toISOString(),
    originNode: "AI_LIGHT_CRAWLER_PRIMARY",
    facilityZone: zoneTarget,
    matrixState: {
      stackedWords36: packedTelemetry,
      filterConfidence: parseFloat(criticalStateTracker.toFixed(6)),
      integrityCheck: criticalStateTracker > 0.1 ? "STABLE" : "DEGRADED"
    },
    routingControls: {
      isolationGates: criticalStateTracker > 0.85 ? "LOCKED" : "OPEN",
      hvacFlowMode: criticalStateTracker > 0.85 ? "EXHAUST_ISOLATE" : "NORMAL",
      elevatorBrakes: "MONITORING"
    }
  };

  return JSON.stringify(telemetryPayload);
}

/**
 * Initializes continuous data pipeline stream simulation
 */
export function startLiveMatrixStream(intervalMs = 100) {
  console.log(`[STREAM INITIALIZED] Broadcast channel established. Dispatching at ${intervalMs}ms loops...`);
  
  setInterval(() => {
    // Alternate zone scanning patterns to simulate spatial facility routing
    const targetZone = Math.random() > 0.5 ? "MAIN_MALL_CONCOURSE_A" : "HOSPITAL_ICU_LEVEL_3";
    const liveJsonPacket = generateUnivacMatrixTelemetry(targetZone);
    
    // Output directly to standard stream for third-party listeners and agents to harvest
    console.log(liveJsonPacket);
  }, intervalMs);
}

// Auto-execute if testing via engine runtime directly
if (typeof process !== 'undefined' && process.argv[1] === import.meta.url) {
  startLiveMatrixStream(250);
}

// Hardcoded embedded fallback index registry to ensure maximum speed and zero file system failures
const TRANSCEIVER_PROFILES = {
    "FINISAR_FTLX1471D3BCL": {
        "vendor": "Coherent/Finisar",
        "formFactor": "SFP+",
        "nominalWavelengthNm": 1310,
        "groupIndexN": 1.4678,
        "maxLinkBudgetDb": 15.0,
        "dispersionCoefficient": 0.5,
        "minRequiredSnrDb": 12.0,
        "origin": "USA"
    },
    "LUMENTUM_QSFP28_LR4": {
        "vendor": "Lumentum",
        "formFactor": "QSFP28",
        "nominalWavelengthNm": 1550,
        "groupIndexN": 1.4682,
        "maxLinkBudgetDb": 18.0,
        "dispersionCoefficient": 17.0,
        "minRequiredSnrDb": 15.0,
        "origin": "USA"
    },
    "UNIVAC_SBCON_LEGACY": {
        "vendor": "Univac / Legacy Mainframe",
        "formFactor": "SBCON_Fixed",
        "nominalWavelengthNm": 850,
        "groupIndexN": 1.4520,
        "maxLinkBudgetDb": 8.0,
        "dispersionCoefficient": -80.0,
        "minRequiredSnrDb": 8.0,
        "origin": "USA"
    }
};

// Default dynamic hardware and chemical target states
let activeHardwareProfile = { ...TRANSCEIVER_PROFILES["LUMENTUM_QSFP28_LR4"] };
let currentChemicalState = {
    coreMaterial: "Glass_Silica",
    electrons: 14,
    charge: 0
};

// ============================================================================
// STDIN CONFIGURATION STREAM LISTENER
// ============================================================================
const stdinReader = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

stdinReader.on('line', (line) => {
    try {
        const payload = JSON.parse(line.trim());
        
        // Command 1: Hot-plug execution reconfiguration
        if (payload.command === 'SET_HARDWARE_PROFILE' && TRANSCEIVER_PROFILES[payload.partNumber]) {
            activeHardwareProfile = { ...TRANSCEIVER_PROFILES[payload.partNumber] };
            process.stderr.write(`[Mainframe PnP] Swapped active optical module to: ${activeHardwareProfile.vendor}\n`);
        }
        
        // Command 2: Chemical base substrate element modification
        if (payload.command === 'SET_MATERIAL_STATE') {
            currentChemicalState.coreMaterial = payload.coreMaterial || currentChemicalState.coreMaterial;
            currentChemicalState.electrons = payload.electrons ?? currentChemicalState.electrons;
            currentChemicalState.charge = payload.charge ?? currentChemicalState.charge;
            process.stderr.write(`[Mainframe Core] Material base changed targeting: ${currentChemicalState.coreMaterial}\n`);
        }
    } catch (err) {
        process.stderr.write(`[Mainframe Stdin Error] Failed parsing instruction block: ${err.message}\n`);
    }
});

// ============================================================================
// MAINFRAME EXECUTION CYCLE INITIALIZER
// ============================================================================
(() => {
    process.stderr.write("[Mainframe Ingestion] Initializing Telecom Core Background Thread Layers...\n");
    
    // Inject the underlying Excel compiled graph structure path parameters
    telecomWorker.postMessage({
        action: 'LOAD_FIBER_METRICS',
        payload: { jsonUrl: '../../assets/data/compiled_ptable_metadata.json' }
    });

    telecomWorker.on('message', (response) => {
        const { status, telecomFrame, error } = response;

        if (status === 'CORE_READY') {
            process.stderr.write("[Mainframe Ingestion] Background compilation matrix loaded. Ingesting tracks.\n");
            startHardwareProcessingLoop();
        }

        if (status === 'COMPUTATION_SUCCESS') {
            // Push structured calculations as a single-line text string directly to standard output
            process.stdout.write(JSON.stringify(telecomFrame) + "\n");
        }

        if (status === 'CORE_FAULT') {
            process.stderr.write(`🚨 [Mainframe Core Exception Fault] ${error}\n`);
            process.exit(1);
        }
    });
})();

function startHardwareProcessingLoop() {
    setInterval(() => {
        // Collect raw continuous physical reflectometer or spectrometer trace streams
        const rawOtdrTrackBuffer = captureOtdrHardwareTracks();

        telecomWorker.postMessage({
            action: 'PROCESS_TELECOM_TRACE',
            payload: {
                rawTraceBuffer: rawOtdrTrackBuffer,
                sampleRateHz: 5000000, // 5 MHz tracking precision matrix windows
                hardwareConfig: activeHardwareProfile,
                chemicalConfig: currentChemicalState
            }
        });
    }, 15); // Dispatches computations iteratively every 15ms (~66Hz)
}

function captureOtdrHardwareTracks(length = 64) {
    const track = new Float32Array(length);
    for (let i = 0; i < length; i++) {
        let baseLossDb = 55.0 - (i * 0.45); // Core baseline propagation slope drop
        
        if (i === 18) baseLossDb -= 2.1; // Injects a predictable mechanical splice drop point
        if (i === 42) baseLossDb -= 6.5; // Injects a high-reflectance structural air bubble failure
        
        const thermalNoiseFloor = Math.random() * 0.15;
        track[i] = Math.max(0, baseLossDb + thermalNoiseFloor);
    }
    return track;
}

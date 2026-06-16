import { UnivacLightEquationNode } from './modules/light_equation_node.js';
import { UnivacOpticalNoiseProcessor } from './modules/optical_noise_processor.js';

// Instantiate Core Logical Engines
const equationNode = new UnivacLightEquationNode();
const noiseProcessor = new UnivacOpticalNoiseProcessor(equationNode);

let dataStreamInterval = null;

// Wait for DOM Elements to render
window.addEventListener('DOMContentLoaded', async () => {
    const statusLabel = document.getElementById('engine-status');
    const btnStream = document.getElementById('btn-toggle-stream');

    // 1. Fetch JSON compiled Excel artifacts right away on load
    const loadSuccess = await equationNode.initializationPipeline('/assets/data/compiled_ptable_metadata.json');
    
    if (loadSuccess) {
        statusLabel.innerText = "ONLINE (READY)";
        statusLabel.style.color = "#22c55e";
        btnStream.disabled = false; // Safely unlock control stream loop actions
        initializeUIListeners();
    } else {
        statusLabel.innerText = "CRITICAL FAILURE (CHECK LOGS)";
        statusLabel.style.color = "#ef4444";
    }
});

function initializeUIListeners() {
    const btnNoise = document.getElementById('btn-capture-noise');
    const btnStream = document.getElementById('btn-toggle-stream');
    
    const txtElement = document.getElementById('input-element');
    const txtElectrons = document.getElementById('input-electrons');
    const txtCharge = document.getElementById('input-charge');

    // Display telemetry DOM pointers
    const displaySnr = document.getElementById('telemetry-snr');
    const displayPeak = document.getElementById('telemetry-peak');
    const displayAtten = document.getElementById('telemetry-attenuation');
    const displayRow = document.getElementById('telemetry-row');
    const emitterViewport = document.getElementById('emitter-viewport');

    // Mock hardware signal telemetry feed generator
    const generateMockHardwareTrack = (vectorLength = 128) => {
        const sampleBuffer = new Float32Array(vectorLength);
        const dynamicPhaseShift = Date.now() * 0.005; // Generates a smooth fluid movement matrix over time
        for(let i = 0; i < vectorLength; i++) {
            const cleanPhotonWave = Math.sin(i * 0.15 + dynamicPhaseShift) * 45 + 50;
            const environmentalNoise = Math.random() * 18 + 4; // Simulated baseline hum noise floor
            sampleBuffer[i] = cleanPhotonWave + environmentalNoise;
        }
        return sampleBuffer;
    };

    // Action A: Sample the Ambient Environment profile
    btnNoise.addEventListener('click', () => {
        const backgroundSnapshot = generateMockHardwareTrack();
        noiseProcessor.calibrateNoiseProfile(backgroundSnapshot);
        
        btnNoise.innerText = "Noise Profile Subtracted! 🎯";
        btnNoise.classList.add('success-state');
    });

    // Action B: Toggle Stream Calculus Array processing
    btnStream.addEventListener('click', () => {
        if (dataStreamInterval) {
            // Stop loop sequence
            clearInterval(dataStreamInterval);
            dataStreamInterval = null;
            
            btnStream.innerText = "Start Optical Stream";
            btnStream.classList.remove('primary-action');
            emitterViewport.style.backgroundColor = "#000000";
            emitterViewport.innerText = "STREAM INACTIVE";
        } else {
            btnStream.innerText = "Halt Stream ⏸";
            btnStream.classList.add('primary-action');

            // Launch the 33ms execution loop (30Hz real-time frequency processing)
            dataStreamInterval = setInterval(() => {
                const liveRawTrackInput = generateMockHardwareTrack();
                
                const targetState = {
                    element: txtElement.value.trim(),
                    electrons: parseInt(txtElectrons.value, 10) || 0,
                    charge: parseInt(txtCharge.value, 10) || 0
                };

                // Process the streaming signals through the pipeline modules
                const processedResults = noiseProcessor.processIncomingTrack(liveRawTrackInput, targetState);

                if (processedResults && !processedResults.chemicalContext.error) {
                    const ctx = processedResults.chemicalContext;
                    
                    // Update Text Outputs
                    displaySnr.innerText = `${processedResults.telemetry.signalToNoiseRatioDb} dB`;
                    displayPeak.innerText = `${processedResults.telemetry.peakIntensity} lm`;
                    displayAtten.innerText = `${processedResults.telemetry.averageAttenuation} dB/km`;
                    displayRow.innerText = `Row ${ctx.matchedRow || '--'}`;

                    // Update dynamic color output straight from your spreadsheet formulas
                    if (ctx.calculatedColorHex) {
                        emitterViewport.style.backgroundColor = ctx.calculatedColorHex;
                        emitterViewport.innerText = `ACTIVE EMISSION: ${ctx.calculatedColorHex.toUpperCase()}`;
                    }
                } else if (processedResults && processedResults.chemicalContext.error) {
                    // Inform operator if an invalid chemical lookup occurred
                    emitterViewport.style.backgroundColor = "#2d1010";
                    emitterViewport.innerText = `ERROR: ${processedResults.chemicalContext.error}`;
                }
            }, 33);
        }
    });
}

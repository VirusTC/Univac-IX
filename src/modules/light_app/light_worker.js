import { parentPort } from 'worker_threads';
import { UnivacLightEquationNode } from '../light_equation_node.js';

const equationNode = new UnivacLightEquationNode();
let indexDatabaseLoaded = false;

// Vacuum speed of light constant
const SPEED_OF_LIGHT_M_S = 299792458; 

parentPort.on('message', async (message) => {
    const { action, payload } = message;

    // 1. Compile Spreadsheet Asset Matrix
    if (action === 'LOAD_FIBER_METRICS') {
        const success = await equationNode.initializationPipeline(payload.jsonUrl);
        if (success) {
            indexDatabaseLoaded = true;
            parentPort.postMessage({ status: 'CORE_READY' });
        } else {
            parentPort.postMessage({ status: 'CORE_FAULT', error: 'Could not load elements database index.' });
        }
    }

    // 2. Headless Computational Pass
    if (action === 'PROCESS_TELECOM_TRACE') {
        if (!indexDatabaseLoaded) return;

        const { rawTraceBuffer, sampleRateHz, linkConfig } = payload;
        
        // Fetch dynamic material constants calculated via your Excel graph formulas
        const cellData = equationNode.executeDynamicLightCalculation(
            linkConfig.coreMaterial, 
            { electrons: linkConfig.electrons, charge: linkConfig.charge }
        );

        // Fallback or mapped refractive index (Group Index N) from sheet data
        const groupIndexN = cellData.effectiveRefractive_N || 1.4682; 
        
        const calculatedPoints = [];
        let totalAttenuationLossDb = 0;
        let anomalyCount = 0;

        // Math: Process the raw optical array matrix down to individual events
        for (let i = 0; i < rawTraceBuffer.length; i++) {
            // Time of flight conversion per index interval sample step
            const timeOfFlightSeconds = i / sampleRateHz;
            const absoluteDistanceMeters = (SPEED_OF_LIGHT_M_S * timeOfFlightSeconds) / (2 * groupIndexN);

            const amplitude = rawTraceBuffer[i];
            let eventDescriptor = "Normal Propagation";

            // Splice Loss and Bubble Defect Event Detection via Rayleigh backscatter drops
            if (i > 0) {
                const stepLoss = rawTraceBuffer[i - 1] - amplitude;
                
                if (stepLoss > 0.5 && stepLoss < 3.0) {
                    eventDescriptor = "Mechanical or Fusion Splice Detected";
                    anomalyCount++;
                } else if (stepLoss >= 3.0) {
                    // Massive Fresnel drop indicates air bubble void or core structural fault
                    eventDescriptor = "Air Bubble Defect / Core Gap Anomaly Flagged";
                    anomalyCount++;
                }
            }

            calculatedPoints.push({
                index: i,
                distanceMeters: parseFloat(absoluteDistanceMeters.toFixed(3)),
                amplitudeDb: parseFloat(amplitude.toFixed(4)),
                status: eventDescriptor
            });
        }

        // Output pure calculation object back up to the processor orchestrator
        parentPort.postMessage({
            status: 'COMPUTATION_SUCCESS',
            telecomFrame: {
                timestamp: Date.now(),
                telemetry: {
                    totalMonitoredDistanceMeters: calculatedPoints[calculatedPoints.length - 1].distanceMeters,
                    anomalyEventCount: anomalyCount,
                    coreMaterialActive: linkConfig.coreMaterial,
                    spectralHexSignature: cellData.calculatedColorHex || "#ffffff"
                },
                traceMatrix: calculatedPoints
            }
        });
    }
});

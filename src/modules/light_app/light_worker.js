import { UnivacLightEquationNode } from '../light_equation_node.js';
import { UnivacOpticalNoiseProcessor } from '../optical_noise_processor.js';

const equationNode = new UnivacLightEquationNode();
let noiseProcessor = null;

// Pure Headless Data Pipeline
self.onmessage = async (event) => {
    const { action, payload } = event.data;

    // 1. Initial Data Matrix Intake
    if (action === 'INITIALIZE_MAINFRAME') {
        const success = await equationNode.initializationPipeline(payload.jsonUrl);
        if (success) {
            noiseProcessor = new UnivacOpticalNoiseProcessor(equationNode);
            self.postMessage({ status: 'MAINFRAME_ONLINE' });
        } else {
            self.postMessage({ status: 'MAINFRAME_ERROR', error: 'Formula matrix failed compilation.' });
        }
    }

    // 2. High-Speed Calibration
    if (action === 'CALIBRATE_NOISE_FLOOR') {
        if (noiseProcessor) {
            noiseProcessor.calibrateNoiseProfile(payload.rawSample);
            self.postMessage({ status: 'NOISE_FLOOR_SET' });
        }
    }

    // 3. Maximum Throughput Stream Computation (Zero-GUI Bottleneck)
    if (action === 'COMPUTE_MATRIX_FRAME') {
        if (!noiseProcessor) return;

        // Perform raw mathematical and optical physics transformations
        const calculationOutput = noiseProcessor.processIncomingTrack(
            payload.liveTrack, 
            payload.targetState
        );

        // Dispatches pure numeric telemetry back down the pipeline
        self.postMessage({ 
            status: 'COMPUTATION_COMPLETE', 
            data: calculationOutput 
        });
    }
};

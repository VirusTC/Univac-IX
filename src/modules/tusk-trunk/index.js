// src/modules/tusk-trunk/index.js
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const SipStack = require('./sip-stack');
const AudioEngine = require('./audio-engine');
const LineTelemetryManager = require('./line-telemetry');
const MainframeInterfaceDriver = require('./mainframe-interface'); // Import the new driver

module.exports = {
  name: 'tuskTrunk',

  init(context) {
    let config = {};
    try {
      const configPath = path.resolve(__dirname, '../../..', 'config.yaml');
      config = yaml.load(fs.readFileSync(configPath, 'utf8'));
    } catch (e) {
      config = { mainframe_io_profile: 'DORADO_ROCE' };
    }

    // Initialize all layers
    const targetIoMode = config.mainframe_io_profile || 'DORADO_ROCE';
    const mainframeDriver = new MainframeInterfaceDriver(targetIoMode);
    const audioEngine = new AudioEngine(config.audio_engine?.acoustic_profile || 'SENNHEISER');
    const telemetry = new LineTelemetryManager({ gatewayIp: config.telephony?.gateway?.ip || '192.168.1.200' });

    // Handle structural line metrics passing through
    telemetry.on('metrics_update', (metrics) => {
      // Package metrics alongside the selected interface profiles
      metrics.backplaneMode = targetIoMode;
      if (context.stateManager) context.stateManager.update('trunk:telemetry', metrics);
    });

    // Fire signaling changes (like MLPP priority overrides)
    SipStack.events.on('ptt_pressed', (headers) => {
      telemetry.startCallTracking();
      
      // Pass headers over to the driver to inspect for high-priority command overrides
      mainframeDriver.processSignalingRules({
        priorityFlash: headers?.priority === 'flash' || false,
        callerId: headers?.from?.uri || 'TUSK-Terminal'
      });
    });

    // Handle Streaming Audio Pipelines
    SipStack.events.on('audio_data', (rawMuLawBuffer) => {
      // 1. Process studio-grade high-fidelity noise cancellation curves
      const linearPcmBuffer = audioEngine.muLawToPcm(rawMuLawBuffer);
      const highFidelityBuffer = audioEngine.applyNoiseCancellation(linearPcmBuffer);

      // 2. Format the buffer to match the selected Mainframe Memory I/O layout
      const dynamicMainframePayload = mainframeDriver.formatMediaForBackplane(highFidelityBuffer);

      // 3. Hand data directly over to your central Univac network processors
      if (context.router) {
        if (targetIoMode.includes('MODERN')) {
          context.router.streamToWebRTC(dynamicMainframePayload);
        } else {
          context.router.broadcastToRawBuffers(dynamicMainframePayload);
        }
      }
    });

    SipStack.events.on('ptt_released', () => {
      telemetry.stopCallTracking();
    });

    // Start signaling server
    SipStack.start({
      ip: config.telephony?.trunk?.ip || '192.168.1.100',
      port: config.telephony?.trunk?.port || 5060
    });
  }
};

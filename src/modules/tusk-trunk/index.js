// src/modules/tusk-trunk/index.js
const SipStack = require('./sip-stack');
const AudioEngine = require('./audio-engine');
const LineTelemetryManager = require('./line-telemetry');

module.exports = {
  name: 'tuskTrunk',

  init(context) {
    console.log('[Module: TUSK Trunk] Initializing high-fidelity audio engine & telemetry node.');

    // 1. Instantiating processing layers
    const targetProfile = process.env.AUDIO_DSP_PROFILE || 'SENNHEISER';
    const audioEngine = new AudioEngine(targetProfile);
    
    const telemetry = new LineTelemetryManager({
      gatewayIp: process.env.GATEWAY_MANAGEMENT_IP || '192.168.1.200'
    });

    // 2. Wire hardware telemetry events to central infrastructure
    telemetry.on('metrics_update', (metrics) => {
      // Expose metrics universally across Univac-IX nodes
      if (context.stateManager) {
        context.stateManager.update('trunk:telemetry', metrics);
      }
    });

    telemetry.on('call_start', (data) => {
      console.log(`[Billing/Timing] Call started for ID: ${data.callerId}`);
    });

    // 3. Link audio processing pipelines during SIP events
    SipStack.start({
      ip: process.env.UNIVAC_TRUNK_IP || '192.168.1.100',
      port: parseInt(process.env.UNIVAC_TRUNK_PORT, 10) || 5060
    });

    SipStack.events.on('ptt_pressed', (inboundSdpHeaders) => {
      const detectedCallerId = inboundSdpHeaders?.from?.uri || 'TUSK-Terminal';
      telemetry.startCallTracking(detectedCallerId);
    });

    SipStack.events.on('audio_data', (rawMuLawBuffer) => {
      // Step A: Convert the restrictive telecom codec to 16-bit linear PCM space
      const linearPcmBuffer = audioEngine.muLawToPcm(rawMuLawBuffer);

      // Step B: Strip background line hiss, mechanical rumble, and apply equalization curves
      const highFidelityBuffer = audioEngine.applyNoiseCancellation(linearPcmBuffer);

      // Step C: Route the sanitized stream to core system formats
      if (context.router) {
        // Example distribution mechanisms based on target format requirement:
        context.router.broadcastToRawBuffers(highFidelityBuffer);
        context.router.streamToWebRTC(highFidelityBuffer);
      }
    });

    SipStack.events.on('ptt_released', () => {
      telemetry.stopCallTracking();
    });
  }
};

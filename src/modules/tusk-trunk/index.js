// src/modules/tusk-trunk/index.js
const sipStack = require('./sip-stack');

module.exports = {
  name: 'tuskTrunk',
  
  /**
   * Initializes the TUSK trunk module within the application runtime
   * @param {Object} context - The central application or node context
   */
  init(context) {
    console.log('[Module: TUSK Trunk] Initializing military phone interface...');
    
    // Start the SIP stack logic
    sipStack.start({
      // Bind configuration variables from your central config module if available
      ip: context.config?.get('TUSK_SIP_IP') || '192.168.1.100',
      port: context.config?.get('TUSK_SIP_PORT') || 5060
    });

    // Example: Registering hooks or publishing events back to your core system
    sipStack.on('callActive', (streamId) => {
      if (context.events) {
        context.events.emit('trunk:connected', { trunk: 'TUSK_Infantry', id: streamId });
      }
    });

    sipStack.on('callDisconnected', (streamId) => {
      if (context.events) {
        context.events.emit('trunk:disconnected', { trunk: 'TUSK_Infantry', id: streamId });
      }
    });
  }
};

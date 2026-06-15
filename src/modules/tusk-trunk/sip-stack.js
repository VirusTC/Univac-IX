// src/modules/tusk-trunk/sip-stack.js
const sip = require('sip');
const dgram = require('dgram');
const EventEmitter = require('events');

// Create an event bus so other files in src/modules can listen to the phone's status
const tuskEvents = new EventEmitter();

let sipServerInstance = null;

/**
 * Starts the SIP stack and begins listening for the TUSK hardware gateway
 * @param {Object} config - Configuration passed from your main application context
 */
function start(config) {
  const options = {
    address: config.ip || '192.168.1.100',
    port: config.port || 5060
  };

  sipServerInstance = sip.start(options, (request) => {
    if (request.method === 'INVITE') {
      handleInboundCall(request, options.address);
    } else if (request.method === 'BYE') {
      handleDisconnect(request);
    }
  });

  console.log(`[TUSK SIP Stack] Listening on ${options.address}:${options.port}`);
}

function handleInboundCall(request, localIp) {
  console.log(`[TUSK Interface] Inbound PTT connection from: ${request.headers.from.uri}`);

  const sdpLines = request.content.split('\r\n');
  let remoteRtpPort = null;
  
  for (let line of sdpLines) {
    if (line.startsWith('m=audio')) {
      remoteRtpPort = parseInt(line.split(' '), 10);
    }
  }

  if (!remoteRtpPort) {
    sip.send(sip.makeResponse(request, 488, 'Not Acceptable Here'));
    return;
  }

  const rtpPortStart = 10000;
  const rtpSocket = dgram.createSocket('udp4');
  
  rtpSocket.bind(rtpPortStart, localIp, () => {
    // Notify your central system that the user pressed the Push-to-Talk button
    tuskEvents.emit('ptt_pressed');
    
    const response = sip.makeResponse(request, 200, 'OK');
    response.headers.contact = [{ uri: `sip:tusk@${localIp}` }];
    response.headers['content-type'] = 'application/sdp';
    
    response.content = 
      `v=0\r\n` +
      `o=TUSK-Framework 123456 123456 IN IP4 ${localIp}\r\n` +
      `s=Talk\r\n` +
      `c=IN IP4 ${localIp}\r\n` +
      `t=0 0\r\n` +
      `m=audio ${rtpPortStart} RTP/AVP 0\r\n` + 
      `a=rtpmap:0 PCMU/8000\r\n`;

    sip.send(response);
    
    rtpSocket.on('message', (msg) => {
      const audioPayload = msg.slice(12); // Strip RTP header
      // Emit the raw audio payload so your core system can route it
      tuskEvents.emit('audio_data', audioPayload);
    });
  });
}

function handleDisconnect(request) {
  console.log('[TUSK Interface] PTT button released.');
  tuskEvents.emit('ptt_released');
  sip.send(sip.makeResponse(request, 200, 'OK'));
}

// Export the methods so src/modules/tusk-trunk/index.js can use them
module.exports = {
  start,
  events: tuskEvents
};

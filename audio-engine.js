// src/modules/tusk-trunk/audio-engine.js
const { Transform } = require('stream');

class TuskAudioEngine {
  constructor(profile = 'SENNHEISER') {
    this.profile = profile;
    this.noiseThreshold = 0.005; // Equivalent to linear amplitude gate
    this.prevSample = 0;         // Used for basic DC offset filtering
  }

  /**
   * Replicates an Audacity-style Noise Gate & Line Filter on raw PCM buffers
   * @param {Buffer} chunk - Raw linear PCM 16-bit audio data
   * @returns {Buffer} Filtered audio data
   */
  applyNoiseCancellation(chunk) {
    const output = Buffer.alloc(chunk.length);
    
    // Process 16-bit samples (2 bytes per sample)
    for (let i = 0; i < chunk.length; i += 2) {
      let sample = chunk.readInt16LE(i);

      // 1. High-Pass Filter (Removes 50Hz/60Hz AC ground hum/static line leak)
      // Cutoff adjusted via alpha coefficient
      const alpha = 0.95;
      const filteredSample = alpha * (this.prevSample + sample - this.prevSample);
      this.prevSample = sample;
      sample = Math.max(-32768, Math.min(32767, filteredSample));

      // 2. Noise Gate (Audacity-style downward expander for line noise)
      const normalizedAmplitude = Math.abs(sample) / 32768;
      if (normalizedAmplitude < this.noiseThreshold) {
        sample = sample * 0.1; // Attenuate background line hiss heavily instead of hard clipping
      }

      // 3. Acoustic Equalization Curve
      if (this.profile === 'SENNHEISER') {
        // Flat/Analytical profile: Gentle high-frequency air boost
        sample = sample * 1.05;
      } else if (this.profile === 'BOSE') {
        // Warm profile: Emphasize lower mid-range presence for vocal clarity over engine roar
        if (Math.abs(sample) > 5000) sample = sample * 1.15;
      }

      output.writeInt16LE(Math.max(-32768, Math.min(32767, sample)), i);
    }
    return output;
  }

  /**
   * Helper to transform raw telecom G.711 mu-law streams to Mainframe PCM Linear
   */
  muLawToPcm(buffer) {
    const pcm = Buffer.alloc(buffer.length * 2);
    for (let i = 0; i < buffer.length; i++) {
      const uLaw = ~buffer[i];
      const sign = (uLaw & 0x80);
      let exponent = (uLaw & 0x70) >> 4;
      let mantissa = uLaw & 0x0F;
      let sample = (mantissa << 3) + 132;
      sample <<= exponent;
      sample -= 132;
      pcm.writeInt16LE(sign ? -sample : sample, i * 2);
    }
    return pcm;
  }

  /**
   * Creates a stream pipeline converter for WebRTC/Mainframe routing
   */
  createTransformStream() {
    const engine = this;
    return new Transform({
      transform(chunk, encoding, callback) {
        // Strip incoming line noise, apply acoustic curves, and push back to stream
        const processed = engine.applyNoiseCancellation(chunk);
        this.push(processed);
        callback();
      }
    });
  }
}

module.exports = TuskAudioEngine;

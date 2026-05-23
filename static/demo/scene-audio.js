// scene-audio.js — Web Audio ambient loops for road stops.
// Pure synthesis: noise, oscillators, filters. Each stop gets its own
// per-frame gain based on listener (camera) proximity.

(function () {
  'use strict';

  let ctx = null;
  let masterGain = null;
  let initialized = false;
  const stops = []; // { id, position, kind, gainNode, sources: [] }

  function ensureCtx() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      ctx = new AC();
      masterGain = ctx.createGain();
      masterGain.gain.value = 0.6;
      masterGain.connect(ctx.destination);
    }
    return ctx;
  }

  // ─── Noise generator (white) ──────────────────────────────────────
  function makeNoiseBuffer(seconds) {
    const sr = ctx.sampleRate;
    const buf = ctx.createBuffer(1, sr * seconds, sr);
    const data = buf.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    return buf;
  }

  // ─── Per-kind synth recipes ───────────────────────────────────────
  function buildStopAudio(kind, gainOut) {
    const sources = [];

    function noiseSource(filterType, freq, q, gain) {
      const src = ctx.createBufferSource();
      src.buffer = makeNoiseBuffer(4);
      src.loop = true;
      const filt = ctx.createBiquadFilter();
      filt.type = filterType;
      filt.frequency.value = freq;
      filt.Q.value = q;
      const g = ctx.createGain();
      g.gain.value = gain;
      src.connect(filt).connect(g).connect(gainOut);
      src.start();
      sources.push(src);
      return { src, filt, g };
    }
    function osc(type, freq, gain) {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.value = freq;
      const g = ctx.createGain();
      g.gain.value = gain;
      o.connect(g).connect(gainOut);
      o.start();
      sources.push(o);
      return { o, g };
    }
    function lfo(target, freq, depth, base) {
      const o = ctx.createOscillator();
      o.frequency.value = freq;
      const g = ctx.createGain();
      g.gain.value = depth;
      o.connect(g).connect(target);
      o.start();
      sources.push(o);
      if (base != null) target.value = base;
    }

    switch (kind) {
      case 'wind_low': {
        const n = noiseSource('lowpass', 360, 0.9, 0.22);
        lfo(n.filt.frequency, 0.13, 220, 360);
        break;
      }
      case 'wind_high': {
        const n = noiseSource('bandpass', 1200, 1.4, 0.18);
        lfo(n.filt.frequency, 0.22, 600, 1200);
        break;
      }
      case 'wind_reeds': {
        const n = noiseSource('bandpass', 700, 2.5, 0.16);
        lfo(n.filt.frequency, 0.4, 280, 700);
        // soft whistle
        const w = osc('sine', 612, 0.012);
        lfo(w.o.frequency, 0.31, 40, 612);
        break;
      }
      case 'transformer_hum': {
        osc('sine', 60, 0.06);
        const h = osc('sawtooth', 120, 0.018);
        lfo(h.g.gain, 0.7, 0.008, 0.018);
        noiseSource('highpass', 4000, 0.6, 0.025);
        break;
      }
      case 'distant_chatter': {
        // band-passed noise + amplitude bursts to suggest voices
        const n = noiseSource('bandpass', 900, 4, 0.16);
        // gain LFOs at irregular rates
        lfo(n.g.gain, 1.7, 0.10, 0.10);
        lfo(n.g.gain, 0.3, 0.06, 0.10);
        // a couple of vowel-ish formants
        const f1 = osc('triangle', 220, 0.012);
        lfo(f1.g.gain, 0.9, 0.012, 0.012);
        break;
      }
      case 'crate_creak': {
        noiseSource('bandpass', 380, 2.5, 0.06);
        // intermittent thud — handled by ad-hoc scheduling
        scheduleHits(gainOut, 280, 0.04, 8000);
        break;
      }
      case 'engine_idle': {
        osc('sawtooth', 36, 0.04);
        const r = osc('square', 72, 0.012);
        lfo(r.o.frequency, 4, 6, 72);
        noiseSource('bandpass', 240, 1.2, 0.05);
        break;
      }
      case 'insect_chirps': {
        // random short blips, plus low ambient
        noiseSource('lowpass', 280, 0.7, 0.07);
        scheduleChirps(gainOut);
        break;
      }
      case 'sensor_ping': {
        // periodic ping every ~3.5s
        schedulePings(gainOut, 3.5);
        noiseSource('highpass', 6000, 0.4, 0.018);
        break;
      }
    }

    function scheduleHits(out, freq, gain, intervalMs) {
      const id = setInterval(() => {
        if (!ctx) return;
        const now = ctx.currentTime;
        const o = ctx.createOscillator();
        o.type = 'sine';
        o.frequency.value = freq;
        const g = ctx.createGain();
        g.gain.setValueAtTime(0, now);
        g.gain.linearRampToValueAtTime(gain, now + 0.01);
        g.gain.exponentialRampToValueAtTime(0.0001, now + 0.4);
        o.connect(g).connect(out);
        o.start(now);
        o.stop(now + 0.5);
      }, intervalMs + Math.random() * 4000);
      sources.push({ stop: () => clearInterval(id) });
    }
    function scheduleChirps(out) {
      const id = setInterval(() => {
        if (!ctx) return;
        if (Math.random() < 0.7) return;
        const now = ctx.currentTime;
        const base = 3200 + Math.random() * 1200;
        for (let n = 0; n < 3; n++) {
          const o = ctx.createOscillator();
          o.type = 'triangle';
          o.frequency.value = base + n * 60;
          const g = ctx.createGain();
          const start = now + n * 0.07;
          g.gain.setValueAtTime(0, start);
          g.gain.linearRampToValueAtTime(0.04, start + 0.01);
          g.gain.exponentialRampToValueAtTime(0.0001, start + 0.06);
          o.connect(g).connect(out);
          o.start(start);
          o.stop(start + 0.08);
        }
      }, 800);
      sources.push({ stop: () => clearInterval(id) });
    }
    function schedulePings(out, intervalS) {
      const id = setInterval(() => {
        if (!ctx) return;
        const now = ctx.currentTime;
        const o = ctx.createOscillator();
        o.type = 'sine';
        o.frequency.value = 1880;
        const g = ctx.createGain();
        g.gain.setValueAtTime(0, now);
        g.gain.linearRampToValueAtTime(0.05, now + 0.01);
        g.gain.exponentialRampToValueAtTime(0.0001, now + 0.5);
        o.connect(g).connect(out);
        o.start(now);
        o.stop(now + 0.6);
      }, intervalS * 1000);
      sources.push({ stop: () => clearInterval(id) });
    }

    return sources;
  }

  // ─── Register a stop with a world position ────────────────────────
  function registerStop(stopID, position, kind) {
    stops.push({ id: stopID, position, kind, gainNode: null, sources: null });
  }

  // ─── User-gesture-gated init ──────────────────────────────────────
  function init() {
    if (initialized) return;
    ensureCtx();
    for (const s of stops) {
      const g = ctx.createGain();
      g.gain.value = 0;
      g.connect(masterGain);
      s.gainNode = g;
      s.sources = buildStopAudio(s.kind, g);
    }
    initialized = true;
  }

  // Update per-stop volume based on listener position (3D-ish falloff)
  function update(listenerPos) {
    if (!initialized) return;
    for (const s of stops) {
      const dx = listenerPos.x - s.position.x;
      const dz = listenerPos.z - s.position.z;
      const d = Math.hypot(dx, dz);
      // audible within ~260u, full near, smooth falloff
      const v = Math.max(0, Math.min(1, 1 - (d - 30) / 230));
      // ramp gently
      s.gainNode.gain.setTargetAtTime(v * 0.5, ctx.currentTime, 0.4);
    }
  }

  function setMaster(v) {
    if (!masterGain) return;
    masterGain.gain.value = v;
  }
  function mute(v) {
    if (!masterGain) return;
    masterGain.gain.value = v ? 0 : 0.6;
  }

  window.SIMUTUM_AUDIO = { registerStop, init, update, setMaster, mute, isInitialized: () => initialized };
})();

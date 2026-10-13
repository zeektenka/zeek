// Synthesise the Midnight Circuit soundtrack straight from the race timeline:
// engines (rpm, gears, doppler, pan from the real camera), wind, a 140 bpm
// synthwave score that drops out for the slow-mo, impacts, crowd and beeps.
//   node tools/audio.mjs out.wav
import { writeFileSync } from 'node:fs';
import * as TL from '../timeline.js';

const SR = 48000, N = Math.ceil(TL.DURATION * SR);
const L = new Float32Array(N), R = new Float32Array(N);
const out = process.argv[2] ?? 'midnight-circuit.wav';

// ---------- helpers
let seed = 1234567;
const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296 * 2 - 1; };
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const ss = TL.smoothstep;
const mix = (i, l, r) => { L[i] += l; R[i] += r; };
function biquadBP() { // RBJ band-pass, coefficients updated per call
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  return (x, f, q) => {
    const w = 2 * Math.PI * clamp(f, 20, SR * 0.45) / SR, al = Math.sin(w) / (2 * q), c = Math.cos(w), a0 = 1 + al;
    const y = ((al) * x + 0 * x1 - al * x2 - (-2 * c) * y1 - (1 - al) * y2) / a0;
    x2 = x1; x1 = x; y2 = y1; y1 = y; return y;
  };
}
const onePole = () => { let y = 0; return (x, f) => { const a = 1 - Math.exp(-2 * Math.PI * f / SR); y += a * (x - y); return y; }; };

// ---------- control-rate tables (camera geometry, car state)
const CR = 600, NC = Math.ceil(TL.DURATION * CR) + 2;
const ctl = [];
for (let k = 0; k < NC; k++) {
  const t = Math.min(k / CR, TL.DURATION - 1e-4);
  const cam = TL.cameraAt(t);
  const fwd = TL.norm(TL.sub(cam.target, cam.pos));
  const right = TL.norm(TL.cross(fwd, cam.up));
  const cars = [0, 1].map((i) => {
    const P = TL.carPose(i, cam.tau);
    const d = TL.sub(P.pos, cam.pos), dist = TL.len(d);
    return { v: P.v, acc: P.acc, air: P.air, dist, pan: clamp(TL.dot(TL.norm(d), right), -1, 1) };
  });
  ctl.push({ t, tau: cam.tau, rate: cam.rate, camPos: cam.pos, cars });
}
for (let k = 0; k < NC; k++) { // radial velocity for doppler, camera speed for wind
  const a = ctl[Math.max(0, k - 3)], b = ctl[Math.min(NC - 1, k + 3)], dt = (b.t - a.t) || 1 / CR;
  ctl[k].cars.forEach((c, i) => { c.vr = (b.cars[i].dist - a.cars[i].dist) / dt; });
  ctl[k].camSpeed = TL.len(TL.sub(b.camPos, a.camPos)) / dt;
}
const ctlAt = (t) => ctl[Math.min(NC - 1, Math.round(t * CR))];

// ---------- engines
const phase = [0, 0], sub = [0, 0], lastGear = [1, 1], shiftT = [-9, -9];
const intake = [biquadBP(), biquadBP()], dopS = [1, 1], gainS = [0, 0], panS = [0, 0];
for (let n = 0; n < N; n++) {
  const t = n / SR, c = ctlAt(t);
  const slow = c.rate;
  for (let i = 0; i < 2; i++) {
    const car = c.cars[i];
    let rpm, gear;
    if (t < TL.T_GO) { // revving on the grid
      const blip = Math.max(0, Math.sin(t * (3.1 + i * 0.4) + i)) ** 3;
      rpm = 1400 + 3200 * blip * ss(0.6, 1.4, t) + 3800 * ss(2.9, 3.8, t); gear = 0;
    } else ({ rpm, gear } = TL.gearRpm(car.v));
    if (gear > lastGear[i]) shiftT[i] = t;
    lastGear[i] = gear;
    const sinceShift = t - shiftT[i];
    const cut = sinceShift < 0.07 ? 0.25 : 1;
    const dop = 420 / (420 + clamp(car.vr, -300, 300));
    dopS[i] += (dop - dopS[i]) * 0.002;
    const pitch = (0.42 + 0.58 * ss(0.16, 1, slow)) * dopS[i] * (i ? 1.06 : 1);
    const f = (rpm / 60) * 4 * pitch;
    phase[i] = (phase[i] + f / SR) % 1; sub[i] = (sub[i] + f / 2 / SR) % 1;
    let s = 0;
    for (let k = 1; k <= 9; k++) s += Math.sin(2 * Math.PI * phase[i] * k) / (k ** 1.15);
    s += 0.7 * Math.sin(2 * Math.PI * sub[i]) + 0.25 * Math.sin(4 * Math.PI * sub[i] + 0.6);
    const load = clamp(0.55 + car.acc / 40, 0.3, 1);
    s = Math.tanh(s * (1.2 + load * 1.6)) * cut;
    s += intake[i](rnd(), f * 3.1, 4) * 0.9 * load;
    // pops & crackles on shifts and lift-off
    if ((sinceShift < 0.12 || car.acc < -8) && rnd() > 0.9965) s += rnd() * 3;
    const dist = car.dist;
    const g = (1 / (1 + dist / 14)) * (car.air > 0.5 ? 0.85 : 1) * (t < TL.T_GO ? 0.75 : 1);
    gainS[i] += (g - gainS[i]) * 0.003; panS[i] += (car.pan - panS[i]) * 0.003;
    const amp = 0.16 * gainS[i] * (0.4 + 0.6 * ss(0.16, 0.9, slow));
    mix(n, s * amp * (1 - 0.6 * Math.max(0, panS[i])), s * amp * (1 + 0.6 * Math.min(0, panS[i])) );
  }
}

// ---------- wind / rush
{
  const lp = onePole(), bp = biquadBP();
  for (let n = 0; n < N; n++) {
    const t = n / SR, c = ctlAt(t);
    const v = Math.max(c.cars[0].v, c.cars[1].v) / TL.VMAX_DISPLAY;
    const cs = clamp(c.camSpeed / TL.VMAX_DISPLAY, 0, 1.5);
    const w = lp(rnd(), 900 + 2500 * cs) * (0.05 * v * v + 0.09 * cs * cs) * c.rate;
    const hiss = bp(rnd(), 2500 + 3000 * cs, 0.8) * 0.02 * cs;
    mix(n, w + hiss, w - hiss);
  }
}

// ---------- score: 140 bpm synthwave
const BPM = 140, BEAT = 60 / BPM, T0 = TL.T_GO;
// music is muted during the jump and finish slow-mo, then slams back in
const musicGain = (t) => {
  if (t < T0) return 0;
  const jumpOut = 1 - ss(39.45, 39.7, t) * (1 - ss(43.25, 43.4, t));
  const finOut = 1 - ss(54.0, 54.3, t) * (1 - ss(56.55, 56.7, t));
  return jumpOut * finOut * (1 - ss(58.5, 60, t) * 0.9);
};
const ROOTS = [45, 41, 43, 40]; // A1 F1 G1 E1 (midi-ish semitone index from A0=21 base)
const midi = (m) => 440 * Math.pow(2, (m - 69) / 12);
{
  const bassLp = onePole(), arpLp = onePole();
  let bassPh = 0, arpPh = 0, kickPh = 0;
  for (let n = 0; n < N; n++) {
    const t = n / SR, g = musicGain(t);
    if (g <= 0) { bassLp(0, 400); continue; }
    const bt = (t - T0) / BEAT, beat = Math.floor(bt), fb = bt - beat;
    const bar = Math.floor(beat / 4), root = ROOTS[bar % 4] + 12;
    // kick
    const kt = fb * BEAT; kickPh += (45 + 110 * Math.exp(-kt * 30)) / SR;
    const kick = Math.sin(2 * Math.PI * kickPh) * Math.exp(-kt * 9) * 0.55;
    // offbeat-pumped rolling bass (16ths)
    const s16 = (bt * 4) % 1, pump = Math.min(1, fb * 4);
    bassPh = (bassPh + midi(root) / SR) % 1;
    const saw = 2 * bassPh - 1 + (2 * ((bassPh * 2.003) % 1) - 1) * 0.5;
    const bass = bassLp(saw, 180 + 900 * Math.exp(-s16 * 6)) * 0.22 * pump * Math.exp(-s16 * 2.5);
    // arpeggio (minor triad over two octaves), enters after the launch
    const arpNotes = [0, 3, 7, 12, 15, 19, 15, 12];
    const step = Math.floor(bt * 4) % 8;
    arpPh = (arpPh + midi(root + 24 + arpNotes[step]) / SR) % 1;
    const sq = (arpPh < 0.5 ? 1 : -1);
    const arp = arpLp(sq, 2400) * 0.05 * Math.exp(-s16 * 3) * ss(7.5, 9, t);
    // hats
    const hat = rnd() * Math.exp(-((bt * 2) % 1) * 40) * 0.05 * ss(5, 6, t);
    const m = (kick + bass + arp) * g;
    mix(n, m + hat * g * 0.7, m + hat * g);
  }
}

// ---------- one-shots
function boom(at, gain = 1, f0 = 60) {
  for (let n = Math.floor(at * SR), k = 0; k < SR * 1.6 && n < N; n++, k++) {
    const t = k / SR, s = Math.sin(2 * Math.PI * (f0 * t + 40 * (1 - Math.exp(-t * 20)) / 20)) * Math.exp(-t * 2.4) * 0.6 * gain;
    const crack = rnd() * Math.exp(-t * 25) * 0.4 * gain;
    mix(n, s + crack, s + crack);
  }
}
function whoosh(at, gain = 1, dur = 0.35, up = false) {
  const bp = biquadBP();
  for (let n = Math.floor(at * SR), k = 0; k < SR * dur && n < N; n++, k++) {
    const u = k / (SR * dur), f = up ? 300 + 5000 * u * u : 5000 * Math.pow(1 - u, 2) + 300;
    const e = Math.sin(Math.PI * u) ** 2;
    const s = bp(rnd(), f, 1.2) * e * 0.35 * gain;
    mix(n, s * (1 - u * 0.5), s * (0.5 + u * 0.5));
  }
}
function beep(at, f, dur, gain = 0.18) {
  for (let n = Math.floor(at * SR), k = 0; k < SR * dur && n < N; n++, k++) {
    const t = k / SR, e = Math.min(1, t * 200) * Math.min(1, (dur - t) * 60);
    const s = Math.sign(Math.sin(2 * Math.PI * f * t)) * 0.5 * e * gain + Math.sin(2 * Math.PI * f * t) * e * gain;
    mix(n, s, s);
  }
}
// countdown lights + GO
for (let k = 0; k < 5; k++) beep(0.6 + k * 0.62, 660, 0.16);
beep(TL.T_GO, 1320, 0.55, 0.22);
boom(TL.T_GO, 1.2, 42);
// camera cuts
for (const c of TL.CUTS) whoosh(c - 0.12, c > 44 && c < 52.2 ? 0.8 : 0.6, 0.3);
// riser into the ramp, then silence, takeoff boom, heartbeat, landing slam
{
  const bp = biquadBP(), a = 35.2, b = 39.5;
  for (let n = Math.floor(a * SR); n < b * SR; n++) {
    const u = (n / SR - a) / (b - a), s = bp(rnd(), 200 + 6000 * u * u, 2) * u * u * 0.5;
    const tone = Math.sin(2 * Math.PI * (110 * Math.pow(4, u)) * (n / SR)) * 0.06 * u;
    mix(n, s + tone, s + tone);
  }
}
boom(39.62, 1.4, 36);
for (let k = 0; k < 3; k++) { boom(40.5 + k * 0.85, 0.45, 48); boom(40.5 + k * 0.85 + 0.22, 0.3, 44); }
for (const l of TL.LANDING_T) if (l.peak > 2) { boom(l.t, l.t > 30 ? 1.5 : 0.9, 40); }
// finish line: slam + crowd roar
const fT = TL.FINISH_T[TL.WINNER];
boom(fT, 1.6, 38);
whoosh(fT - 0.4, 1.2, 0.6, true);
{
  const bp = biquadBP(), bp2 = biquadBP();
  for (let n = 0; n < N; n++) {
    const t = n / SR;
    const near = Math.exp(-(((t - 1.5) / 3) ** 2)) * 0.5 + ss(fT - 0.3, fT + 0.4, t) * (1 - ss(58, 60, t)) * 1.3 + Math.exp(-(((t - 28.5) / 1.2) ** 2)) * 0.6;
    if (near < 0.01) continue;
    const s = (bp(rnd(), 900 + 300 * Math.sin(t * 7), 0.7) + bp2(rnd(), 2200, 1.5) * 0.5) * 0.12 * near;
    mix(n, s * (1 + 0.2 * Math.sin(t * 3)), s * (1 - 0.2 * Math.sin(t * 3)));
  }
}

// ---------- master: fade, soft clip, normalise
let peak = 0;
for (let n = 0; n < N; n++) {
  const t = n / SR, fade = Math.min(1, t / 0.3) * (1 - ss(59.2, 60, t));
  L[n] = Math.tanh(L[n] * 1.4 * fade); R[n] = Math.tanh(R[n] * 1.4 * fade);
  peak = Math.max(peak, Math.abs(L[n]), Math.abs(R[n]));
}
const norm = 0.89 / peak;
const buf = Buffer.alloc(44 + N * 4);
buf.write('RIFF', 0); buf.writeUInt32LE(36 + N * 4, 4); buf.write('WAVEfmt ', 8);
buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22); buf.writeUInt32LE(SR, 24);
buf.writeUInt32LE(SR * 4, 28); buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34); buf.write('data', 36); buf.writeUInt32LE(N * 4, 40);
for (let n = 0; n < N; n++) {
  buf.writeInt16LE(Math.round(clamp(L[n] * norm, -1, 1) * 32767), 44 + n * 4);
  buf.writeInt16LE(Math.round(clamp(R[n] * norm, -1, 1) * 32767), 46 + n * 4);
}
writeFileSync(out, buf);
console.log(`wrote ${out} (${TL.DURATION}s, peak ${peak.toFixed(2)})`);

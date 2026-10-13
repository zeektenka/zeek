// Midnight Circuit — deterministic race script.
// Pure math (no three.js) so the browser renderer and the Node audio
// synthesiser read exactly the same track, cars, slow-mo and camera.

export const DURATION = 60;
export const FPS = 30;

// ---------------------------------------------------------------- math
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const lerp = (a, b, t) => a + (b - a) * t;
export const smoothstep = (e0, e1, x) => { const t = clamp((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t); };
const ease = (t) => { t = clamp(t, 0, 1); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const easeOut = (t) => 1 - Math.pow(1 - clamp(t, 0, 1), 3);
const easeIn = (t) => Math.pow(clamp(t, 0, 1), 3);
const mod = (a, n) => ((a % n) + n) % n;

export const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
export const madd = (a, b, s) => [a[0] + b[0] * s, a[1] + b[1] * s, a[2] + b[2] * s];
export const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
export const len = (a) => Math.hypot(a[0], a[1], a[2]);
export const norm = (a) => { const l = len(a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
const mix3 = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
// rotate v around unit axis k by angle a (Rodrigues)
const rot = (v, k, a) => {
  const c = Math.cos(a), s = Math.sin(a);
  return add(add(mul(v, c), mul(cross(k, v), s)), mul(k, dot(k, v) * (1 - c)));
};

// deterministic hash / smooth noise
export const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
const noise1 = (t, seed = 0) =>
  Math.sin(t * 1.0 + seed) * 0.5 + Math.sin(t * 2.31 + seed * 1.7) * 0.3 + Math.sin(t * 5.13 + seed * 2.9) * 0.2;

// cubic Hermite through keys [[x, y], ...] with finite-difference tangents
function makeCurve(keys) {
  const n = keys.length;
  const tan = keys.map((k, i) => {
    if (i === 0 || i === n - 1) return 0;
    return (keys[i + 1][1] - keys[i - 1][1]) / (keys[i + 1][0] - keys[i - 1][0]);
  });
  return (x) => {
    if (x <= keys[0][0]) return keys[0][1];
    if (x >= keys[n - 1][0]) return keys[n - 1][1];
    let i = 0;
    while (x > keys[i + 1][0]) i++;
    const [x0, y0] = keys[i], [x1, y1] = keys[i + 1], h = x1 - x0, u = (x - x0) / h;
    const u2 = u * u, u3 = u2 * u;
    return (2 * u3 - 3 * u2 + 1) * y0 + (u3 - 2 * u2 + u) * h * tan[i] + (-2 * u3 + 3 * u2) * y1 + (u3 - u2) * h * tan[i + 1];
  };
}

// ---------------------------------------------------------------- time warp (slow motion)
// [start, end, rate] in real seconds
export const WARPS = [
  [3.95, 5.2, 0.32],   // launch
  [39.5, 43.7, 0.25],  // the jump
  [54.15, 55.75, 0.16], // photo finish
];
const RAMP = 0.35;
export function rateAt(t) {
  let r = 1;
  for (const [a, b, k] of WARPS) {
    const w = smoothstep(a - RAMP, a, t) * (1 - smoothstep(b, b + RAMP, t));
    r -= (1 - k) * w;
  }
  return r;
}
const WDT = 1 / 600;
const TAU = new Float64Array(Math.ceil((DURATION + 2) / WDT) + 2);
for (let i = 1; i < TAU.length; i++) TAU[i] = TAU[i - 1] + rateAt((i - 0.5) * WDT) * WDT;
export function tauOf(t) {
  const x = clamp(t, 0, DURATION + 1.9) / WDT, i = Math.floor(x);
  return lerp(TAU[i], TAU[i + 1], x - i);
}
export function tOfTau(tau) {
  let lo = 0, hi = TAU.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (TAU[m] < tau) lo = m; else hi = m; }
  return (lo + (tau - TAU[lo]) / (TAU[hi] - TAU[lo] || 1)) * WDT;
}

// ---------------------------------------------------------------- track (centerline in xz)
const CTRL = [
  [0, 0], [170, 0], [340, 0], [450, -30], [480, -120], [430, -200], [340, -220],
  [275, -270], [290, -350], [240, -430], [110, -455], [-60, -450], [-240, -440],
  [-360, -400], [-410, -310], [-380, -215], [-300, -170], [-320, -90], [-260, -15], [-140, 0],
];
const TRACK_SCALE = 0.66;

function catmull(p0, p1, p2, p3, u) {
  const tj = (a, b) => Math.pow(Math.hypot(b[0] - a[0], b[1] - a[1]), 0.5) || 1e-4;
  const t0 = 0, t1 = t0 + tj(p0, p1), t2 = t1 + tj(p1, p2), t3 = t2 + tj(p2, p3);
  const T = t1 + (t2 - t1) * u;
  const L = (a, b, ta, tb) => [((tb - T) * a[0] + (T - ta) * b[0]) / (tb - ta), ((tb - T) * a[1] + (T - ta) * b[1]) / (tb - ta)];
  const A1 = L(p0, p1, t0, t1), A2 = L(p1, p2, t1, t2), A3 = L(p2, p3, t2, t3);
  const B1 = L(A1, A2, t0, t2), B2 = L(A2, A3, t1, t3);
  return L(B1, B2, t1, t2);
}

const dense = [];
{
  const P = CTRL.map(([x, z]) => [x * TRACK_SCALE, z * TRACK_SCALE]), n = P.length;
  for (let i = 0; i < n; i++) {
    const p0 = P[mod(i - 1, n)], p1 = P[i], p2 = P[mod(i + 1, n)], p3 = P[mod(i + 2, n)];
    for (let k = 0; k < 400; k++) dense.push(catmull(p0, p1, p2, p3, k / 400));
  }
  dense.push(dense[0]);
}
const cum = [0];
for (let i = 1; i < dense.length; i++) cum.push(cum[i - 1] + Math.hypot(dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]));
export const TRACK_LENGTH = cum[cum.length - 1];
const L = TRACK_LENGTH;
const NS = Math.round(L);           // ~1 unit resolution
export const DS = L / NS;
const TX = new Float64Array(NS + 1), TZ = new Float64Array(NS + 1);
{
  let j = 0;
  for (let i = 0; i <= NS; i++) {
    const s = i * DS;
    while (j < cum.length - 2 && cum[j + 1] < s) j++;
    const f = (s - cum[j]) / (cum[j + 1] - cum[j] || 1);
    TX[i] = lerp(dense[j][0], dense[j + 1][0], f);
    TZ[i] = lerp(dense[j][1], dense[j + 1][1], f);
  }
}
const HEAD = new Float64Array(NS);
for (let i = 0; i < NS; i++) {
  const a = mod(i - 1, NS), b = mod(i + 1, NS);
  HEAD[i] = Math.atan2(TZ[b] - TZ[a], TX[b] - TX[a]);
}
const angDiff = (a, b) => mod(a - b + Math.PI, Math.PI * 2) - Math.PI;
const boxSmooth = (arr, r) => {
  const out = new Float64Array(arr.length), n = arr.length;
  for (let i = 0; i < n; i++) { let s = 0; for (let k = -r; k <= r; k++) s += arr[mod(i + k, n)]; out[i] = s / (2 * r + 1); }
  return out;
};
const KRAW = new Float64Array(NS);
for (let i = 0; i < NS; i++) KRAW[i] = angDiff(HEAD[mod(i + 4, NS)], HEAD[mod(i - 4, NS)]) / (8 * DS);
const KAPPA = boxSmooth(KRAW, 10);      // signed curvature, >0 = turning right
const KAPPA_WIDE = boxSmooth(KRAW, 45); // for racing line anticipation

const sampleArr = (arr, s) => {
  const x = mod(s, L) / DS, i = Math.floor(x) % NS, f = x - Math.floor(x);
  return lerp(arr[i], arr[(i + 1) % NS], f);
};
export const kappaAt = (s) => sampleArr(KAPPA, s);
function xzAt(s) {
  const x = mod(s, L) / DS, i = Math.floor(x), f = x - i;
  return [lerp(TX[i], TX[i + 1], f), lerp(TZ[i], TZ[i + 1], f)];
}
function headAt(s) {
  const x = mod(s, L) / DS, i = Math.floor(x) % NS, f = x - Math.floor(x);
  const a = HEAD[i], b = HEAD[(i + 1) % NS];
  return a + angDiff(b, a) * f;
}

// ---------------------------------------------------------------- race progress (speed from curvature)
const VTOP = 92, ALAT = 40, BRAKE = 30, ACC = 24;
const SDT = 1 / 240;
export const TAU_GO = tauOf(4.0);
export const TAU_END = tauOf(DURATION) + 1;
const NT = Math.ceil(TAU_END / SDT) + 2;
export const FINISH_S = 2 * L; // two laps
export const LAPS = 2;

const EXT = Math.ceil((2 * L + 1200) / DS);
function brakeProfile(k) {
  const vb = new Float64Array(EXT);
  for (let i = 0; i < EXT; i++) {
    const kap = Math.abs(KAPPA[i % NS]);
    vb[i] = k * Math.min(VTOP, Math.sqrt(ALAT / Math.max(kap, 1e-5)));
  }
  for (let i = EXT - 2; i >= 0; i--) vb[i] = Math.min(vb[i], Math.sqrt(vb[i + 1] * vb[i + 1] + 2 * BRAKE * k * DS));
  return vb;
}
function simProgress(k) {
  const vb = brakeProfile(k);
  const M = new Float64Array(NT), Vv = new Float64Array(NT);
  let m = 0, v = 0;
  for (let i = 0; i < NT; i++) {
    const tau = i * SDT;
    if (tau >= TAU_GO) {
      if (m < FINISH_S) {
        const a = ACC * Math.max(0.12, 1 - v / (k * VTOP * 1.05));
        v = Math.min(v + a * SDT, vb[Math.min(EXT - 1, Math.floor(m / DS))]);
      } else v = Math.max(16, v - 14 * SDT);
    }
    M[i] = m; Vv[i] = v;
    m += v * SDT;
  }
  return { M, Vv };
}
const lookup = (arr, tau) => {
  const x = clamp(tau / SDT, 0, NT - 1.001), i = Math.floor(x);
  return lerp(arr[i], arr[i + 1], x - i);
};
// pick a speed scale so the leader crosses the line (2 laps) at t ≈ 54.9
export const T_FINISH_TARGET = 54.95;
let K_SPEED;
let PROG;
{
  const target = tauOf(T_FINISH_TARGET);
  let lo = 0.4, hi = 3;
  for (let it = 0; it < 40; it++) {
    const k = (lo + hi) / 2;
    const p = simProgress(k);
    if (lookup(p.M, target) > FINISH_S) hi = k; else lo = k;
  }
  K_SPEED = (lo + hi) / 2;
  PROG = simProgress(K_SPEED);
}
export const SPEED_SCALE = K_SPEED;
export const meanS = (tau) => lookup(PROG.M, tau);
export const meanV = (tau) => lookup(PROG.Vv, tau);

// jump lip goes wherever the pack is at t = 40.0 on lap two
export const JUMP_S = mod(meanS(tauOf(40.05)), L);

// ---------------------------------------------------------------- elevation
const wrapD = (a, b) => mod(a - b + L / 2, L) - L / 2;
export const JUMP_H = 6.5;
const RAMP_LEN = 75, PLATEAU = 4.6;
export function elev(s) {
  s = mod(s, L);
  const u = (s / L) * Math.PI * 2;
  let h = 3.0 + 1.7 * Math.sin(u * 3 + 0.7) + 0.9 * Math.sin(u * 5 + 2.1);
  const dJ = wrapD(s, JUMP_S), d0 = wrapD(s, 0);
  const w = smoothstep(120, 260, Math.abs(d0)) * smoothstep(240, 380, Math.abs(dJ));
  h *= w;
  if (dJ > -RAMP_LEN && dJ <= 0) {
    const x = (dJ + RAMP_LEN) / RAMP_LEN;
    h += JUMP_H * x * x;
  } else if (dJ > 0 && dJ < 18) {
    // short kicker drop-off onto the landing plateau
    const x = dJ / 18, m0 = (2 * JUMP_H / RAMP_LEN) * 18, m1 = -0.04 * 18;
    h += (2 * x ** 3 - 3 * x * x + 1) * JUMP_H + (x ** 3 - 2 * x * x + x) * m0 + (-2 * x ** 3 + 3 * x * x) * PLATEAU + (x ** 3 - x * x) * m1;
  } else if (dJ >= 18 && dJ < 240) {
    h += PLATEAU * (1 - smoothstep(18, 240, dJ)) - 0.04 * 18 * (1 - smoothstep(18, 40, dJ)) * 0;
  }
  return h;
}
export const elevD = (s) => (elev(s + 0.25) - elev(s - 0.25)) / 0.5;
export const bankAt = (s) => clamp(sampleArr(KAPPA, s) * 260, -0.17, 0.17);

export function trackFrame(s) {
  const [x, z] = xzAt(s), th = headAt(s), h = elev(s), dh = elevD(s);
  const T = norm([Math.cos(th), dh, Math.sin(th)]);
  const R0 = norm(cross(T, [0, 1, 0]));
  const U0 = cross(R0, T);
  const b = bankAt(s), cb = Math.cos(b), sb = Math.sin(b);
  const U = add(mul(U0, cb), mul(R0, sb));
  const R = sub(mul(R0, cb), mul(U0, sb));
  return { p: [x, h, z], T, R, U, kappa: kappaAt(s), head: th };
}
export const trackPoint = (s, lat = 0, up = 0) => {
  const f = trackFrame(s);
  return madd(madd(f.p, f.R, lat), f.U, up);
};

// ---------------------------------------------------------------- the duel: gap & lanes (keyed in real seconds)
// gap = sA - sB  (A = #07 red "VEGA", B = #23 cyan "KAI")
const GAP_KEYS = [
  [0, 0], [4, 0], [5.0, -0.5], [6.5, -2.5], [8.5, -6.5], [11, -9.5], [14, -9], [17, -7.5], [19.5, -5.2],
  [21.5, -2.6], [23, -0.8], [24.5, 1.6], [26, 4.6], [28, 7.6], [31, 9], [33, 8], [35.5, 4.2], [37.5, 1.4],
  [39.4, 0.3], [40.6, 0], [42.6, -1.1], [44.5, -3], [46.5, -4.6], [48.5, -4], [50.5, -2.2], [52.5, -0.7],
  [54, 0.1], [55, 0.9], [56.5, 2.2], [60, 4.5],
];
const LAT_KEYS = [ // t, A, B
  [0, -3, 3], [4.6, -3, 3], [6.6, -2.8, 2.8], [10, -0.4, 0.5], [12, 0.7, 0.6], [17, 0.8, 0.6],
  [19, -2.9, 1.0], [21, -3.1, 2.7], [26, -3, 2.8], [27.6, -1.2, 1.6], [29.5, 0.3, 0.2], [32, 0.4, -0.2],
  [34, 1.2, -1.6], [35.4, 2.8, -2.8], [57, 2.8, -2.8], [60, 1.6, -2.2],
];
const toTau = (keys) => keys.map((k) => [tauOf(k[0]), ...k.slice(1)]);
const gapCurve = makeCurve(toTau(GAP_KEYS));
const latA = makeCurve(toTau(LAT_KEYS).map((k) => [k[0], k[1]]));
const latB = makeCurve(toTau(LAT_KEYS).map((k) => [k[0], k[2]]));

export const CARS = [
  { name: 'VEGA', num: '07', color: 0xff1e3c, accent: 0xffd400, glow: 0xff2a6a },
  { name: 'KAI', num: '23', color: 0x08c8ff, accent: 0xe8f4ff, glow: 0x00e5ff },
];
export const carS = (i, tau) => meanS(tau) + (i === 0 ? 0.5 : -0.5) * gapCurve(tau);
export const carV = (i, tau) => (carS(i, tau + 0.01) - carS(i, tau - 0.01)) / 0.02;
export function carLat(i, tau) {
  const s = carS(i, tau);
  const apex = clamp(sampleArr(KAPPA_WIDE, s + 25) * 170, -2.2, 2.2) * smoothstep(TAU_GO + 2, TAU_GO + 5, tau);
  return clamp((i === 0 ? latA(tau) : latB(tau)) + apex, -6.4, 6.4);
}

// ---------------------------------------------------------------- vertical physics (airtime, suspension, pitch)
const G = 40;
export const LANDINGS = []; // {car, tau, impact}
const VERT = [0, 1].map((ci) => {
  const AIR = new Float32Array(NT), SUS = new Float32Array(NT), PIT = new Float32Array(NT);
  let s = carS(ci, 0), y = elev(s), vy = 0, air = false, c = 0, cv = 0, pAbs = Math.atan(elevD(s)), vPrev = 0, peak = 0;
  for (let i = 0; i < NT; i++) {
    const tau = i * SDT;
    const sN = carS(ci, tau + SDT), v = (sN - s) / SDT, gN = elev(sN), slope = elevD(sN);
    const acc = (v - vPrev) / SDT; vPrev = v;
    vy -= G * SDT;
    let yN = y + vy * SDT;
    if (yN <= gN) {
      const gVy = (gN - elev(s)) / SDT;
      if (air) {
        const impact = gVy - vy;
        if (impact > 3) LANDINGS.push({ car: ci, tau, impact, peak });
        peak = 0;
        cv += impact * 0.55;
      }
      yN = gN; vy = gVy; air = false;
    } else if (yN - gN > 0.04) air = true;
    // suspension spring (c > 0 = compressed)
    const ca = -190 * c - 15 * cv + (air ? -6 : 0);
    cv += ca * SDT; c += cv * SDT;
    c = clamp(c, -0.18, 0.32);
    const roadPitch = Math.atan(slope);
    if (air) pAbs += (Math.atan2(vy, Math.max(v, 1)) * 0.45 - pAbs) * Math.min(1, SDT * 1.6);
    else pAbs = roadPitch - clamp(acc, -40, 40) * 0.0012;
    y = yN; s = sN;
    if (air) peak = Math.max(peak, y - gN);
    AIR[i] = Math.max(0, y - gN); SUS[i] = c; PIT[i] = pAbs - roadPitch;
  }
  return { AIR, SUS, PIT };
});

// ---------------------------------------------------------------- car pose
export function carPose(i, tau) {
  const s = carS(i, tau), v = carV(i, tau), lat = carLat(i, tau);
  const f = trackFrame(s);
  const dlat = (carLat(i, tau + 0.03) - carLat(i, tau - 0.03)) / 0.06;
  const psi = clamp(Math.atan2(dlat, Math.max(v, 4)), -0.3, 0.3);
  const air = lookup(VERT[i].AIR, tau), susp = lookup(VERT[i].SUS, tau), pitch = lookup(VERT[i].PIT, tau);
  const roll = clamp(-v * v * f.kappa * 0.0011, -0.07, 0.07);
  const cp = Math.cos(psi), sp = Math.sin(psi);
  let fwd = add(mul(f.T, cp), mul(f.R, sp));
  let right = sub(mul(f.R, cp), mul(f.T, sp));
  let up = f.U;
  const cph = Math.cos(pitch), sph = Math.sin(pitch);
  const fwd2 = add(mul(fwd, cph), mul(up, sph));
  const up2 = sub(mul(up, cph), mul(fwd, sph));
  const cr = Math.cos(roll), sr = Math.sin(roll);
  const up3 = add(mul(up2, cr), mul(right, sr));
  const right3 = sub(mul(right, cr), mul(up2, sr));
  const pos = madd(madd(f.p, f.R, lat), [0, 1, 0], air);
  const acc = (carV(i, tau + 0.05) - carV(i, tau - 0.05)) / 0.1;
  return { pos, fwd: fwd2, up: up3, right: right3, left: mul(right3, -1), v, s, lat, air, susp, acc, steer: psi, frame: f };
}
// point in a car's local frame: x = left, y = up, z = forward
export const local = (P, x, y, z) => madd(madd(madd(P.pos, P.left, x), P.up, y), P.fwd, z);
const mid = (A, B) => ({ ...A, pos: mix3(A.pos, B.pos, 0.5), fwd: norm(add(A.fwd, B.fwd)), left: norm(add(A.left, B.left)), up: norm(add(A.up, B.up)) });

// gears / rpm (shared with audio + exhaust pops)
const GEAR_TOP = [0, 0.27, 0.42, 0.56, 0.7, 0.83, 0.95, 9].map((g) => g * VTOP * K_SPEED);
export function gearRpm(v) {
  let g = 1;
  while (g < 7 && v > GEAR_TOP[g]) g++;
  const lo = g === 1 ? 0 : GEAR_TOP[g - 1] * 0.97, hi = GEAR_TOP[g];
  const u = clamp((v - lo) / (hi - lo), 0, 1.05);
  return { gear: g, rpm: lerp(g === 1 ? 2600 : 5200, 8800, u) };
}
export const VMAX_DISPLAY = VTOP * K_SPEED;
export const kmh = (v) => Math.round((v / (VTOP * K_SPEED)) * 338);

// ---------------------------------------------------------------- events
export const T_GO = 4.0;
const finishTau = (i) => { let lo = TAU_GO, hi = TAU_END; for (let k = 0; k < 50; k++) { const m = (lo + hi) / 2; if (carS(i, m) > FINISH_S) hi = m; else lo = m; } return (lo + hi) / 2; };
export const FINISH_TAU = [finishTau(0), finishTau(1)];
export const FINISH_T = FINISH_TAU.map(tOfTau);
export const WINNER = FINISH_TAU[0] < FINISH_TAU[1] ? 0 : 1;
export const LANDING_T = LANDINGS.map((l) => ({ ...l, t: tOfTau(l.tau) }));
const bigLandings = LANDING_T.filter((l) => l.peak > 2);

// ---------------------------------------------------------------- cinematography
const FRENZY = [44.2, 45.15, 46.05, 46.95, 47.8, 48.7, 49.55, 50.45, 51.3, 52.1];
export const CUTS = [4.2, 7.6, 11.6, 15.4, 17.3, 19.4, 23.0, 27.0, 29.0, 31.0, 35.0, 39.3, ...FRENZY.slice(0, -1), 52.1, 53.95, 56.6];

function shake(t, amp, freq = 1, seed = 0) {
  if (amp <= 0) return [0, 0, 0];
  const x = t * freq * 6;
  return [noise1(x, seed + 1) * amp, noise1(x * 1.13, seed + 7) * amp, noise1(x * 0.91, seed + 13) * amp];
}

function shotAt(t) {
  const tau = tauOf(t);
  const A = carPose(0, tau), B = carPose(1, tau);
  const lead = A.s >= B.s ? A : B, trail = lead === A ? B : A;
  const M = mid(A, B);
  const at = (t0, t1) => ({ lt: t - t0, u: clamp((t - t0) / (t1 - t0), 0, 1) });
  const fixedAlong = (sx, lat, h) => trackPoint(sx, lat, h);

  // 1. Grid: swooping descent around the cars while the lights count down
  if (t < 4.2) {
    const { u } = at(0, 4.2), e = easeOut(u);
    const a = lerp(-2.6, -0.32, e), r = lerp(70, 7.5, e), h = lerp(42, 0.75, Math.pow(e, 0.8));
    const pos = madd(madd(madd(M.pos, M.fwd, Math.cos(a) * r), M.left, Math.sin(a) * r), [0, 1, 0], h);
    return { pos, target: madd(M.pos, [0, 1, 0], 0.7 + 3 * (1 - e)), fov: lerp(42, 62, e), roll: lerp(0.25, 0, e), shake: 0.02 + 0.05 * u * u, blur: 0 };
  }
  // 2. Launch: camera sits on the asphalt, cars rip away, rig chases
  if (t < 7.6) {
    const { lt } = at(4.2, 7.6);
    const G0 = carPose(0, TAU_GO), G1 = carPose(1, TAU_GO), GM = mid(G0, G1);
    const fixed = local(GM, 0, 0.45, -5.5);
    const chase = local(M, 0, 1.6, -10);
    const k = smoothstep(0.8, 2.6, lt);
    return { pos: mix3(fixed, chase, k), target: local(M, 0, 0.6, 6), fov: lerp(58, 78, smoothstep(0.4, 2, lt)), roll: Math.sin(lt * 2) * 0.05, shake: 0.12 * (1 - k * 0.5), blur: 0.06 + 0.08 * k };
  }
  // 3. Drone orbit around the leader
  if (t < 11.6) {
    const { lt, u } = at(7.6, 11.6);
    const a = Math.PI * 0.9 + lt * 1.55, r = 8.5 + 2 * Math.sin(lt * 1.7), h = 2.4 + 1.6 * Math.sin(lt * 1.25);
    const pos = madd(madd(madd(lead.pos, lead.fwd, Math.cos(a) * r), lead.left, Math.sin(a) * r), lead.up, h);
    return { pos, target: local(lead, 0, 0.6, 1.5), fov: 64, roll: Math.sin(lt * 2.2) * 0.22, shake: 0.05, blur: 0.08 + 0.04 * u };
  }
  // 4. Bumper cam on the leader looking back at the hunter
  if (t < 15.4) {
    const { lt } = at(11.6, 15.4);
    return { pos: local(B, 0.15, 1.05, -2.75), target: local(A, 0, 0.75 + 0.3 * Math.sin(lt), 0), fov: 70, roll: Math.sin(lt * 3) * 0.04, shake: 0.035, shakeFreq: 4, blur: 0.12 };
  }
  // 5. Helicopter: spinning top-down that drops toward the pack
  if (t < 17.3) {
    const { lt, u } = at(15.4, 17.3), e = easeIn(u);
    const h = lerp(80, 22, e), back = lerp(0.5, 6, e);
    const pos = madd(madd(M.pos, [0, 1, 0], h), M.fwd, -back);
    const spin = lt * 1.1;
    const up = add(mul(M.fwd, Math.cos(spin)), mul(M.left, Math.sin(spin)));
    return { pos, target: local(M, 0, 0.5, 2), up, fov: lerp(55, 66, e), shake: 0.03 + 0.06 * e, blur: 0.04 + 0.1 * e };
  }
  // 5b. Lap-one ramp: camera on the landing kerb, cars fly over it
  if (t < 19.4) {
    const { u } = at(17.3, 19.4);
    const pos = trackPoint(JUMP_S + 34, -8.6, 0.55);
    return { pos, target: madd(M.pos, [0, 1, 0], 0.6), fov: lerp(62, 74, u), shake: 0.02, blur: 0.05 };
  }
  // 6. Hood cam on the hunter (#07), closing on #23
  if (t < 23.0) {
    const { lt } = at(19.4, 23.0);
    return { pos: local(A, 0, 1.62, -0.35), target: local(A, -0.2 * Math.sin(lt), 1.1, 40), up: A.up, fov: 78, shake: 0.03, shakeFreq: 7, blur: 0.18 };
  }
  // 7. Side tracking telephoto: whip-in, then watch the overtake
  if (t < 27.0) {
    const { u } = at(23.0, 27.0), e = easeOut(u * 1.6);
    const pos = madd(madd(madd(M.pos, M.left, 13.5 - 1.5 * u), [0, 1, 0], 3.6 + 1.0 * u), M.fwd, lerp(40, -3, e));
    return { pos, target: local(M, 0, 0.6, lerp(-2, 3, u)), fov: lerp(38, 46, u), roll: lerp(-0.12, 0.05, e), shake: 0.04, blur: 0.06 + 0.1 * (1 - e) };
  }
  // 8a. Trackside whip-pan, low on the outside kerb
  if (t < 29.0) {
    const sx = carS(0, tauOf(28.15)) + 6;
    return { pos: fixedAlong(sx, 8.9, 0.5), target: local(M, 0, 0.6, 1), fov: 40, shake: 0.015, blur: 0.04 };
  }
  // 8b. Trackside high, cars blast under the camera
  if (t < 31.0) {
    const sx = carS(0, tauOf(30.15)) + 2;
    return { pos: fixedAlong(sx, -2.5, 7.5), target: local(M, 0, 0.3, 2), fov: 66, shake: 0.03, blur: 0.06 };
  }
  // 9. Barrel roll fly-through
  if (t < 35.0) {
    const { u } = at(31.0, 35.0), e = ease(u);
    const z = lerp(18, -12, e), h = 1.3 + 2.8 * Math.sin(Math.PI * u);
    const pos = madd(local(M, Math.sin(u * 6.28) * 1.2, h, z), [0, 0, 0], 0);
    const yaw = lerp(Math.PI, 0, smoothstep(0.25, 0.75, u));
    const dir = add(mul(M.fwd, Math.cos(yaw)), mul(M.left, Math.sin(yaw) * 0.6));
    return { pos, target: madd(pos, norm(dir), 10), fov: 74, roll: e * Math.PI * 2, shake: 0.03, blur: 0.15 };
  }
  // 10. Low chase into the ramp — dolly zoom, rising tension
  if (t < 39.3) {
    const { lt, u } = at(35.0, 39.3);
    return { pos: local(M, Math.sin(lt * 1.3) * 0.8, 0.75 + 0.4 * u, -7.5 + 2.5 * u), target: local(M, 0, 1.6 + 2 * u, 25), fov: lerp(58, 92, easeIn(u)), roll: Math.sin(lt * 0.9) * 0.08 * u, shake: 0.03 + 0.12 * u, shakeFreq: 3, blur: 0.08 + 0.2 * u };
  }
  // 11. The jump: bullet-time arc around both cars in the air
  if (t < 44.2) {
    const { u } = at(39.3, 44.2), e = ease(u);
    const a = lerp(1.15, -1.25, e), r = lerp(14, 8.5, e);
    const pos = madd(madd(madd(M.pos, M.fwd, Math.cos(a) * r), M.left, Math.sin(a) * r), [0, 1, 0], lerp(1.2, 3.6, e));
    return { pos, target: madd(M.pos, [0, 1, 0], 0.9), fov: 52, roll: Math.sin(u * Math.PI) * -0.18, shake: 0.01, blur: 0.02 };
  }
  // 12. Frenzy: rapid-fire cuts
  if (t < 52.1) {
    let k = 0; while (k < FRENZY.length - 2 && t >= FRENZY[k + 1]) k++;
    const lt = t - FRENZY[k], u = clamp(lt / (FRENZY[k + 1] - FRENZY[k]), 0, 1);
    switch (k) {
      case 0: return { pos: local(B, -1.3, 0.45, -1.1), target: local(B, -1.0, 0.35, 16), fov: 78, shake: 0.03, shakeFreq: 6, blur: 0.25 };
      case 1: return { pos: local(lead, 0, 0.5, lerp(13, 7, u)), target: local(M, 0, 0.6, 0), fov: 60, roll: lerp(-0.2, 0.2, u), shake: 0.05, blur: 0.18 };
      case 2: { const sp = lt * 2.4; return { pos: madd(M.pos, [0, 1, 0], 16 - 4 * u), target: M.pos, up: add(mul(M.fwd, Math.cos(sp)), mul(M.left, Math.sin(sp))), fov: 60, shake: 0.04, blur: 0.12 }; }
      case 3: return { pos: local(A, 0, 1.62, -0.35), target: local(A, 0, 1.1, 40), up: A.up, fov: 84, shake: 0.035, shakeFreq: 7, blur: 0.26 };
      case 4: { const a = lt * 2.6; return { pos: madd(madd(madd(M.pos, M.fwd, Math.cos(a) * 8), M.left, Math.sin(a) * 8), [0, 1, 0], 1.4), target: local(M, 0, 0.5, 0), fov: 66, roll: 0.15, shake: 0.04, blur: 0.16 }; }
      case 5: { const sx = carS(0, tauOf(FRENZY[5] + 0.5)) + 3; return { pos: fixedAlong(sx, -8.9, 0.55), target: local(M, 0, 0.6, 1), fov: 44, shake: 0.02, blur: 0.06 }; }
      case 6: return { pos: local(M, 0, 1.3, -8), target: local(M, 0, 0.7, 10), fov: 72, roll: Math.sin(lt * 5) * 0.35, shake: 0.08, blur: 0.22 };
      case 7: return { pos: local(B, -2.6, 0.7, lerp(-2, 1, u)), target: local(A, 0, 0.6, 1.5), fov: 62, shake: 0.04, shakeFreq: 4, blur: 0.2 };
      default: return { pos: local(M, 0, 0.8, lerp(10, 8, u)), target: local(M, 0, 0.6, 0), fov: 64, roll: lerp(0.3, -0.3, u), shake: 0.06, blur: 0.16 };
    }
  }
  // 13a. Front-quarter tracking into the line
  if (t < 53.95) {
    const { u } = at(52.1, 53.95);
    return { pos: local(M, -10 + 2 * u, 1.0, lerp(12, 7, u)), target: local(M, 0, 0.6, 0), fov: 50, roll: 0.06, shake: 0.06, blur: 0.18 };
  }
  // 13b. Photo-finish camera on the line
  if (t < 56.6) {
    const { u } = at(53.95, 56.6);
    const line = trackFrame(FINISH_S);
    const pos = madd(madd(madd(line.p, line.R, -8.6), [0, 1, 0], 5.2), line.T, lerp(-2.5, 1.0, u));
    const tgt = madd(madd(line.p, line.R, 0.6), line.T, lerp(-0.5, 3, smoothstep(0.55, 1, u)));
    return { pos, target: tgt, fov: lerp(50, 58, smoothstep(0.6, 1, u)), shake: 0.006, blur: 0 };
  }
  // 14. Victory: rise up and away from the winner
  {
    const { u } = at(56.6, 60), e = easeOut(u);
    const W = WINNER === 0 ? A : B;
    return { pos: madd(local(W, lerp(-5, -14, e), lerp(1.4, 26, e), lerp(6, -22, e)), [0, 0, 0], 0), target: local(W, 0, 0.6, 2), fov: 52, roll: lerp(0.12, 0, e), shake: 0.02 * (1 - u), blur: 0.04 };
  }
}

export function cameraAt(t) {
  const c = shotAt(t);
  const sh = shake(t, c.shake || 0, c.shakeFreq || 1, 0);
  const sh2 = shake(t, (c.shake || 0) * 0.6, c.shakeFreq || 1, 50);
  const pos = add(c.pos, sh), target = add(c.target, sh2);
  // roll around view axis
  const view = norm(sub(target, pos));
  let up = c.up || [0, 1, 0];
  if (Math.abs(dot(norm(up), view)) > 0.98) up = norm(add(up, [0.01, 0, 0.02]));
  if (c.roll) up = rot(up, view, c.roll);
  // flash on cuts, GO, landings and the line
  let flash = 0;
  for (const ct of CUTS) { const d = t - ct; if (d >= 0 && d < 0.35) flash = Math.max(flash, (t > 44 && t < 52.2 ? 0.55 : 0.35) * Math.exp(-d * 14)); }
  { const d = t - T_GO; if (d >= 0) flash = Math.max(flash, 0.7 * Math.exp(-d * 6)); }
  for (const l of bigLandings) { const d = t - l.t; if (d >= 0) flash = Math.max(flash, 0.35 * Math.exp(-d * 7)); }
  { const d = t - FINISH_T[WINNER]; if (d >= 0) flash = Math.max(flash, 0.55 * Math.exp(-d * 5)); }
  const fade = Math.max(1 - smoothstep(0, 0.8, t), smoothstep(58.7, 59.95, t));
  // zoom-blur scales with speed of the action
  const tau = tauOf(t), speed = meanV(tau) / VMAX_DISPLAY;
  const blur = (c.blur || 0) * (0.35 + 0.65 * speed) * (0.4 + 0.6 * rateAt(t)) + flash * 0.08;
  return { pos, target, up, fov: c.fov || 60, blur, ca: 0.002 + blur * 0.025, flash, fade, rate: rateAt(t), tau };
}

// ---------------------------------------------------------------- broadcast overlay state
export function hudAt(t) {
  const tau = tauOf(t);
  const sA = carS(0, tau), sB = carS(1, tau);
  const order = sA >= sB ? [0, 1] : [1, 0];
  const lapM = meanS(tau);
  const lap = clamp(Math.floor(lapM / L) + 1, 1, LAPS);
  const raceTime = Math.max(0, tau - TAU_GO);
  const gapT = Math.abs(sA - sB) / Math.max(meanV(tau), 10);
  let caption = null;
  const caps = [
    [5.2, 7.4, 'LAUNCH'], [17.7, 19.3, 'SEND IT'], [23.6, 26.6, 'OVERTAKE'], [37.2, 39.3, 'RAMP AHEAD'], [40.2, 43.6, 'AIRTIME'],
    [52.3, 53.95, 'FINAL STRAIGHT'], [54.3, 56.5, 'PHOTO FINISH'],
  ];
  for (const [a, b, txt] of caps) if (t >= a && t < b) caption = { text: txt, age: t - a, left: b - t };
  const lightsOn = t < 0.6 ? 0 : t >= T_GO ? -1 : Math.min(5, Math.floor((t - 0.6) / 0.62) + 1);
  return {
    show: t >= 4.4 && t < 57.2,
    title: Math.max(0, 1 - smoothstep(2.6, 3.4, t)) * smoothstep(0.3, 1.0, t),
    lights: lightsOn,
    go: t >= T_GO && t < T_GO + 1.0 ? 1 - smoothstep(T_GO + 0.5, T_GO + 1.0, t) : 0,
    lap, laps: LAPS, raceTime,
    finished: [tau >= FINISH_TAU[0], tau >= FINISH_TAU[1]],
    order, gapT,
    speeds: [kmh(carV(0, tau)), kmh(carV(1, tau))],
    gears: [gearRpm(carV(0, tau)).gear, gearRpm(carV(1, tau)).gear],
    caption,
    slowmo: rateAt(t) < 0.6,
    winner: t >= 56.7 ? smoothstep(56.7, 57.4, t) : 0,
    winnerName: CARS[WINNER].name, winnerNum: CARS[WINNER].num,
    margin: Math.abs(FINISH_TAU[0] - FINISH_TAU[1]),
  };
}

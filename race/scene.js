// Midnight Circuit — three.js scene. Everything is a pure function of the
// film time t, so it can be scrubbed, played live, or rendered frame by frame.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import * as TL from './timeline.js';

const L = TL.TRACK_LENGTH;
const v3 = (a) => new THREE.Vector3(a[0], a[1], a[2]);
const hdr = (hex, k) => new THREE.Color(hex).multiplyScalar(k);

function rng(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function canvasTex(w, h, draw, { repeat = true, srgb = true } = {}) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}
function setBasis(obj, x, y, z) {
  const m = new THREE.Matrix4().makeBasis(v3(x), v3(y), v3(z));
  obj.quaternion.setFromRotationMatrix(m);
}

// ribbon along the track between two edge functions edge(s) -> [x,y,z]
function strip(edgeA, edgeB, vScale, step = 2) {
  const n = Math.round(L / step), pos = [], uv = [], idx = [];
  for (let i = 0; i <= n; i++) {
    const s = (i / n) * L, a = edgeA(s), b = edgeB(s);
    pos.push(...a, ...b);
    uv.push(0, s / vScale, 1, s / vScale);
    if (i < n) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

// ------------------------------------------------------------------ textures
function roadTextures() {
  const W = 256, H = 1024; // 16 units across x 40 units along
  const R = rng(7);
  const map = canvasTex(W, H, (g) => {
    g.fillStyle = '#26262c'; g.fillRect(0, 0, W, H);
    for (let i = 0; i < 26000; i++) {
      const v = 20 + R() * 40; g.fillStyle = `rgb(${v},${v},${v + 4})`;
      g.fillRect(R() * W, R() * H, 1.2, 1.2);
    }
    // rubbered-in racing line + skid marks
    for (let i = 0; i < 14; i++) {
      g.strokeStyle = `rgba(0,0,0,${0.12 + R() * 0.2})`; g.lineWidth = 3 + R() * 4;
      const x = W * (0.25 + R() * 0.5); g.beginPath(); g.moveTo(x, R() * H);
      g.lineTo(x + (R() - 0.5) * 30, R() * H); g.stroke();
    }
    g.fillStyle = '#e8e8e8';
    g.fillRect(6, 0, 5, H); g.fillRect(W - 11, 0, 5, H);
    for (let k = 0; k < 4; k++) g.fillRect(W / 2 - 3, k * (H / 4), 6, H / 8);
  });
  const glow = canvasTex(W, H, (g) => {
    g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
    const pool = (x, y) => {
      g.save(); g.translate(x, y); g.scale(1, 1.6);
      const gr = g.createRadialGradient(0, 0, 0, 0, 0, W * 0.62);
      gr.addColorStop(0, 'rgba(255,190,120,0.95)'); gr.addColorStop(0.45, 'rgba(255,150,80,0.32)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = gr; g.fillRect(-W, -W, 2 * W, 2 * W); g.restore();
    };
    g.globalCompositeOperation = 'lighter';
    pool(W * 0.12, 0); pool(W * 0.12, H); pool(W * 0.88, H / 2);
  });
  return { map, glow };
}

// ------------------------------------------------------------------ car
function makeCar(def, envMap) {
  const car = new THREE.Group();
  const body = new THREE.Group();
  car.add(body);
  const paint = new THREE.MeshPhysicalMaterial({ color: def.color, metalness: 0.55, roughness: 0.28, clearcoat: 1, clearcoatRoughness: 0.08, envMap, envMapIntensity: 0.55 });
  const carbon = new THREE.MeshStandardMaterial({ color: 0x0b0b0f, metalness: 0.4, roughness: 0.45, envMap, envMapIntensity: 0.3 });
  const glass = new THREE.MeshStandardMaterial({ color: 0x05070c, metalness: 0.95, roughness: 0.06, envMap, envMapIntensity: 1.1 });
  const accent = new THREE.MeshStandardMaterial({ color: def.accent, metalness: 0.3, roughness: 0.35, envMap, envMapIntensity: 0.4 });

  const profile = new THREE.Shape();
  [[2.36, 0.3], [2.34, 0.52], [1.9, 0.62], [1.1, 0.74], [0.5, 0.8], [-0.4, 0.86], [-1.5, 0.9], [-2.28, 0.92], [-2.34, 0.62], [-2.26, 0.3], [-1.8, 0.2], [1.9, 0.2]]
    .forEach(([x, y], i) => (i ? profile.lineTo(x, y) : profile.moveTo(x, y)));
  const extrude = (shape, depth, bevel) => {
    const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 4, steps: 1, curveSegments: 8 });
    g.rotateY(-Math.PI / 2); g.translate(depth / 2, 0, 0);
    return g;
  };
  body.add(new THREE.Mesh(extrude(profile, 1.82, 0.09), paint));
  const stripe = new THREE.Mesh(extrude(profile, 0.34, 0.09), accent);
  stripe.scale.set(1, 1.012, 1.004); stripe.position.y = -0.003;
  body.add(stripe);

  const cabin = new THREE.Shape();
  [[0.62, 0.8], [0.0, 1.2], [-0.95, 1.24], [-1.75, 0.92]].forEach(([x, y], i) => (i ? cabin.lineTo(x, y) : cabin.moveTo(x, y)));
  body.add(new THREE.Mesh(extrude(cabin, 1.38, 0.07), glass));

  const box = (w, h, d, mat, x, y, z) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat); m.position.set(x, y, z); body.add(m); return m; };
  box(2.1, 0.05, 0.42, carbon, 0, 1.3, -2.02);            // wing
  box(0.06, 0.3, 0.12, carbon, 0.55, 1.12, -1.95);
  box(0.06, 0.3, 0.12, carbon, -0.55, 1.12, -1.95);
  box(0.06, 0.32, 0.45, accent, 1.03, 1.22, -2.02);       // endplates
  box(0.06, 0.32, 0.45, accent, -1.03, 1.22, -2.02);
  box(2.05, 0.06, 0.5, carbon, 0, 0.2, 2.25);              // splitter
  box(1.7, 0.18, 0.3, carbon, 0, 0.3, -2.3);               // diffuser
  box(0.08, 0.1, 3.0, carbon, 1.0, 0.24, 0);               // side skirts
  box(0.08, 0.1, 3.0, carbon, -1.0, 0.24, 0);

  const headMat = new THREE.MeshBasicMaterial({ color: hdr(0xeaf4ff, 3.2) });
  for (const x of [-0.62, 0.62]) {
    const h = box(0.5, 0.06, 0.06, headMat, x, 0.56, 2.32);
    h.rotation.y = x > 0 ? 0.25 : -0.25;
  }
  const tailMat = new THREE.MeshBasicMaterial({ color: hdr(0xff1020, 3) });
  box(1.86, 0.06, 0.04, tailMat, 0, 0.8, -2.37);
  const exhaustMat = new THREE.MeshBasicMaterial({ color: 0x111111 });
  for (const x of [-0.42, 0.42]) { const e = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.12, 12), exhaustMat); e.rotation.x = Math.PI / 2; e.position.set(x, 0.36, -2.36); body.add(e); }

  // number roundels on the doors
  const numTex = canvasTex(256, 256, (g) => {
    g.fillStyle = '#fff'; g.beginPath(); g.arc(128, 128, 120, 0, 7); g.fill();
    g.fillStyle = '#000'; g.font = '900 150px Inter, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(def.num, 128, 138);
  }, { repeat: false });
  const numMat = new THREE.MeshStandardMaterial({ map: numTex, transparent: true, roughness: 0.4 });
  for (const side of [1, -1]) {
    const p = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.62), numMat);
    p.position.set(side * 1.002, 0.55, -0.25); p.rotation.y = side * Math.PI / 2;
    body.add(p);
  }
  const roof = new THREE.Mesh(new THREE.PlaneGeometry(0.7, 0.7), numMat);
  roof.rotation.x = -Math.PI / 2; roof.rotation.z = Math.PI; roof.position.set(0, 1.315, -0.45);
  body.add(roof);

  // wheels
  const tyre = new THREE.MeshStandardMaterial({ color: 0x111113, roughness: 0.85 });
  const rimMat = new THREE.MeshStandardMaterial({ color: 0xc8ccd4, metalness: 1, roughness: 0.25, envMap, envMapIntensity: 0.9 });
  const tyreGeo = new THREE.CylinderGeometry(0.37, 0.37, 0.34, 28); tyreGeo.rotateZ(Math.PI / 2);
  const rimGeo = new THREE.CylinderGeometry(0.25, 0.25, 0.35, 20); rimGeo.rotateZ(Math.PI / 2);
  const spokeGeo = new THREE.BoxGeometry(0.36, 0.44, 0.06);
  const wheels = [];
  for (const [x, z] of [[0.9, 1.42], [-0.9, 1.42], [0.92, -1.42], [-0.92, -1.42]]) {
    const pivot = new THREE.Group(); pivot.position.set(x, 0.37, z);
    const spin = new THREE.Group(); pivot.add(spin);
    spin.add(new THREE.Mesh(tyreGeo, tyre));
    spin.add(new THREE.Mesh(rimGeo, rimMat));
    const spokes = new THREE.Group();
    for (let k = 0; k < 5; k++) { const s = new THREE.Mesh(spokeGeo, carbon); s.rotation.x = (k / 5) * Math.PI; spokes.add(s); }
    spin.add(spokes);
    car.add(pivot);
    wheels.push({ pivot, spin, spokes, front: z > 0 });
  }

  // exhaust flames
  const flameMat = new THREE.MeshBasicMaterial({ color: hdr(0xff7a20, 4), transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false });
  const flameGeo = new THREE.ConeGeometry(0.12, 0.9, 10, 1, true); flameGeo.rotateX(-Math.PI / 2); flameGeo.translate(0, 0, -0.45);
  const flames = [-0.42, 0.42].map((x) => { const f = new THREE.Mesh(flameGeo, flameMat); f.position.set(x, 0.36, -2.4); body.add(f); return f; });

  return { car, body, wheels, flames, flameMat, tailMat };
}

function blobTex(inner, outer) {
  return canvasTex(128, 256, (g, w, h) => {
    g.save(); g.translate(w / 2, h / 2); g.scale(1, h / w);
    const gr = g.createRadialGradient(0, 0, 0, 0, 0, w / 2);
    gr.addColorStop(0, inner); gr.addColorStop(0.55, inner.replace(/[\d.]+\)$/, '0.5)')); gr.addColorStop(1, outer);
    g.fillStyle = gr; g.fillRect(-w, -w, 2 * w, 2 * w); g.restore();
  }, { repeat: false, srgb: false });
}

// ------------------------------------------------------------------ particles
const PARTICLE_VS = `
attribute float size; attribute float alpha; attribute vec3 tint;
varying float vAlpha; varying vec3 vTint;
uniform float scale;
void main(){
  vAlpha = alpha; vTint = tint;
  vec4 mv = modelViewMatrix * vec4(position,1.0);
  gl_PointSize = clamp(size * scale / -mv.z, 0.0, 400.0);
  gl_Position = projectionMatrix * mv;
}`;
const PARTICLE_FS = (hard) => `
varying float vAlpha; varying vec3 vTint;
void main(){
  vec2 c = gl_PointCoord - 0.5; float d = length(c) * 2.0;
  float a = ${hard ? 'pow(max(0.0, 1.0 - d), 2.5)' : 'smoothstep(1.0, 0.0, d) * 0.8'};
  gl_FragColor = vec4(vTint, a * vAlpha);
}`;
function particleSystem(max, hard) {
  const g = new THREE.BufferGeometry();
  const attrs = { position: 3, tint: 3, size: 1, alpha: 1 };
  for (const [k, n] of Object.entries(attrs)) g.setAttribute(k, new THREE.BufferAttribute(new Float32Array(max * n), n).setUsage(THREE.DynamicDrawUsage));
  const mat = new THREE.ShaderMaterial({
    uniforms: { scale: { value: 600 } }, vertexShader: PARTICLE_VS, fragmentShader: PARTICLE_FS(hard),
    transparent: true, depthWrite: false, blending: hard ? THREE.AdditiveBlending : THREE.NormalBlending,
  });
  const pts = new THREE.Points(g, mat);
  pts.frustumCulled = false;
  let n = 0;
  return {
    pts, mat,
    begin() { n = 0; },
    push(p, tint, size, alpha) {
      if (n >= max) return;
      const P = g.attributes.position.array, T = g.attributes.tint.array;
      P[n * 3] = p[0]; P[n * 3 + 1] = p[1]; P[n * 3 + 2] = p[2];
      T[n * 3] = tint[0]; T[n * 3 + 1] = tint[1]; T[n * 3 + 2] = tint[2];
      g.attributes.size.array[n] = size; g.attributes.alpha.array[n] = alpha; n++;
    },
    end() {
      for (const k of Object.keys(attrs)) g.attributes[k].needsUpdate = true;
      g.setDrawRange(0, n);
    },
  };
}

// ------------------------------------------------------------------ post FX
const FXShader = {
  uniforms: {
    tDiffuse: { value: null }, uBlur: { value: 0 }, uCA: { value: 0.002 }, uFlash: { value: 0 }, uFade: { value: 0 },
    uTime: { value: 0 }, uAspect: { value: 16 / 9 },
  },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float uBlur, uCA, uFlash, uFade, uTime, uAspect; varying vec2 vUv;
    float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453); }
    void main(){
      vec2 c = vec2(0.5); vec2 d = vUv - c;
      vec3 col = vec3(0.0); float tot = 0.0;
      float jitter = h(vUv + uTime) ;
      for (int i = 0; i < 12; i++) {
        float f = (float(i) + jitter) / 12.0;
        float s = 1.0 - uBlur * f * 0.6;
        vec2 uv = c + d * s;
        float w = 1.0 - f * 0.55;
        col.r += texture2D(tDiffuse, c + d * s * (1.0 + uCA)).r * w;
        col.g += texture2D(tDiffuse, uv).g * w;
        col.b += texture2D(tDiffuse, c + d * s * (1.0 - uCA)).b * w;
        tot += w;
      }
      col /= tot;
      float r = length(d * vec2(uAspect, 1.0));
      col *= mix(1.0, 0.35, smoothstep(0.45, 1.05, r));
      col += (h(vUv * 431.0 + uTime * 7.0) - 0.5) * 0.035;
      col = mix(col, vec3(1.0, 0.97, 0.92), uFlash * 0.75);
      col *= 1.0 - uFade;
      gl_FragColor = vec4(col, 1.0);
    }`,
};

// ------------------------------------------------------------------ the film
export function createFilm(canvas, { width, height, pixelRatio = 1 }) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: true });
  renderer.setPixelRatio(pixelRatio);
  renderer.setSize(width, height, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;

  const scene = new THREE.Scene();
  const FOG = 0x0d0820;
  scene.fog = new THREE.FogExp2(FOG, 0.0016);
  scene.background = new THREE.Color(FOG);
  const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 9000);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const envMap = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  scene.add(new THREE.HemisphereLight(0x4a5cff, 0x1a0b1e, 0.55));
  const moon = new THREE.DirectionalLight(0x9fb0ff, 0.5); moon.position.set(-300, 500, -200); scene.add(moon);

  // ---- sky
  const sky = new THREE.Mesh(new THREE.SphereGeometry(6000, 32, 16), new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    vertexShader: `varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: `varying vec3 vP; void main(){
      float y = vP.y;
      vec3 top = vec3(0.004,0.006,0.02), mid = vec3(0.05,0.02,0.11), hor = vec3(0.32,0.09,0.28);
      vec3 c = mix(hor, mid, smoothstep(0.0, 0.12, y)); c = mix(c, top, smoothstep(0.12, 0.6, y));
      c = mix(c, vec3(0.05,0.03,0.08), smoothstep(0.0,-0.1,y));
      gl_FragColor = vec4(c, 1.0); }`,
  }));
  sky.renderOrder = -10;
  scene.add(sky);
  {
    const R = rng(3), N = 2200, p = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      const a = R() * Math.PI * 2, y = 0.06 + Math.pow(R(), 0.7) * 0.94, r = Math.sqrt(1 - y * y);
      p.set([Math.cos(a) * r * 5000, y * 5000, Math.sin(a) * r * 5000], i * 3);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3));
    scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0xcfd8ff, size: 1.6, sizeAttenuation: false, fog: false })));
    const moonDisc = new THREE.Mesh(new THREE.CircleGeometry(120, 48), new THREE.MeshBasicMaterial({ color: hdr(0xf2eedd, 2.2), fog: false }));
    moonDisc.position.set(-2200, 2200, -3600); moonDisc.lookAt(0, 0, 0); scene.add(moonDisc);
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: blobTex('rgba(180,170,255,0.6)', 'rgba(0,0,0,0)'), blending: THREE.AdditiveBlending, fog: false, depthWrite: false }));
    halo.scale.set(1400, 1400, 1); halo.position.copy(moonDisc.position); scene.add(halo);
  }

  // ---- ground
  const groundTex = canvasTex(512, 512, (g, w, h) => {
    const R = rng(11); g.fillStyle = '#0d1410'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 9000; i++) { const v = R(); g.fillStyle = `rgba(${20 + v * 30},${35 + v * 40},${25 + v * 20},0.6)`; g.fillRect(R() * w, R() * h, 2, 2); }
  });
  groundTex.repeat.set(400, 400);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(12000, 12000), new THREE.MeshStandardMaterial({ map: groundTex, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -0.6;
  scene.add(ground);

  // ---- road, kerbs, walls, neon
  const { map: roadMap, glow: roadGlow } = roadTextures();
  const road = new THREE.Mesh(strip((s) => TL.trackPoint(s, -8), (s) => TL.trackPoint(s, 8), 40), new THREE.MeshStandardMaterial({
    map: roadMap, emissiveMap: roadGlow, emissive: 0xffffff, emissiveIntensity: 0.55, roughness: 0.32, metalness: 0.15, envMap, envMapIntensity: 0.6,
  }));
  scene.add(road);
  const kerbTex = canvasTex(32, 128, (g, w, h) => { g.fillStyle = '#d81a2a'; g.fillRect(0, 0, w, h); g.fillStyle = '#f4f4f4'; g.fillRect(0, 0, w, h / 2); });
  const kerbMat = new THREE.MeshStandardMaterial({ map: kerbTex, roughness: 0.5, emissive: 0x220000, emissiveIntensity: 0.4 });
  for (const sgn of [-1, 1]) {
    scene.add(new THREE.Mesh(strip((s) => TL.trackPoint(s, sgn * 8, 0.02), (s) => TL.trackPoint(s, sgn * 9.6, 0.1), 3.2), kerbMat));
  }
  const wallTex = canvasTex(64, 512, (g, w, h) => {
    g.fillStyle = '#2c2c34'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#3c3c46'; for (let y = 0; y < h; y += 64) g.fillRect(0, y, w, 4);
    g.fillStyle = '#f2c300'; for (let y = 0; y < h; y += 64) g.fillRect(0, y + 20, w, 16);
  });
  const wallMat = new THREE.MeshStandardMaterial({ map: wallTex, roughness: 0.7, side: THREE.DoubleSide, emissive: 0x0a0a12 });
  for (const sgn of [-1, 1]) {
    const lat = sgn * 9.7;
    scene.add(new THREE.Mesh(strip((s) => { const p = TL.trackPoint(s, lat, 0); return [p[0], -1.5, p[2]]; }, (s) => TL.trackPoint(s, lat, 1.05), 24), wallMat));
    const neon = new THREE.MeshBasicMaterial({ color: sgn < 0 ? hdr(0x00e5ff, 2.2) : hdr(0xff2bd6, 2.2), side: THREE.DoubleSide });
    scene.add(new THREE.Mesh(strip((s) => TL.trackPoint(s, lat, 1.05), (s) => TL.trackPoint(s, lat, 1.22), 10), neon));
  }

  // ---- start / finish
  {
    const checker = canvasTex(256, 32, (g, w, h) => { for (let x = 0; x < 16; x++) for (let y = 0; y < 2; y++) { g.fillStyle = (x + y) % 2 ? '#111' : '#f5f5f5'; g.fillRect(x * 16, y * 16, 16, 16); } }, { repeat: false });
    const line = new THREE.Mesh(new THREE.PlaneGeometry(16, 2), new THREE.MeshStandardMaterial({ map: checker, roughness: 0.6, polygonOffset: true, polygonOffsetFactor: -2 }));
    const f = TL.trackFrame(0);
    line.position.copy(v3(TL.trackPoint(0, 0, 0.03)));
    setBasis(line, f.R, f.T, f.U);
    line.rotateX(0); scene.add(line);
  }
  const gantry = new THREE.Group();
  const startLights = [];
  {
    const f = TL.trackFrame(0);
    const mat = new THREE.MeshStandardMaterial({ color: 0x1a1a22, metalness: 0.7, roughness: 0.4, envMap });
    for (const sgn of [-1, 1]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.8, 11, 0.8), mat); p.position.set(sgn * 11, 5.5, 0); gantry.add(p); }
    const beam = new THREE.Mesh(new THREE.BoxGeometry(23, 2.4, 1.2), mat); beam.position.set(0, 10, 0); gantry.add(beam);
    const board = canvasTex(1024, 128, (g, w, h) => {
      g.fillStyle = '#05020c'; g.fillRect(0, 0, w, h);
      g.font = 'italic 900 82px Inter, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillStyle = '#ff2bd6'; g.fillText('MIDNIGHT  CIRCUIT', w / 2 + 3, h / 2 + 5);
      g.fillStyle = '#00e5ff'; g.fillText('MIDNIGHT  CIRCUIT', w / 2, h / 2);
    }, { repeat: false });
    const bm = new THREE.MeshBasicMaterial({ map: board, color: new THREE.Color(1.8, 1.8, 1.8) });
    for (const side of [1, -1]) { const b = new THREE.Mesh(new THREE.PlaneGeometry(21, 2.1), bm); b.position.set(0, 10, side * 0.61); if (side < 0) b.rotation.y = Math.PI; gantry.add(b); }
    for (let i = 0; i < 5; i++) {
      const m = new THREE.Mesh(new THREE.CircleGeometry(0.42, 24), new THREE.MeshBasicMaterial({ color: 0x220000 }));
      m.position.set((i - 2) * 1.3, 7.9, -0.62); m.rotation.y = Math.PI; gantry.add(m); startLights.push(m);
      const pod = new THREE.Mesh(new THREE.BoxGeometry(1.1, 1.1, 0.4), mat); pod.position.set((i - 2) * 1.3, 7.9, -0.4); gantry.add(pod);
    }
    gantry.position.copy(v3(TL.trackPoint(0, 0, 0)));
    const R0 = TL.norm([f.R[0], 0, f.R[2]]), T0 = TL.norm([f.T[0], 0, f.T[2]]);
    setBasis(gantry, TL.mul(R0, -1), [0, 1, 0], T0);
    scene.add(gantry);
  }

  // ---- grandstand + crowd flashes (outside of the main straight)
  const flashes = particleSystem(400, true);
  const flashSpots = [];
  {
    const crowd = canvasTex(1024, 256, (g, w, h) => {
      const R = rng(5); g.fillStyle = '#100d18'; g.fillRect(0, 0, w, h);
      const cols = ['#ff3355', '#33aaff', '#ffd23f', '#ffffff', '#7a5cff', '#ff8a3d', '#32e0a0'];
      for (let row = 0; row < 16; row++) for (let x = 0; x < 120; x++) {
        g.fillStyle = cols[Math.floor(R() * cols.length)]; g.globalAlpha = 0.35 + R() * 0.5;
        g.beginPath(); g.arc(x * 8.6 + (row % 2) * 4 + R() * 2, row * 16 + 8, 3.2, 0, 7); g.fill();
      }
    });
    crowd.repeat.set(4, 1);
    const R = rng(21);
    for (const [s0, s1] of [[-88, -14], [14, 165]]) {
      const len = s1 - s0, f = TL.trackFrame((s0 + s1) / 2);
      const R0 = TL.norm([f.R[0], 0, f.R[2]]), T0 = TL.norm([f.T[0], 0, f.T[2]]);
      const stand = new THREE.Group();
      const slope = new THREE.Mesh(new THREE.PlaneGeometry(len, 22), new THREE.MeshStandardMaterial({ map: crowd, emissiveMap: crowd, emissive: 0xffffff, emissiveIntensity: 0.5, roughness: 0.9 }));
      slope.rotation.x = -Math.PI / 2 - 0.62; slope.position.set(0, 7.5, 9);
      stand.add(slope);
      const roof = new THREE.Mesh(new THREE.BoxGeometry(len, 0.6, 16), new THREE.MeshStandardMaterial({ color: 0x15151c, roughness: 0.6 }));
      roof.position.set(0, 20, 12); stand.add(roof);
      const strip2 = new THREE.Mesh(new THREE.BoxGeometry(len, 0.3, 0.3), new THREE.MeshBasicMaterial({ color: hdr(0xff2bd6, 4) }));
      strip2.position.set(0, 19.6, 4.2); stand.add(strip2);
      stand.position.copy(v3(TL.trackPoint((s0 + s1) / 2, 15, 0)));
      setBasis(stand, T0, [0, 1, 0], R0);
      scene.add(stand);
      stand.updateMatrixWorld();
      for (let i = 0; i < 160; i++) {
        const p = new THREE.Vector3((R() - 0.5) * len, 0, 0);
        const yy = R() * 18; p.y = 2 + yy * Math.sin(0.62) + 0.5; p.z = 1.5 + yy * Math.cos(0.62);
        flashSpots.push(stand.localToWorld(p).toArray());
      }
    }
    scene.add(flashes.pts);
  }

  // ---- neon arches
  {
    const geo = new THREE.TorusGeometry(12.2, 0.32, 8, 64, Math.PI);
    const mats = [new THREE.MeshBasicMaterial({ color: hdr(0x00e5ff, 3.2) }), new THREE.MeshBasicMaterial({ color: hdr(0xff2bd6, 3.2) })];
    let k = 0;
    for (let s = 70; s < L - 60; s += 75) {
      const dJ = ((s - TL.JUMP_S + L * 1.5) % L) - L / 2;
      if (dJ > -150 && dJ < 60) continue;
      const f = TL.trackFrame(s);
      const a = new THREE.Mesh(geo, mats[k++ % 2]);
      a.position.copy(v3(f.p)).y -= 0.2;
      setBasis(a, TL.norm([-f.R[0], 0, -f.R[2]]), [0, 1, 0], TL.norm([f.T[0], 0, f.T[2]]));
      scene.add(a);
    }
  }

  // ---- street lamps (instanced) — their pools are baked into the road glow map
  {
    const lamps = [];
    for (let s = 0; s < L - 1; s += 20) lamps.push({ s, side: Math.round(s / 20) % 2 ? 1 : -1 });
    const poleG = new THREE.CylinderGeometry(0.14, 0.2, 9.5, 8); poleG.translate(0, 4.75, 0);
    const armG = new THREE.BoxGeometry(0.16, 0.16, 3.4); armG.translate(0, 9.4, 1.6);
    const headG = new THREE.BoxGeometry(0.6, 0.18, 1.3); headG.translate(0, 9.25, 3.0);
    const coneG = new THREE.ConeGeometry(4.2, 9.3, 20, 1, true); coneG.translate(0, 9.25 - 4.65, 3.0);
    const metal = new THREE.MeshStandardMaterial({ color: 0x24242c, metalness: 0.6, roughness: 0.5 });
    const headM = new THREE.MeshBasicMaterial({ color: hdr(0xffc890, 5) });
    const coneM = new THREE.MeshBasicMaterial({ color: 0xffb070, transparent: true, opacity: 0.05, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    const meshes = [[poleG, metal], [armG, metal], [headG, headM], [coneG, coneM]].map(([g, m]) => new THREE.InstancedMesh(g, m, lamps.length));
    const o = new THREE.Object3D();
    lamps.forEach((l, i) => {
      const f = TL.trackFrame(l.s);
      const p = TL.trackPoint(l.s, l.side * 11.6, 0);
      o.position.set(p[0], p[1] - 0.2, p[2]);
      const inward = TL.mul(TL.norm([f.R[0], 0, f.R[2]]), -l.side);
      setBasis(o, TL.cross([0, 1, 0], inward), [0, 1, 0], inward);
      o.updateMatrix();
      meshes.forEach((m) => m.setMatrixAt(i, o.matrix));
    });
    meshes.forEach((m) => scene.add(m));
  }

  // ---- distance helper for scenery placement
  const trackSamples = [];
  for (let s = 0; s < L; s += 6) trackSamples.push(TL.trackPoint(s));
  const distToTrack = (x, z) => { let d = 1e9; for (const p of trackSamples) d = Math.min(d, (p[0] - x) ** 2 + (p[2] - z) ** 2); return Math.sqrt(d); };
  let cx = 0, cz = 0; trackSamples.forEach((p) => { cx += p[0]; cz += p[2]; }); cx /= trackSamples.length; cz /= trackSamples.length;

  // ---- trees
  {
    const R = rng(33), N = 700;
    const trunkG = new THREE.CylinderGeometry(0.3, 0.4, 3, 6); trunkG.translate(0, 1.5, 0);
    const crownG = new THREE.ConeGeometry(3, 9, 7); crownG.translate(0, 7, 0);
    const trunks = new THREE.InstancedMesh(trunkG, new THREE.MeshStandardMaterial({ color: 0x1c140f }), N);
    const crowns = new THREE.InstancedMesh(crownG, new THREE.MeshStandardMaterial({ color: 0x0f2418, roughness: 0.9 }), N);
    const o = new THREE.Object3D(); let n = 0;
    while (n < N) {
      const x = cx + (R() - 0.5) * 900, z = cz + (R() - 0.5) * 760;
      const d = distToTrack(x, z);
      if (d < 22 || d > 240) continue;
      o.position.set(x, -0.6, z); const sc = 0.7 + R() * 0.9; o.scale.set(sc, sc * (0.8 + R() * 0.5), sc); o.rotation.y = R() * 6; o.updateMatrix();
      trunks.setMatrixAt(n, o.matrix); crowns.setMatrixAt(n, o.matrix); n++;
    }
    scene.add(trunks, crowns);
  }

  // ---- city skyline (procedural lit windows)
  const blinkers = [];
  let blinkPts;
  {
    const mat = new THREE.ShaderMaterial({
      fog: true,
      uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, { uSeed: { value: 1 } }]),
      vertexShader: `
        varying vec3 vW; varying vec3 vN; varying float vId;
        #include <fog_pars_vertex>
        void main(){
          vec4 w = modelMatrix * instanceMatrix * vec4(position,1.0);
          vW = w.xyz; vN = normalize(mat3(modelMatrix * instanceMatrix) * normal); vId = float(gl_InstanceID);
          vec4 mvPosition = viewMatrix * w;
          gl_Position = projectionMatrix * mvPosition;
          #include <fog_vertex>
        }`,
      fragmentShader: `
        varying vec3 vW; varying vec3 vN; varying float vId;
        #include <fog_pars_fragment>
        float h(vec2 p){ return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }
        void main(){
          vec3 base = vec3(0.025, 0.025, 0.04);
          if (abs(vN.y) > 0.5) { gl_FragColor = vec4(base * 0.6, 1.0); }
          else {
            vec2 c = abs(vN.x) > 0.5 ? vec2(vW.z, vW.y) : vec2(vW.x, vW.y);
            vec2 cell = floor(c / vec2(3.2, 3.6)); vec2 f = fract(c / vec2(3.2, 3.6));
            float lit = step(0.58, h(cell + vId * 7.13));
            float win = step(0.18, f.x) * step(f.x, 0.82) * step(0.25, f.y) * step(f.y, 0.8);
            float warm = h(cell.yx + vId);
            vec3 wc = mix(vec3(1.0, 0.72, 0.38), vec3(0.55, 0.8, 1.0), step(0.7, warm)) * (0.9 + warm);
            gl_FragColor = vec4(base + win * lit * wc * 1.4, 1.0);
          }
          #include <fog_fragment>
        }`,
    });
    const R = rng(77), N = 420;
    const g = new THREE.BoxGeometry(1, 1, 1); g.translate(0, 0.5, 0);
    const city = new THREE.InstancedMesh(g, mat, N);
    const o = new THREE.Object3D(); let n = 0;
    while (n < N) {
      const a = R() * Math.PI * 2, r = 480 + Math.pow(R(), 0.8) * 1100;
      const x = cx + Math.cos(a) * r * 1.15, z = cz + Math.sin(a) * r;
      if (distToTrack(x, z) < 160) continue;
      const hgt = 25 + Math.pow(R(), 2.2) * 230 * (r > 900 ? 1 : 0.6);
      o.position.set(x, -0.6, z); o.scale.set(18 + R() * 40, hgt, 18 + R() * 40); o.rotation.y = R() * Math.PI; o.updateMatrix();
      city.setMatrixAt(n++, o.matrix);
      if (hgt > 120) blinkers.push([x, hgt - 0.6 + 2, z]);
    }
    scene.add(city);
    const bg = new THREE.BufferGeometry(); bg.setAttribute('position', new THREE.Float32BufferAttribute(blinkers.flat(), 3));
    const bm = new THREE.PointsMaterial({ color: hdr(0xff2020, 3), size: 5, sizeAttenuation: false, fog: false, transparent: true });
    blinkPts = new THREE.Points(bg, bm);
    scene.add(blinkPts);
  }

  // ---- cars
  const beamTex = canvasTex(128, 256, (g, w, h) => {
    // headlight throw: narrow at the bumper (bottom), wide and faint far ahead (top)
    for (let y = 0; y < h; y++) {
      const k = 1 - y / h, half = (0.12 + 0.88 * (1 - k)) * w / 2;
      const a = Math.pow(k, 0.5) * Math.min(1, (h - y) / 14) * (0.35 + 0.65 * (1 - k));
      const gr = g.createLinearGradient(w / 2 - half, 0, w / 2 + half, 0);
      gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(0.5, `rgba(255,255,255,${a.toFixed(3)})`); gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = gr; g.fillRect(0, y, w, 1);
    }
  }, { repeat: false, srgb: false });
  const cars = TL.CARS.map((def) => {
    const c = makeCar(def, envMap);
    scene.add(c.car);
    c.glow = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 7.2), new THREE.MeshBasicMaterial({ map: blobTex('rgba(255,255,255,0.9)', 'rgba(0,0,0,0)'), color: hdr(def.glow, 1.6), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    c.shadow = new THREE.Mesh(new THREE.PlaneGeometry(2.8, 5.6), new THREE.MeshBasicMaterial({ map: blobTex('rgba(0,0,0,0.85)', 'rgba(0,0,0,0)'), transparent: true, depthWrite: false }));
    c.beam = new THREE.Mesh(new THREE.PlaneGeometry(10, 30), new THREE.MeshBasicMaterial({ map: beamTex, color: new THREE.Color(0.75, 0.82, 1).multiplyScalar(0.2), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    c.glow.renderOrder = 2; c.shadow.renderOrder = 1; c.beam.renderOrder = 2;
    scene.add(c.glow, c.shadow, c.beam);
    return c;
  });

  // ---- particles
  const smoke = particleSystem(1400, false);
  const sparks = particleSystem(1600, true);
  scene.add(smoke.pts, sparks.pts);
  const landingsByCar = TL.LANDINGS;

  // ---- composer
  const composer = new EffectComposer(renderer);
  composer.setPixelRatio(pixelRatio);
  composer.setSize(width, height);
  composer.addPass(new RenderPass(scene, camera));
  // tame specular glints before bloom so a single hot pixel can't wash out the frame
  composer.addPass(new ShaderPass({
    uniforms: { tDiffuse: { value: null } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
    fragmentShader: `uniform sampler2D tDiffuse; varying vec2 vUv; void main(){ vec4 c = texture2D(tDiffuse, vUv); float m = max(c.r, max(c.g, c.b)); gl_FragColor = vec4(c.rgb * min(1.0, 7.0 / max(m, 1e-4)), c.a); }`,
  }));
  const bloom = new UnrealBloomPass(new THREE.Vector2(width, height), 0.55, 0.42, 0.92);
  composer.addPass(bloom);
  const fx = new ShaderPass(FXShader);
  fx.isFX = true;
  composer.addPass(fx);
  composer.addPass(new OutputPass());

  const tmpPose = (i, tau) => TL.carPose(i, tau);

  function updateParticles(tau, t) {
    smoke.begin(); sparks.begin();
    const H = TL.hash;
    // launch wheelspin smoke
    for (let ci = 0; ci < 2; ci++) {
      const t0 = TL.TAU_GO - 0.5, t1 = TL.TAU_GO + 1.4, life = 2.4, dt = 0.012;
      const k0 = Math.ceil((Math.max(t0, tau - life) - t0) / dt), k1 = Math.floor((Math.min(t1, tau) - t0) / dt);
      for (let k = k0; k <= k1; k++) {
        const bb = t0 + k * dt, age = tau - bb, id = ci * 1000 + k;
        const P = tmpPose(ci, Math.max(bb, 0));
        const side = k % 2 ? 1 : -1;
        const p0 = TL.local(P, side * 0.95, 0.25, -1.45);
        const vel = TL.add(TL.add(TL.mul(P.fwd, -3 - H(id) * 4), TL.mul(P.left, side * (1 + H(id + 1) * 3))), [0, 1.2 + H(id + 2) * 1.5, 0]);
        const p = TL.add(p0, TL.mul(vel, age * (1 - age / (life * 2))));
        const fadeIn = Math.min(1, age * 8);
        const g = 0.32 + H(id + 3) * 0.1;
        smoke.push(p, [g, g, g * 1.05], 1.4 + age * 3.0, 0.3 * fadeIn * Math.pow(1 - age / life, 1.4));
      }
    }
    // landings: sparks + dust
    landingsByCar.forEach((l, li) => {
      if (tau < l.tau || tau > l.tau + 1.2) return;
      const big = l.peak > 2;
      const dur = 0.3, dt = big ? 0.0025 : 0.006, life = 0.55;
      const k1 = Math.floor((Math.min(l.tau + dur, tau) - l.tau) / dt);
      for (let k = 0; k <= k1; k++) {
        const b = l.tau + k * dt, age = tau - b, id = li * 5000 + k;
        if (age > life) continue;
        const P = tmpPose(l.car, b);
        const p0 = TL.local(P, (H(id) - 0.5) * 1.6, 0.06, (H(id + 1) - 0.5) * 3.4);
        const vel = TL.add(TL.add(TL.mul(P.fwd, P.v * (0.55 + H(id + 2) * 0.3)), TL.mul(P.left, (H(id + 3) - 0.5) * 9)), [0, 2 + H(id + 4) * 7, 0]);
        const p = TL.add(TL.add(p0, TL.mul(vel, age)), [0, -12 * age * age, 0]);
        const heat = 1 - age / life;
        sparks.push(p, [4 * heat + 1, 1.8 * heat + 0.4, 0.4 * heat], 0.22 + 0.1 * H(id + 5), heat);
      }
      for (let k = 0; k < (big ? 24 : 8); k++) {
        const b = l.tau + (k / 24) * 0.2, age = tau - b, id = li * 7000 + k;
        if (age < 0 || age > 1.1) continue;
        const P = tmpPose(l.car, b);
        const p0 = TL.local(P, (H(id) - 0.5) * 2.4, 0.2, -1.5 - H(id + 1) * 1.5);
        const p = TL.add(p0, TL.add(TL.mul(P.fwd, P.v * 0.3 * age), [0, age * 1.2, 0]));
        smoke.push(p, [0.22, 0.2, 0.24], 1.5 + age * 3, 0.2 * (1 - age / 1.1));
      }
    });
    // crowd camera flashes — a storm at the finish
    flashes.begin();
    const nearFinish = Math.exp(-Math.pow((tau - TL.FINISH_TAU[TL.WINNER]) / 1.2, 2));
    const nearStart = Math.exp(-Math.pow((tau - TL.TAU_GO) / 1.5, 2));
    const prob = 0.012 + 0.25 * nearFinish + 0.08 * nearStart;
    const frame = Math.floor(tau * 24);
    flashSpots.forEach((p, i) => { if (H(frame * 0.37 + i * 1.731) < prob) flashes.push(p, [6, 6, 6], 1.4, 1); });
    flashes.end();
    smoke.end(); sparks.end();
    void t;
  }

  function render(t) {
    const cam = TL.cameraAt(t);
    const tau = cam.tau;

    cars.forEach((c, i) => {
      const P = TL.carPose(i, tau);
      c.car.position.copy(v3(P.pos));
      setBasis(c.car, P.left, P.up, P.fwd);
      c.body.position.y = -P.susp * 0.45;
      const wheelRot = -P.s / 0.37;
      c.wheels.forEach((w) => {
        w.spin.rotation.x = wheelRot;
        w.spokes.visible = P.v < 14;
        if (w.front) w.pivot.rotation.y = P.steer * 1.4;
        w.pivot.position.y = 0.37 - Math.min(P.air, 0.12);
      });
      // exhaust pops: on upshifts and when lifting off
      const gr = TL.gearRpm(P.v), grPrev = TL.gearRpm(TL.carV(i, tau - 0.12));
      const shift = gr.gear > grPrev.gear ? 1 : 0;
      const lift = P.acc < -6 ? 0.6 : 0;
      const crackle = TL.hash(Math.floor(tau * 30) + i * 13);
      const flame = Math.max(shift * (0.6 + crackle * 0.6), lift * (crackle > 0.45 ? crackle : 0), (tau > TL.TAU_GO - 2 && tau < TL.TAU_GO) ? (crackle > 0.7 ? 0.6 : 0) : 0);
      c.flames.forEach((f, k) => { f.visible = flame > 0.05; f.scale.set(0.8 + flame, 0.8 + flame, flame * (1.2 + TL.hash(tau * 50 + k) * 0.8)); });
      c.flameMat.color.copy(hdr(crackle > 0.5 ? 0x60a0ff : 0xff7a20, 4));
      c.tailMat.color.copy(hdr(0xff1020, P.acc < -8 ? 9 : 3));
      // ground glow + contact shadow on the road under the car
      const f = P.frame;
      const ground = TL.madd(TL.madd(f.p, f.R, P.lat), f.U, 0.04);
      for (const [m, lift2, ahead] of [[c.shadow, 0.035, 0], [c.glow, 0.05, 0], [c.beam, 0.06, 17]]) {
        m.position.copy(v3(TL.madd(TL.madd(ground, f.U, lift2), P.fwd, ahead)));
        setBasis(m, TL.cross(P.fwd, f.U), P.fwd, f.U);
      }
      c.beam.material.opacity = Math.max(0, 1 - P.air / 1.5);
      const airK = Math.max(0, 1 - P.air / 6);
      c.shadow.material.opacity = airK;
      c.glow.material.opacity = 0.25 + 0.75 * airK;
      const sc = 1 + P.air * 0.08; c.shadow.scale.set(sc, sc, 1);
    });

    // start lights
    const hud = TL.hudAt(t);
    startLights.forEach((m, i) => m.material.color.copy(hud.lights > i ? hdr(0xff1010, 6) : new THREE.Color(0x200000)));
    blinkPts.material.opacity = Math.sin(tau * 3.2) > 0.2 ? 1 : 0.1;

    updateParticles(tau, t);

    camera.position.copy(v3(cam.pos));
    camera.up.copy(v3(cam.up));
    camera.lookAt(v3(cam.target));
    camera.fov = cam.fov;
    camera.updateProjectionMatrix();
    const ps = renderer.getDrawingBufferSize(new THREE.Vector2());
    smoke.mat.uniforms.scale.value = sparks.mat.uniforms.scale.value = flashes.mat.uniforms.scale.value = ps.y / (2 * Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)));

    fx.uniforms.uBlur.value = cam.blur;
    fx.uniforms.uCA.value = cam.ca;
    fx.uniforms.uFlash.value = cam.flash;
    fx.uniforms.uFade.value = cam.fade;
    fx.uniforms.uTime.value = t;
    fx.uniforms.uAspect.value = width / height;
    composer.render();
    return { hud, cam };
  }

  function resize(w, h, pr = pixelRatio) {
    width = w; height = h;
    renderer.setPixelRatio(pr); renderer.setSize(w, h, false);
    composer.setPixelRatio(pr); composer.setSize(w, h);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }

  return { render, resize, renderer, scene, composer };
}

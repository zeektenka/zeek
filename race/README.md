# Midnight Circuit

A 60-second, fully procedural three.js short: two cars, #07 VEGA and #23 KAI,
race two laps of a neon night circuit. It has a launch, a mid-race overtake,
a slow-motion jump on lap two and a photo finish. There are no models,
textures or audio files: geometry, livery, city, particles and the soundtrack
are all generated in code.

`midnight-circuit.mp4` is the rendered film (1280×720, 30 fps, with audio).

## Watch it live

Serve the folder and open `index.html`:

```bash
cd race
python3 -m http.server 8000   # → http://localhost:8000
```

Space plays and pauses, `R` restarts, ←/→ skip 5 s, and clicking the bar at
the bottom scrubs. The page plays `midnight-circuit.m4a` alongside the
picture if the file is present.

## How it's built

| File | What it does |
| --- | --- |
| `timeline.js` | The deterministic race script, written as pure math so Node can use it too. It holds the track spline, the curvature-limited speed profile (tuned so the leader crosses the line at 54.95 s), the gap and lane choreography between the cars, the airtime and suspension physics, and the slow-motion time warp. It also defines the camera shots and the HUD state. |
| `scene.js` | The three.js world: road ribbons with baked lamp-light pools, kerbs, neon walls and arches, lamps, the grandstand, the city skyline (windows lit by a shader), the cars, particles for wheelspin smoke, landing sparks and crowd flashes, then bloom, zoom blur, chromatic aberration and grain. |
| `hud.js` | The broadcast overlay: start lights, lap and timer, standings, speed and gear, captions and the winner card. |
| `tools/render.mjs` | Renders frames in headless Chromium (SwiftShader) across parallel workers. |
| `tools/audio.mjs` | Synthesizes the soundtrack from the same timeline. Engine pitch follows each car's real rpm and gear, with Doppler and pan taken from the actual camera. A 140 bpm synthwave score drops out for the slow-mo, and impacts, whooshes on the cuts, and the crowd are layered on top. |

Every frame is a pure function of time `t`, so the film can be scrubbed,
played live, or rendered in parallel.

## Re-render the video

```bash
cd race
npm install                                   # local three.js for offline rendering
NODE_PATH=$(npm root -g) node tools/render.mjs --out frames --workers 4
node tools/audio.mjs midnight-circuit.wav
ffmpeg -framerate 30 -i frames/f%05d.jpg -i midnight-circuit.wav \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k \
  -movflags +faststart -shortest midnight-circuit.mp4
ffmpeg -i midnight-circuit.wav -c:a aac -b:a 160k midnight-circuit.m4a
```

To render a few stills instead of the whole film, pass `--times 4.6,18.4,41,55`.

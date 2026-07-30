# Neon Raiders

A colorful retro-arcade space shooter, built with plain HTML5 canvas and vanilla JavaScript — no build step, no dependencies, no external art or audio files.

## Play

Open `index.html` in a browser, or serve the folder with any static server:

```bash
python3 -m http.server 8000
# then visit http://localhost:8000
```

It also works great hosted on GitHub Pages directly from this repo.

## Controls

| Action | Key |
| --- | --- |
| Move | Arrow keys or `A` / `D` |
| Fire | `Space` (hold for auto-fire) |
| Pause | `P` |
| Mute | button on the start screen |

On touch devices, drag anywhere on screen to move, or use the left/right zones — touching either side auto-fires.

## Features

- Neon CRT arcade look: scanlines, vignette, glow, glitchy title, pixel font
- Parallax multi-layer starfield
- Three enemy types (drone / striker / brute) plus a boss fight every 5 waves
- Power-ups: rapid fire, triple spread shot, temporary shield, extra life
- Escalating difficulty, particle explosions, screen shake
- All sound effects (lasers, explosions, power-ups, boss alert, game-over jingle) and the background bassline are synthesized live with the Web Audio API — zero audio files to load
- High score saved locally via `localStorage`

## Files

- `index.html` — page structure and UI overlays
- `style.css` — retro arcade visual theme
- `game.js` — game loop, entities, physics, audio engine

# Off the Map: animation engine (v2)

Python engine for the channel's collage / cutout look (2.5D parallax). It
replaces the v1 engine, which was lost with an old workspace. It lives in git
now so that can't happen again.

```bash
./setup.sh                                   # once per fresh workspace
python3 videos/01-zimbabwe/make.py sheet     # contact sheet of every shot
python3 videos/01-zimbabwe/make.py preview   # fast 540p check with audio
python3 videos/01-zimbabwe/make.py master    # 1080p60 + mixed audio
python3 tools/thumbnails.py                  # thumbnails for both videos
```

`make.py` assembles whichever acts have voiceover in `videos/<v>/audio/`, so it
works while a video is only partly voiced. **Read `NEXT-SESSION.md` first** — it
says what is finished and what is blocked.

## Layout

| Path | What it does |
| --- | --- |
| `engine/canvas.py` | Canvas, camera, sprites. World space is fixed at 1920x1080; output size and supersampling (`ss`) are separate, so the same scene code renders a 540p preview or a 4K master. `depth` gives parallax (0 = pinned to screen, 1 = main plane). |
| `engine/ease.py` | Easing curves (ease-in-out, overshoot pop-ins), keyframe `Track`, `stagger` (2-4 frame offsets), `drift` (the camera never sits still). |
| `engine/paper.py` | Materials: paper grain, torn edges with a fibrous rim, photo cutouts with white borders, masking tape, rubber stamps, typewriter labels, halftone, hand-drawn circles and underlines. All seeded, so they render the same every time. |
| `engine/style.py` | Design system tokens (palette, fonts, shadows) and collage pieces: desk background, newsprint scraps, banknote, loaf, halftone bank facade, case folder, title strips. Motion helpers: `slap` (drop-onto-page entrance), `write_on`. |
| `engine/geo.py` | Natural Earth borders as vectors, projected every frame: real zooms from continent to city, highlighted countries lift off as paper cutouts. |
| `engine/post.py` | Radial light, vignette, glow, film grain (also stops banding after YouTube compression). |
| `engine/render.py` | `Video` timeline: stills, contact sheets (stage 8), sub-frame motion blur, chunked parallel rendering to ffmpeg, audio mux. Profiles: `preview`, `master` (x264 CRF 14), `master10` (x265 10-bit). |
| `engine/audio.py` | Stage 6 and 9: join voiceover parts, word timestamps from ElevenLabs speech-to-text JSON (`Timing.at("loaf of bread")`), silence fallback, music ducking (sidechain), swells, sound effects, two-pass loudnorm to -14 LUFS. |
| `engine/cutout.py` | Background removal for photo cutouts (IS-Net, rembg's general-use model, onnxruntime on CPU). |
| `engine/shots.py` | Shot templates (headline, big stat, ledger, cards, equation, line chart, two-sided card, map shot, counter, arrow, share grid) and `Reel`, which turns a list of (narration phrase, shot) into a timed video. |
| `videos/01-zimbabwe/` | Video 1: script, sources, shot lists per act, upload package. |
| `videos/10-printing/` | Video 10: same structure. |
| `tools/` | Thumbnail generation and voiceover fetching. |

## How a video is assembled

Shots are cued to **phrases in the narration**, never to hard-coded seconds:

```python
SHOTS = [
    ("In 2008", hook),
    ("you have to start somewhere unexpected", map_intro),
    ("that economy ran into three bills", three_bills),
]
```

`Reel` looks each phrase up in the voiceover's timing and derives every start and
duration from it. Regenerating the audio re-times the whole video with no code
changes. Inside a shot, `cue("Black Friday")` gives the local time of that phrase.

Timings come from `engine/audio.py: align`, an offline forced aligner: it detects
pauses, matches sentence boundaries to them by dynamic programming, then spreads
words by character weight. No transcription service, so no credits. It matched a
known ground truth to within 0.4 s. `Timing.from_elevenlabs` still accepts real
speech-to-text JSON if you want exact word timings.

## Writing a scene

A scene is `fn(cv, t)`, with `t` in seconds from the scene's start. Build
sprites once with `S.cached(...)`, then place them every frame:

```python
def scene(cv, t):
    camera_drift(cv, t)                       # slow push-in + drift
    S.desk(cv)
    note = S.cached(cv, "note", lambda r: S.banknote(r))
    S.slap(cv, note, 640, 430, t, T.at("trillion") - t0, rot=-6)
    S.write_on(cv, P.hand_ellipse(1390, 395, 290, 190), t, 1.5)
    S.finish(cv)
```

Key moments come from the voiceover timing (`Timing.at(phrase)`), not hand-typed
seconds.

## Design rules (v2)

- Palette: ink base `#151412`, paper `#eee6d6`, kraft `#c4ad86`, grey `#8a857a`, accent `#ff4a1c`. Use the accent only for the key point of each shot.
- Fonts (in `assets/fonts`, OFL/Apache): Anton for headlines and numbers, Special Elite for labels, Inter for clean text.
- Few words on screen, set large. A visual change every 3-5 s; the strongest visual in the first 10 s.

## Workspace notes (Oct 12, 2026)

This workspace differs from the one the v2 hand-off describes:

- 4 CPUs, ~15 GB RAM.
- pip works. `setup.sh` installs scipy and OpenCV.
- `raw.githubusercontent.com` **does** work here, contrary to the old notes.
- Wikimedia, Pexels and Pixabay are still blocked by the environment's network
  policy. To allow them: environment menu → Edit → Network access → add the hosts
  under Allowed domains. That would let the installed IS-Net model cut out real
  photos instead of everything being drawn in code.
- ElevenLabs audio **is** retrievable: generated files are served from
  `storage.googleapis.com`, which is reachable. Generate via the connector, then
  `tools/fetch_vo.py`.
- GitHub clones and release downloads work. Fonts ship in the repo; `setup.sh` fetches the borders and the cutout model.

Rough speed on this workspace:

| Job | Time |
| --- | --- |
| Style frame, 1080p at ss 2 | ~6 s |
| Preview video, 540p30 | ~2 s per second of video |
| Master, 1080p60 at ss 1.25 | ~9 s per second of video on 4 cores |

4K60 is about 8x the master figure — roughly 7 hours for an 8-minute video on
this container. The engine is resolution-independent: `Video(3840, 2160, fps=60)`
produces 4K when there is a machine for it.

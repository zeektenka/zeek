# Daniel — Scene 01: "The Message"

Vertical 9:16 keyframes (1152×2048) for the 2.5D parallax story series.
Generated with ElevenLabs Creative (GPT Image 2.5 Sunburst, 2K, high quality).

| File | Notes |
| --- | --- |
| `daniel_v2.png` | **Recommended canonical frame.** Clearest head/window separation, cleanest subtitle-safe lower fifth, lamp and city well isolated for parallax. |
| `daniel_v1.png` | Tighter framing, strongest expression, busier foreground. |
| `daniel_v3.png` | Softest light, most painterly background. |

## Canonical character sheet — Daniel
- Age 28, semi-realistic adult proportions
- Messy, tousled dark brown-black hair, strands over forehead
- Defined cheekbones and jaw, straight nose, light stubble, dark eyes, light-olive skin
- Plain charcoal-grey hoodie, hood down, grey drawstrings, no print

## Palette and light
Deep navy shadows, muted teal midtones, warm amber lamp key (right), cool phone underlight on face, restrained gold accents (lamp base, glass rim), atmospheric haze, subtle grain.

## Parallax layers (back to front)
1. Night sky and haze
2. City skyline
3. Window frame mullions
4. Sofa, cushions, side table and lamp
5. Daniel
6. Foreground: coffee table, water glass, book, plant leaves (left)

Suggested motion: slow push-in, foreground drift opposite camera, blink and slight head tilt, flickering phone glow on face and hands.

## Animation — `daniel_scene01.mp4`

10 s, 1080×1920, 30 fps, H.264. Rendered from `daniel_v2.png` by `animate.py`
(`pip install opencv-python-headless numpy pillow rembg`, plus ffmpeg).

Timeline:
- 0–10 s: slow push-in toward Daniel's eyes, with each layer moving at its own depth (city slowest, foreground fastest)
- 2.2 s: phone flares as a message arrives; Daniel recoils slightly
- 3.1 s: blink
- 4.2–6.4 s: he leans in toward the screen
- 6.4 s: scroll flicker on the phone light
- 7.9 s: double blink
- Throughout: city lights twinkle, tower beacon blinks, haze drifts, dust floats in the lamp light, lamp breathes, film grain

`layers/` holds the separated RGBA plates (city, room, Daniel, foreground)
for re-animating in After Effects, CapCut or similar.

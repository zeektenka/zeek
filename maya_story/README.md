# SPARK: a 1-minute animated short

**Story:** Bolt, a little scrap robot, sleeps alone under the moon. A falling star
crashes nearby. He carries it, but its light is fading, so he opens his chest and
gives it his own glowing core and goes dark. The star rises home, the whole sky
lights up in thanks, and one tiny star drifts down to relight Bolt. He waves goodbye.

| Time   | Beat |
|--------|------|
| 0–8 s  | Title, moonlit field, Bolt asleep |
| 8–16 s | Shooting star crashes, Bolt wakes |
| 16–28 s| Bolt walks to the crater |
| 28–36 s| He lifts the star; its light fades |
| 36–44 s| He gives it his core; his eye goes dark |
| 44–54 s| Star rises home, sky blooms with stars, one returns |
| 54–60 s| Bolt glows again, waves. The End |

## Files
- `spark_story.py`: **Maya** script (maya.cmds, Maya 2022+). Builds the whole scene:
  set, rigged Bolt, stars, lights, a keyed `shotCam` with cuts, and 1440 frames at 24 fps.
  Run it in the Script Editor, then `playblast_story("path/spark.mov")` or render `shotCam` with Arnold.
- `render_preview.py`: standalone 2D preview of the same beat sheet (Pillow + numpy + ffmpeg),
  with a synthesized music-box score. `python3 render_preview.py`
- `spark_preview.mp4`: the rendered 60 s preview (1280×720, 24 fps, with audio).

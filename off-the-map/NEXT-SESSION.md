# Pick up here

Updated 12 Oct 2026, overnight session.

## The one thing blocking both videos

**The ElevenLabs account is out of credits.** The quota is 30,001 and 1,220 were
left when I tried to generate. Of six voiceover parts, only one generated:

| Part | Status | Credits |
| --- | --- | --- |
| Zimbabwe part 1 | ✅ generated, 2:46, in `videos/01-zimbabwe/audio/part1.mp3` | 2,206 |
| Zimbabwe parts 2, 3 | ❌ rejected — quota | ~3,600 |
| Printing parts 1-3 | ❌ rejected — quota | ~5,900 |

The rejected ones were refused **before generating**, so they cost nothing. The
whole remaining run needs about **9,500 credits (~$1.90)**.

I deliberately did **not** spend the last 1,220 credits on a fragment of part 2 —
it would have left an awkward join and you'd regenerate the whole part anyway.

**To unblock:** top up or wait for the quota to reset, then do the step below.

## To finish both videos (one pass)

1. Generate the five remaining parts. The exact text is in:
   - `videos/01-zimbabwe/vo/part2.txt`, `part3.txt`
   - `videos/10-printing/vo/part1.txt`, `part2.txt`, `part3.txt`

   Settings that produced part 1: voice **Cedric M – Engaging Documentary
   Narrator** (`VvVVKaa2nHZpbZdtSRSX`), model `eleven_v3`, **1 generation** per
   part (not the default 4 — that quadruples the cost).

2. Download each one:
   ```bash
   python3 tools/fetch_vo.py 01-zimbabwe 2 "<signed url>"
   ```
   The URLs expire after ~2 hours, so fetch them in the same session.

3. Build. Nothing else needs editing — every shot is cued to a phrase in the
   narration, so the animation re-times itself around the new audio:
   ```bash
   python3 videos/01-zimbabwe/make.py sheet     # check the shots first
   python3 videos/01-zimbabwe/make.py master    # 1080p60 + mixed audio
   python3 videos/10-printing/make.py master
   ```

`make.py` only assembles the acts whose audio exists, so it works at every stage.

## What's already done

- **Engine rebuilt** (v2 collage) and committed, so it can't be lost again.
- **Both scripts written and fact-checked** — `script.md` and `facts.md` in each
  video folder. Every figure has a source; a few are flagged ⚠ to re-check.
- **Both videos fully storyboarded in code** — 23 shots for Zimbabwe act 1,
  11 + 9 for acts 2-3, and 26 for the printing video. All cue phrases are
  validated against the scripts, so they will resolve.
- **Zimbabwe Act 1 rendered**: 2:46, 1080p60, narration + ducked music bed,
  mixed to −14.2 LUFS.
- **Upload packages** written for both (`upload.md`).

## Decisions worth your sign-off

1. **Render spec.** I rendered 1080p60, not 4K60. On this 4-CPU container 4K60
   would be roughly 8× slower — about 7 hours for one video. The code is
   resolution-independent: `Video(3840, 2160, fps=60, ss=1.25)` gives 4K when
   there's a machine for it. 1080p also matches the MTN video.
2. **Music.** `make.py` generates a quiet drone as a placeholder bed so the mix
   is real. Replace `out/<video>/music.wav` with a licensed track and re-run.
3. **No photographs.** Media sites are still blocked from this workspace, so
   every image is drawn in code. See the network note in `README.md` — allowing
   Wikimedia/Pexels would open up real cutouts via the IS-Net model, which is
   already installed and tested.
4. **No sound effects yet.** The pipeline calls for paper rustle, tape rip,
   stamp and whoosh hits. I could synthesise those here, but I can't *listen* to
   what I'd be shipping, and badly judged effects would cheapen the whole thing
   faster than having none. `engine/audio.py: mix` already takes an `sfx` list of
   `(time, path, gain_db)`, so they drop straight in once you have files you've
   actually heard — generated in ElevenLabs, or anything licensed.
5. **Timing without transcription.** Rather than spend credits on speech-to-text,
   I wrote an offline forced aligner (`engine/audio.py: align`). It matched a
   known ground truth to within 0.4 s. If you'd rather have exact word timings,
   `Timing.from_elevenlabs` is still there and takes the STT JSON.

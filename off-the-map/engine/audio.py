"""Voiceover timing and the final mix.

Stage 6: join the ElevenLabs parts and load word-level timestamps.
Stage 9: duck music under the voice, add sound effects, normalise to -14 LUFS.
"""
import json
import re
import subprocess

import numpy as np


def _run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def duration(path):
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "default=nw=1:nk=1", path])
    return float(r.stdout.strip())


def join_parts(parts, out, gap=0.0):
    """Concatenate voiceover parts (in order) into one 48 kHz WAV.
    Returns the start offset of each part, needed to shift per-part timestamps."""
    offsets, t = [], 0.0
    for p in parts:
        offsets.append(t)
        t += duration(p) + gap
    inputs = sum((["-i", p] for p in parts), [])
    pad = f"apad=pad_dur={gap}," if gap else ""
    chains = "".join(f"[{i}:a]aresample=48000,{pad}aformat=channel_layouts=mono[a{i}];"
                     for i in range(len(parts)))
    labels = "".join(f"[a{i}]" for i in range(len(parts)))
    _run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex",
          f"{chains}{labels}concat=n={len(parts)}:v=0:a=1[out]", "-map", "[out]", out])
    return offsets


class Word:
    __slots__ = ("text", "start", "end")

    def __init__(self, text, start, end):
        self.text, self.start, self.end = text, start, end

    def __repr__(self):
        return f"{self.text}@{self.start:.2f}"


def _norm(s):
    return re.sub(r"[^a-z0-9%$]+", "", s.lower())


class Timing:
    """Word-level timestamps. Load from ElevenLabs speech-to-text JSON (one
    file per part, with that part's offset) and look words up by phrase."""

    def __init__(self, words=None):
        self.words = words or []

    @classmethod
    def from_elevenlabs(cls, paths, offsets=None):
        if isinstance(paths, str):
            paths = [paths]
        offsets = offsets or [0.0] * len(paths)
        words = []
        for p, off in zip(paths, offsets):
            with open(p) as f:
                data = json.load(f)
            for w in data.get("words", []):
                if w.get("type", "word") != "word":
                    continue
                words.append(Word(w["text"].strip(), w["start"] + off, w["end"] + off))
        return cls(words)

    def _find(self, phrase, occurrence=1):
        target = [_norm(x) for x in phrase.split() if _norm(x)]
        toks = [_norm(w.text) for w in self.words]
        seen = 0
        for i in range(len(toks) - len(target) + 1):
            if toks[i:i + len(target)] == target:
                seen += 1
                if seen == occurrence:
                    return i, i + len(target) - 1
        raise KeyError(f"phrase not found: {phrase!r} (#{occurrence})")

    def at(self, phrase, occurrence=1):
        """Time the phrase starts being spoken."""
        return self.words[self._find(phrase, occurrence)[0]].start

    def end(self, phrase, occurrence=1):
        return self.words[self._find(phrase, occurrence)[1]].end

    def sentences(self):
        """(start, end, text) per sentence, split on . ? !"""
        out, cur = [], []
        for w in self.words:
            cur.append(w)
            if re.search(r"[.?!][\"')\]]*$", w.text):
                out.append((cur[0].start, cur[-1].end, " ".join(x.text for x in cur)))
                cur = []
        if cur:
            out.append((cur[0].start, cur[-1].end, " ".join(x.text for x in cur)))
        return out


def speech_runs(path, noise_db=-35, min_len=0.20):
    """Stretches of actual speech, as (start, end), from silence detection."""
    total = duration(path)
    gaps = pauses(path, noise_db, min_len)
    runs, t = [], 0.0
    for s, e in gaps:
        if s > t + 0.02:
            runs.append((t, min(s, total)))
        t = max(t, e)
    if t < total - 0.02:
        runs.append((t, total))
    return runs or [(0.0, total)]


_ABBR = ("U.S.", "U.K.", "e.g.", "i.e.", "Mr.", "Mrs.", "Dr.", "St.", "No.", "vs.")


def _sentences_of(text):
    """Split into sentences without breaking on abbreviations like U.S."""
    t = " ".join(text.split())
    for i, a in enumerate(_ABBR):
        t = t.replace(a, f"\x00{i}\x00")
    parts = re.split(r"(?<=[.!?])\s+", t)
    out = []
    for p in parts:
        for i, a in enumerate(_ABBR):
            p = p.replace(f"\x00{i}\x00", a)
        if p.strip():
            out.append(p)
    return out


def align(path, text, noise_db=-35, min_len=0.20):
    """Word-level timing for narration WITHOUT a transcription service.

    Sentence boundaries are matched to real pauses in the audio by dynamic
    programming (choosing which detected gaps are sentence ends so that each
    sentence's share of the time best matches its share of the characters),
    then words are spread inside each sentence by character weight.

    Accurate to roughly a couple of hundred milliseconds, which is enough to
    cue visuals. Swap in Timing.from_elevenlabs when a real transcript exists.
    """
    total = duration(path)
    runs = speech_runs(path, noise_db, min_len)
    sents = _sentences_of(text)
    n = len(sents)
    weights = np.array([len(s) for s in sents], float)
    target = np.concatenate([[0.0], np.cumsum(weights) / weights.sum()])

    # candidate sentence boundaries: the end of each speech run
    cands = [0.0] + [e for _, e in runs[:-1]] + [total]
    cands = sorted(set(round(c, 4) for c in cands))
    m = len(cands)
    if m - 2 < n - 1:                      # fewer pauses than sentences
        bounds = [total * t for t in target]
    else:
        INF = float("inf")
        # cost[i][j] = best cost placing boundary j (1..n-1) at candidate i
        cost = [[INF] * (n + 1) for _ in range(m)]
        back = [[-1] * (n + 1) for _ in range(m)]
        cost[0][0] = 0.0
        for j in range(1, n + 1):
            lo, hi = (j, m - 1) if j < n else (m - 1, m - 1)
            for i in range(lo, hi + 1):
                want = target[j] * total
                pen = ((cands[i] - want) / max(total, 1e-6)) ** 2
                best, bi = INF, -1
                for k in range(j - 1, i):
                    if cost[k][j - 1] + pen < best:
                        best, bi = cost[k][j - 1] + pen, k
                cost[i][j], back[i][j] = best, bi
        bounds, i = [total], m - 1
        for j in range(n, 0, -1):
            i = back[i][j]
            bounds.append(cands[i])
        bounds = sorted(bounds)

    words = []
    for si, sent in enumerate(sents):
        t0, t1 = bounds[si], bounds[si + 1]
        toks = sent.split()
        w = np.array([len(x) + 1 for x in toks], float)
        cum = np.concatenate([[0.0], np.cumsum(w) / w.sum()])
        for wi, tok in enumerate(toks):
            words.append(Word(tok, t0 + (t1 - t0) * cum[wi], t0 + (t1 - t0) * cum[wi + 1]))
    return Timing(words)


def pauses(path, noise_db=-35, min_len=0.25):
    """Silence gaps (start, end) — fallback timing when there is no transcript."""
    r = subprocess.run(["ffmpeg", "-i", path, "-af", f"silencedetect=n={noise_db}dB:d={min_len}",
                        "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(starts, ends))


def mix(voice, out, music=None, sfx=(), music_db=-20, duck_db=None, swells=(),
        target_lufs=-14.0, true_peak=-1.0, length=None):
    """Final mix.

    voice: narration WAV. music: bed (looped to length), ducked under the
    voice by sidechain compression. swells: [(start, dur, +dB)] lift the music
    at reveals. sfx: [(time, path, gain_db)]. Two-pass loudnorm to
    target_lufs integrated, true peak limited.
    """
    length = length or duration(voice)
    ins = ["-i", voice]
    fc, mixes = [], ["[v]"]
    fc.append("[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[v][vsc]")
    n = 1
    if music:
        ins += ["-stream_loop", "-1", "-i", music]
        vol = f"{music_db}dB"
        if swells:
            # volume envelope: base level plus smooth bumps at reveals
            terms = "+".join(
                f"({10 ** (db / 20) - 1:.3f})*between(t,{s},{s + d})*sin(PI*(t-{s})/{d})"
                for s, d, db in swells)
            vol = f"'{10 ** (music_db / 20):.4f}*(1+{terms})':eval=frame"
        fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,"
                  f"atrim=0:{length},volume={vol}[m]")
        fc.append("[m][vsc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md]")
        mixes.append("[md]")
        n += 1
    else:
        fc.append("[vsc]anullsink")
    for t, path, gain in sfx:
        ins += ["-i", path]
        ms = int(t * 1000)
        fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,"
                  f"volume={gain}dB,adelay={ms}|{ms}[s{n}]")
        mixes.append(f"[s{n}]")
        n += 1
    fc.append(f"{''.join(mixes)}amix=inputs={len(mixes)}:normalize=0:duration=first[pre]")
    graph = ";".join(fc)
    # pass 1: measure
    r = subprocess.run(["ffmpeg", "-y", *ins, "-filter_complex",
                        graph + f";[pre]loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:print_format=json[o]",
                        "-map", "[o]", "-t", str(length), "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    ln = (f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:measured_I={m['input_i']}:"
          f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    _run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex",
          graph + f";[pre]{ln},aresample=48000[o]", "-map", "[o]", "-t", str(length),
          "-c:a", "pcm_s24le", out])
    return out


def loudness(path):
    """Integrated loudness (LUFS) of a file, for checking the final mix."""
    r = subprocess.run(["ffmpeg", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)[-1])

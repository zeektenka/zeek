#!/usr/bin/env python3
"""Download generated voiceover audio into a video's audio/ folder.

    python3 tools/fetch_vo.py 01-zimbabwe 2 "https://storage.googleapis.com/..."

ElevenLabs content URLs are signed and expire after about two hours, so fetch
them in the same session that generated them.
"""
import os
import subprocess
import sys

if len(sys.argv) != 4:
    sys.exit(__doc__)
video, part, url = sys.argv[1], int(sys.argv[2]), sys.argv[3]
dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "videos", video, "audio")
os.makedirs(dest_dir, exist_ok=True)
dest = os.path.join(dest_dir, f"part{part}.mp3")
subprocess.run(["curl", "-sSL", "--max-time", "180", "-o", dest, url], check=True)
dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=nw=1:nk=1", dest], capture_output=True, text=True).stdout.strip()
print(f"saved {dest} ({float(dur):.1f}s)")

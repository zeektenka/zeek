#!/usr/bin/env bash
# One-time setup for a fresh workspace. Fonts ship in the repo; this fetches
# the larger assets (world borders, cutout model) and Python packages.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p assets/geo assets/models

# Python packages (numpy, Pillow and onnxruntime are usually preinstalled)
python3 -c "import scipy, cv2" 2>/dev/null || \
  pip install -q --break-system-packages scipy opencv-python-headless || \
  echo "pip blocked: install scipy + opencv another way"

# Exact world borders (Natural Earth 50m, public domain)
if [ ! -f assets/geo/ne_50m_admin_0_countries.geojson ]; then
  tmp=$(mktemp -d)
  git clone -q --depth 1 --filter=blob:none --sparse https://github.com/nvkelso/natural-earth-vector.git "$tmp/ne"
  (cd "$tmp/ne" && git sparse-checkout set --no-cone /geojson/ne_50m_admin_0_countries.geojson)
  cp "$tmp/ne/geojson/ne_50m_admin_0_countries.geojson" assets/geo/
  rm -rf "$tmp"
fi

# Background removal model for photo cutouts (IS-Net, ~178 MB)
if [ ! -f assets/models/isnet-general-use.onnx ]; then
  curl -sSL -o assets/models/isnet-general-use.onnx \
    https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx
fi
echo "setup ok"

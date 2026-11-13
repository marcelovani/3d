#!/bin/bash
# Rebuilds the printable engine from the downloaded model, from scratch.
# Usage: ./build.sh [model zip, default source/engine-gltf.zip] [output folder, default output/latest]
# Needs: Blender 4.5+ (uses the MANIFOLD boolean solver), at /Applications/Blender.app
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ZIP="${1:-$HERE/source/engine-gltf.zip}"
OUT="${2:-$HERE/output/latest}"
HERE="$(cd "$(dirname "$0")" && pwd)"; SC="$HERE/scripts"
BL=/Applications/Blender.app/Contents/MacOS/Blender
WORK="$HERE/work"; mkdir -p "$WORK/src"
unzip -oq "$ZIP" -d "$WORK/src"
$BL -b -P "$SC/build1.py" -- "$WORK/stage1.blend" "$SC" "$WORK/src/scene.gltf"   # upright, 150 mm, split moving parts, fuse body
$BL -b "$WORK/stage1.blend" -P "$SC/build2.py" -- "$WORK/stage2.blend"             # fill inside, compute cavity
$BL -b "$WORK/stage2.blend" -P "$SC/build3.py" -- "$SC" "$WORK/stage3.blend"       # cut cavity + holes, split sump and oil cap
$BL -b "$WORK/stage3.blend" -P "$SC/build4.py" -- "$SC" "$WORK/stage4.blend"       # N20 sleeve + gears
$BL -b "$WORK/stage4.blend" -P "$SC/build5.py" -- "$SC" "$WORK" "$WORK/stage5.blend"       # smoke system, rocker cover, manifold, exhaust, intake
$BL -b "$WORK/stage5.blend" -P "$SC/build6.py" -- "$SC" "$WORK" "$WORK/stage6.blend"       # screw starter holes
$BL -b "$WORK/stage6.blend" -P "$SC/export.py" -- "$SC" "$OUT"                    # clean, decimate, STLs + USDZ + .blend
echo "Done: $OUT"

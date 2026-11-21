#!/bin/bash
# Scan every piece of the simplified source, one Blender process per piece, so memory is
# released between pieces. A watchdog kills Blender above LIMIT_KB (default 4 GB).
# Pieces whose STL already exists are skipped, so a stopped run can be resumed.
# Usage: scripts/v5/run.sh [out dir] [piece ...]   (from Models/Engine; no pieces = all, biggest first)
set -u
cd "$(dirname "$0")/../.."
B=/Applications/Blender.app/Contents/MacOS/Blender
SRC=${SRC:-source/engine-parts.blend}
OUT=${1:-output/v5}; shift 2>/dev/null || true
LIMIT_KB=${LIMIT_KB:-4000000}
mkdir -p "$OUT"
NAMES="$*"
[ -z "$NAMES" ] && NAMES=$($B -b "$SRC" --python-expr "import bpy
for o in sorted((o for o in bpy.data.objects if o.type=='MESH'), key=lambda o:-len(o.data.polygons)): print('NAME', o.name)" 2>/dev/null | awk '/^NAME /{print $2}')
for n in $NAMES; do
  [ -f "$OUT/$n.stl" ] && { echo "skip $n"; continue; }
  $B -b -P scripts/v5/scan.py -- "$SRC" "$OUT" "$n" >> "$OUT/log.txt" 2>&1 &
  P=$!; PEAK=0
  while kill -0 $P 2>/dev/null; do
    R=$(ps -o rss= -p $P 2>/dev/null | tr -d ' '); R=${R:-0}
    [ "$R" -gt "$PEAK" ] && PEAK=$R
    if [ "$R" -gt "$LIMIT_KB" ]; then kill $P; echo "KILLED $n at $((R/1024)) MB"; fi
    sleep 1
  done
  echo "$n peak $((PEAK/1024)) MB $(grep "LOG [0-9]* $n G" "$OUT/log.txt" | tail -1 | cut -d' ' -f6-)"
done
# make parts that sit on each other fit (pulley holes opened to their pins, pockets cut for them)
$B -b -P scripts/v5/fit.py -- "$OUT" 2>&1 | grep -E "^FIT|Error"
# every part together in its print colour: engine.blend, and one STL per colour (engine-<colour>.stl)
$B -b -P scripts/v5/assemble.py -- "$OUT" 2>&1 | grep -E "^ASSEMBLE|Error"
$B -b "$OUT/engine.blend" -P scripts/v5/sheet.py -- "$OUT/contact-sheet.png" 4 2>&1 | grep -E "SHEET|Error"

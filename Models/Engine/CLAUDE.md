# Engine — 3D-printable model engine

Side project: a downloaded car-engine model turned into a 15 cm printable engine. An N20 motor turns the
flywheel, a rubber-band belt drives the fan, and a DIY e-cig smoke system (still to come) blows smoke out
through the exhaust manifold.

- **Read `NOTES.md` first.** It has the goal, decisions, parts list with links, part map, version history,
  and how to rebuild.
- **Record every step in `NOTES.md` as you go.** Marcelo wants to be able to redo everything from scratch
  in another session.
- Rebuild from scratch with `./build.sh` (Blender ≥ 4.5 headless). It reads `source/` and writes `output/latest/`.
  Stage scripts live in `scripts/`.
- When a change works, copy `output/latest/` to the next `output/vN/` and add a version section to `NOTES.md`.
- Scratch files go in the session scratchpad, never in other projects.

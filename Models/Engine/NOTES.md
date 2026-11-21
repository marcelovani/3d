# Engine model — 3D print with working flywheel and fan

Project folder: `~/Development/Projects/3d/Models/Engine/` — `NOTES.md` (this file), `build.sh`, `scripts/`, `source/`, `output/`, `images/`.

Started 2026-11-13.

## Goal

Print a simplified copy of the downloaded engine model, about **10 cm long**, with a small motor inside
that turns the flywheel and, through a rubber-band belt, the fan at the front, so it looks like a running engine.

## Source model

| File                                                             | Contents                                      |
| ---------------------------------------------------------------- | --------------------------------------------- |
| `source/engine-gltf.zip` (copy of `~/Downloads/archive (2).zip`) | `scene.gltf` + `scene.bin` — **working copy** |
| `source/engine.usdz` (copy of `~/Downloads/scene.usdz`)          | Same model as USD (`scene.usdc`), not used    |

- 143 meshes, ~2.3 million triangles — far too detailed to print at 10 cm.
- Proportions (x, y, z): 0.659 × 0.584 × 0.726 model units.
- Front: fan, water-pump pulley, alternator, crank pulley, belt. Back: flywheel with ring gear.
- Parts have **no useful names** (`Mesh_0`…`Mesh_142`, materials `App…`), and some meshes were merged
  by material, so one mesh can hold several physical parts. Parts are identified by position, shape
  and a labelled contact sheet.

## Part map (from contact sheet `images/engine-parts-contact-sheet.png`)

| Part                       | Mesh     | Note                                       |
| -------------------------- | -------- | ------------------------------------------ |
| Flywheel (incl. ring gear) | Mesh_115 | Merged with small pieces elsewhere — split |
| Fan                        | Mesh_17  |                                            |
| Fan pulley (behind fan)    | Mesh_25  | Merged with other pieces — split           |
| Crank pulley (lower front) | Mesh_138 | Merged with other pieces — split           |

**The file is upside down** — rotate 180° around X (the crank axis) before any work. Plan image:
`images/engine-plan.png`.
| Belt | Mesh_3 | Removed — rubber band replaces it |
| Crankshaft | Mesh_104 | Its axis = where the 3 mm axle goes |
| Internals (pistons, rods 140, camshaft 69, timing gear 53, chain 4, valves/springs) | various | Removed — makes room for the motor |

To be confirmed by the user.

## Decisions

| #   | Decision                                                                                          | Why                                                                                              |
| --- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| 1   | Edit with Blender, scripted (headless)                                                            | Handles glTF, can fuse, remesh, decimate and export STL                                          |
| 2   | Print size ~10 cm long                                                                            | User's choice                                                                                    |
| 3   | ~~Worm gear + 130 motor crosswise~~ → **N20 geared motor (~300 rpm @ 6 V), parallel to the axle** | User wanted the motor parallel; worm only works at 90°. Gearbox is built in — no worm set to buy |
| 4   | N20 drives the axle through **one pair of printed 1:1 spur gears** (module 1, ~15T)               | Module 1 is printable; N20 output and axle are both 3 mm                                         |
| 5   | Crank axle: 3 mm steel rod through the block — flywheel at the back, crank pulley at the front    | One axle, no extra gears                                                                         |
| 6   | Rubber band as belt: crank pulley → fan pulley; fan pulley on its own short axle                  | Simple, cheap                                                                                    |
| 7   | ~~Buy the small gears~~ — no longer needed with the N20                                           | Module 1 gears print fine                                                                        |
| 8   | Reuse the existing model as the starting point                                                    | Keeps the look; only add the internal mechanism                                                  |
| 9   | Exhaust manifold (Mesh_0, 4-into-1) **hollow**, open into the hollow block                        | Air flows from inside the engine out through the pipes                                           |
| 10  | Add an **exhaust pipe** from the manifold outlet, down and back past the flywheel                 | Same bore as the manifold outlet                                                                 |

| 11 | Exhaust pipe stops just behind the flywheel (stub) | Can be extended later |

### Smoke system (idea, 2026-11-13 — open)

- Oil cap: removable, push-fit (no thread). Glycerin is poured in through it.
- 4 mm hose from the oil cap down to a **glycerin container** inside the block.
- E-cig coil (solenoid) in the container heats the glycerin → smoke.
- **Fan inside the engine** pulls outside air in, past the coil, and pushes smoke out through the hollow manifold and exhaust.
- User's idea: fan driven by the crank, geared faster than the flywheel.
- Air intake: suggested through the **air filter** on top (already a mesh).

Concerns raised:

- Coil runs ~200 °C+; PLA softens ~60 °C, PETG ~80 °C → heater must sit in a metal housing (e.g. a ready-made atomizer with wick), not directly in printed plastic.
- A bare coil without a wick tends to burn the glycerin (acrid) rather than vaporise it.
- Coil draws 2–4 A → needs a protected Li-ion cell and a switch.
- Space at 10 cm is tight for motor + worm + tank + heater + fan → consider a bigger print.
- A ready-made RC model smoke generator (heater + wick + fan in one unit) would replace the DIY coil and the crank-driven fan.

User: print size can grow as needed. E-cig atomizer keeps heat inside its own housing — acceptable fallback.

**Decision: DIY.** Ready-made units too expensive / unavailable. Use the dismantled e-cig atomizer
(cylinder ~10 mm Ø × 20 mm) in a printed holder; design our own fan.
Airflow: air filter (intake) → blower → atomizer → hollow manifold → exhaust stub.

Blower: printed centrifugal (snail housing). Motor chosen: single-shaft N20 300 rpm (https://www.ebay.co.uk/itm/267082315931).
**Two-stage rubber-band step-up**: crank → intermediate pulley on its own axle (~4×) → blower (~4×) = ~16×, ~4,800 rpm at full speed.
Dual-shaft N20 (rear shaft at motor speed) was the alternative — rejected. Mount also fits a 130 motor as a fallback. Chosen for realism — more power → faster spin → more smoke flow.

Controls: one speed controller for the motor, a separate one for the burner (heater power sets how much glycerin burns).
For now battery + controllers sit **outside**; wires exit through the **bottom** of the engine. Base/compartment later.

### Layout check at 150 mm (2026-11-13) — `images/engine-layout.png`

Placeholder blocks inside the ghosted engine; everything fits with room to spare.

- Axle on the original crank line (y 83, z 52 mm), front pulley → flywheel.
- Worm wheel + worm + motor near the flywheel end; motor crosswise.
- Big pulley on the crank → blower in the upper block, front half.
- Atomizer next to the blower outlet, on the manifold side.
- Glycerin tank in the head, under the oil cap.

RC smoke unit options (rejected, kept for reference):

- CHICHIYANG 1/10, metal, split air pump + control board, 7.4–11.1 V, ~£39 — https://www.amazon.co.uk/CHICHIYANG-Simulation-Generator-Generation-Accessory/dp/B0CPQ6JN61
- MOOKEENONE 1/10, throttle-linked — https://www.amazon.co.uk/MOOKEENONE-Crawler-Generator-Simulator-Replacement/dp/B0BNDK6448
- AD-RC set incl. smoke chamber + 30 ml oil — https://www.ebay.co.uk/itm/112666123594
- 1/16 tank unit (smaller) — https://www.amazon.co.uk/NATEFEMIN-Simulation-Exhaust-Generator-Henglong/dp/B0C3BV16KX

Manifold sizes at 10 cm: ~57 mm long, pipes ~4–5 mm across → ~2.5 mm bore with 1 mm walls.
Bore must stay round and unsupported inside (supports can't be removed from a pipe).

## Motor

**Now: N20 geared motor, 6 V, ~300 rpm, 3 mm D-shaft, 12 × 10 × ~25 mm + gearbox.**

- https://www.ebay.co.uk/itm/267082315931 (GA12-N20, 300 rpm @ 6 V, 3 mm × 10 mm shaft)
- https://www.amazon.co.uk/Motor-30-3000RPM-Electric-Reduction-Motors/dp/B0DKXNB724 (choose 300 rpm)

Previously considered (dropped):

- 130/030-size DC motor: **25 mm long, 20 mm wide, 15 mm tall**
- Shaft: **2 mm diameter, 7.5 mm long** (enough for a pressed-on worm)
- Listing: https://www.ebay.co.uk/itm/397408355262

## Materials to order

Not verified by hand — check the bores before ordering: **worm 2 mm** (motor shaft), **wheel 3 mm** (axle).

| #   | Part                                                              | Link                                                                            | Note                                       |
| --- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------ |
| 1   | ~~Brass worm gear set, module 0.5, 1:25~~ (dropped — N20 instead) | https://www.ebay.co.uk/p/1494496719                                             | Reportedly 2 mm worm bore, 3 mm wheel bore |
| 2   | Brass worm gear sets, several modules/sizes (alternative)         | https://www.ebay.co.uk/itm/404552199513                                         | No 2 mm worm bore seen                     |
| 3   | Plastic gear pack, module 0.5, 200 pcs (backup)                   | https://www.amazon.co.uk/200pcs-Plastic-Single-Reduction-Electric/dp/B08GQ85R37 | Worms fit 130 motors                       |
| 4   | Plastic worm set for 130 motors, 11 pcs                           | https://www.amazon.co.uk/11pcs-K002B-Plastic-Motor-Parts/dp/B0F59XT6G4          | Needs a wheel from #3                      |
| 5   | 3 mm × 100 mm stainless rod, 5-pack (crank axle, fan axle)        | https://www.amazon.co.uk/sourcing-map-Diameter-Stainless-Steel/dp/B088PBSBTJ    | File the ends                              |
| 6   | Rubber band                                                       | —                                                                               | Belt, crank pulley → fan pulley            |

## Approach

1. **Identify parts** — labelled contact sheet of every mesh; confirm flywheel, fan, crank pulley, fan pulley. ← in progress
2. **Separate moving parts** — split merged meshes; flywheel, crank pulley, fan + pulley become their own prints.
3. **Simplify the body** — fuse the static parts into one solid (voxel remesh), drop detail finer than
   the nozzle can print, decimate to ~200k triangles.
4. **Hollow the block** — removable sump/lid for access; motor holder crosswise; worm/wheel clearance;
   3 mm axle holes through front and back; fan axle hole; wire exit.
5. **Shaft fittings** — 3 mm bores in flywheel and crank pulley; fan pulley bore for its axle; groove
   in pulleys for the rubber band.
6. **Export** — one STL per part, check in slicer, test-print the motor holder first.
7. **Adjust** when the gears arrive — measure and update holder/clearances.

## Open questions

- Confirm which meshes are the flywheel, fan, crank pulley and fan pulley (contact sheet).
- Exact gear dimensions once the parts arrive.
- Power: battery type and switch location.

## Version 1 — 2026-11-13

Folder: `output/v1/` — `preview.png`, `engine-assembly.usdz` (open with Quick Look), `engine-v1.blend`, and one STL per part.

| Part                             | File               | Notes                                                                                                                          |
| -------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| Block (body, hollow, 3 mm walls) | `block.stl`        | Axle hole Ø3.4 front→back on crank line; Ø3.0 blind hole for fan pin; oil-filler seat Ø6.5 × 6 + Ø4.2 hose hole down to cavity |
| Sump (removable)                 | `sump.stl`         | Split at z = 36 mm; Ø8 wire hole in the floor; original floor window closed with a 3 mm plate                                  |
| Oil cap (push-fit)               | `oil_cap.stl`      | Ø6.1 peg into the Ø6.5 seat                                                                                                    |
| Flywheel                         | `flywheel.stl`     | Ø3.1 bore (press fit on 3 mm rod)                                                                                              |
| Crank pulley                     | `crank_pulley.stl` | Hub added, Ø3.1 bore                                                                                                           |
| Fan + fan pulley (one piece)     | `fan.stl`          | Ø3.4 bore (spins on a 3 mm pin)                                                                                                |

Size: 150 × 133 × 165 mm. Parts exported in their assembled positions (not yet oriented for printing).

Not in v1 yet: N20 motor mount + drive gears, blower + its pulleys, atomizer holder, glycerin tank,
air intake from the air filter, hollow manifold + exhaust stub, screws/locating pins for sump, print orientation.
Inside of the block is rough (follows the original shape) — hidden, but worth smoothing later.

## How to rebuild from scratch (any session)

Everything is scripted. Project folder: `~/Development/Projects/3d/Models/Engine/`

- `build.sh` — one command: `./build.sh` (defaults: `source/engine-gltf.zip` → `output/latest/`) (~4 min).
  Needs Blender ≥ 4.5 at `/Applications/Blender.app` (MANIFOLD boolean solver). Verified from scratch 2026-11-13.
- `scripts/` — the stages, run in order by `build.sh`:

| Stage | Script                                                              | What it does                                                                                                                                                                                                                                                                                                                                                     |
| ----- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | `build1.py` (+`common.py`)                                          | Import glTF, rotate 180° about X (file is upside down), scale so length = 150 mm, bake transforms; split loose pieces to pick moving parts (flywheel = Mesh_115 near axis; crank pulley = Mesh_25 + Mesh_17 hub on axis; fan = Mesh_17 + Mesh_138 on fan axis y56 z89); drop belt Mesh_3; keep crankshaft Mesh_104 aside; voxel-remesh body 0.3 mm, parts 0.2 mm |
| 2     | `build2.py`                                                         | Delete small loose shells; close the window in the sump floor (2D hole fill, 3 mm plate at floor height); plug rear main-seal hole; voxel grid 1 mm; **outside = seen along any of 6 axis rays**; filler (solid eroded 3) unioned in; cavity = solid eroded 4 voxels (≈3 mm walls) inside core box, connected to the centre                                      |
| 3     | `build3.py` (+`helpers.py`)                                         | Cut cavity; axle Ø3.4 along x at (y83, z52); fan pin Ø3.0 at (y56, z89); wire hole Ø8 in sump floor; oil cap (Ø17.2 cut at (90.5, 76.5), z>146) + Ø6.1 peg, seat Ø6.5 × 6, hose Ø4.2; split sump at z = 36 inside x28–146, y50–118; bores: flywheel/crank pulley Ø3.1 (crank pulley gets Ø9 hub), fan Ø3.4                                                       |
| 4     | `build4.py`                                                         | N20 drive: motor axis 16.2 mm from axle at 210° (y 69.0, z 43.9), found by searching the cavity; sleeve 12.4 × 10.4 inner, 1.6 walls, x 75–95, open at the front, lip with Ø5 hole, web fused to the side wall; clearance pocket; two 16T module-1 involute gears, 5 mm wide, x 98.5–103.5 (axle gear Ø3.1 + hub, motor gear D-bore 3.1/2.6)                     |
| —     | `export.py`                                                         | Drop loose bits, decimate, write STLs + `engine-assembly.usdz` + `engine.blend`                                                                                                                                                                                                                                                                                  |
| —     | `view.py`, `explode.py`, `section.py`, `drivesec.py`, `sumpview.py` | Preview renders used to check each step                                                                                                                                                                                                                                                                                                                          |

All coordinates are mm in the 150 mm model, x = front (fan) → back (flywheel), z up.

## Version 2 — 2026-11-13

Folder: `output/v2/` (supersedes v1 — v1's hollow missed the crankcase).
New: proper hollow through the crankcase and sump (≈3 mm walls), N20 motor sleeve in the block,
`gear_axle.stl` + `gear_motor.stl`, `drive-cutaway.png`.

Assembly order (draft): sump off → slide motor into sleeve from the front end (wires toward the front) →
press motor gear on → push 3 mm rod in from the back through the axle gear → flywheel on the back, crank pulley on the front.

### Viewing the .blend (2026-11-13)
The model is in mm but Blender treats 1 unit as 1 m, so the engine looked 150 m big and the view started inside it.
`scripts/viewsetup.py` (called by `export.py`) sets units to mm (scale 0.001), frames the view on the engine
and sets clip end 20 000. If the view is ever empty: in the 3D view press Home (View → Frame All).

### Filament estimate (v2, 2026-11-13)
Solid volumes: block 254 cm³, sump 26, flywheel 12.7, fan 6.9, crank pulley 2.1, gears 1.1 + 0.9, oil cap 1.1 → ~305 cm³.
PLA at 1.24 g/cm³ = ~380 g if 100% solid; with normal infill (~15–20%) plus supports, roughly **250–350 g**.
A 1 kg spool is enough, including test pieces. User has no motor and not enough filament yet (2026-11-13) — printing deferred.

## Repository (2026-11-13)

Lives in `github.com/marcelovani/3d` (public) under `Models/Engine/`. Not committed (see root `.gitignore`):
`work/` and `output/` (rebuild with `./build.sh`). `source/engine-gltf.zip` is committed (CC BY 3.0, see below).

### Source licence (checked 2026-11-13)
Icosa Gallery page https://icosa.gallery/view/59QBP8GiT0q: "Internal Combustion Engine", by T-FLEX CAD ST (Free)
from Sketchfab, uploaded by Devin Marble, **CC BY 3.0**. Sharing and changing allowed with credit, licence link
and a note of changes → `source/engine-gltf.zip` is committed with `source/ATTRIBUTION.md`. The 86 MB `.usdz`
copy is not committed (unused, near GitHub's 100 MB limit).

## Version 3 — smoke system and separate parts (2026-11-13)

### Decisions (user, 2026-11-13)
| # | Decision | Why |
|---|----------|-----|
| 12 | Add-on parts printed separately: exhaust manifold, intake manifold + carburettor, air filter, alternator, oil filter (plus sump, rocker cover, oil cap, flywheel, fan, pulleys, gears) | Easier to print and assemble; **each can be a different PLA colour** |
| 13 | Parts joined with small screws: **1.5 mm starter holes**, user drills/screws | No tight printed fits needed |
| 14 | Rods: **2 mm starter holes** in pulleys, flywheel, fan, gears, plate bosses — user drills to the rod size. Exception: the long crank axle hole through the block stays full size (Ø3.4) so it runs straight; the motor gear keeps its exact D-bore | User has metal rods and drills |
| 15 | Removable **rocker cover** (split z = 127) | Top access to blower, atomizer, tank, hose |

### Smoke system layout (`scripts/build5.py`)
- **Smoke module** = one separate part (purple in `images/v3-exploded.png`): plate + rod bosses + blower housing + duct + atomizer
  chamber. Assemble on the bench (impeller, lid plug, atomizer), lower in from the top with the rocker cover off, fix with
  2 screws through the block's -y wall at z 75 and 88 (x 63.5). The block gets a 0.4 mm clearance around it.
  (First try had it fused into the block — the impeller could not be fitted, so it was split out.)
- **Plate**: cavity cross-section at x 62–65 shrunk ~1 voxel so it drops in, z 70–127.
- **Belts** on the front side of the plate: crank inner pulley Ø28 (x 55–61, on the axle) → intermediate small Ø8;
  intermediate big Ø22 (x 49–55) → blower pulley Ø8. Ratio ≈ 3.5 × 2.75 ≈ 9.6 → ~2,900 rpm blower at 300 rpm crank.
  Intermediate rod at (y 84, z 85), blower rod at (y 80, z 118).
- **Blower**: scroll housing Ø25 inside, x 65–76 behind the plate, open at the back for the **blower_lid** (Ø9 inlet);
  **impeller** Ø22, 8 blades.
- **Blower lid**: push-in plug (no flange) x 74–76 with a Ø9 inlet; impeller blades end at x 73.4.
- **Atomizer chamber**: vertical tube ID 10.6 at (x 84, y 89), z 98–127, open at the top under the rocker cover; **chamber_cap**
  has a nipple for the glycerin hose (from the oil-cap filler) and a wire slot. Air enters at the top (duct from the housing,
  z 121–125.5), passes through the atomizer, leaves by the **outlet nipple** at the bottom (z 102, pointing +x).
- **Smoke gallery** (in the block): tube ID 4.5 along x at (y 100, z 106), x 49–132, with an **inlet nipple** pointing up at x 72.
  Join the chamber outlet nipple to it with a short piece of the 4 mm hose. Drilled into each of the 4 exhaust ports
  (found from the manifold channel: x 55, 79, 103, 127; y 104; z 110). The module is notched where the gallery passes.
- **Exhaust manifold** (separate part): hollowed by voxel erosion (0.4 mm grid, 1.2 mm walls) of the original Mesh_0;
  **exhaust stub** Ø7/Ø4 from the collector outlet (≈ x 95, y 120, z 74) down to z 58, then straight back to x 152
  (first try went down to z 30 and ran through the sump).
- **Air intake**: Ø5 hole down through the air filter, carburettor and intake into the head (path found by search, x 88, z 110).

### Add-on part boxes (`scripts/build1.py`, islands fully inside go to the part)
air_filter (46,-4,138)–(110,57,172) · intake_manifold (38,-4,92)–(134,63,150) · alternator (12,18,36)–(58,60,90) ·
oil_filter (8,93,6)–(52,134,82) · exhaust_manifold (33,101,60)–(137,142,130).

### Stage 1 change: add-ons cut out of the fused block
Fusing the block alone (without the add-ons) dropped whole walls, because the voxel fuse leaks through the open ports.
So the block is fused **with** the add-ons and each add-on is then cut out grown by 0.4 mm (also the fitting gap).
Stage 2 counts the add-ons as walls for the inside/outside test but keeps the filler out of them.
Stage 3 cuts 0.5 mm clearance around flywheel, crank pulley and fan; stage 6 re-cuts 0.3 mm around the add-ons.

### Checks
- `scripts/overlap.py` lists parts whose surfaces intersect. v3 final: only faces meant to touch (sump/cover split faces,
  oil cap and chamber cap seats, the two gears).
- `scripts/explode.py` renders the coloured exploded view.

### Screw starter holes (`scripts/build6.py`)
Sump 4, rocker cover 4 (vertical, in solid wall), exhaust 2, intake 2, oil filter 2, air filter → intake 2, smoke module 2.
Alternator: the holes did not reach into the alternator body (log warning) — drill those by hand when fitting.

### Known issues
- Some recesses on the block sides are filled flat (filler shows through where the original surface was open). Cosmetic.
- Wall check near the atomizer chamber flagged a few points closer than 2 mm to the outside (v3 first try) — pockets removed.

## Version 4: clean parts from the original (2026-11-13)

**Why:** the v3 STLs had holes and missing pieces. Three causes: the original is a display model
made of open surfaces; the v3 voxel remesh at 0.25–0.3 mm lost thin details; and the boolean
cuts plus decimation opened gaps. Decision: take each part straight from the original, make it
solid on its own, and work out the joins (axle, gears, screws, smoke system) later.

**How** (`scripts/v4/extract.py`, no booleans, no decimate):
1. Select the parts with the same boxes as v3 `build1.py`. The block is everything else; the belt (M3) is dropped.
2. Sample each part's surface into a voxel grid: 0.1–0.12 mm for small parts, 0.25 mm for the block.
3. Solid = every voxel that can't be seen from outside along any of the 6 axis directions.
4. Mesh it with OpenVDB (`convertToPolygons`, after a light 1-2-1 blur). The result is watertight by construction.
5. Drop loose pieces under 5% of the biggest (floating bolts, wires).
6. Block: fill it using every part's surface, so openings hidden behind the add-ons stay closed. Then remove each add-on and moving part from it, in voxel space.

**Run** (about 11 min; output/v4 is git-ignored):
```
cd Models/Engine
/Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/v4/extract.py -- scripts work/src/scene.gltf output/v4 [part ...]
/Applications/Blender.app/Contents/MacOS/Blender -b output/v4/engine-parts.blend -P scripts/v4/partviews.py -- output/v4/views
```
`work/src/scene.gltf` is unzipped from `source/engine-gltf.zip`, the same as stage 1 of build.sh.

**Parts:** block, flywheel, crank_pulley, fan, air_filter, intake_manifold, alternator, oil_filter, exhaust_manifold.

**Known issues:**
- Islands centred in an add-on box that stick out by no more than 15 mm now go to that add-on, which moved most of the carburettor off the block. One small bracket is still on top of the block.
- A few hundred to about 1,500 non-manifold edges on the block, air filter, intake and alternator, where two surfaces touch. Slicers usually repair these.
- Rocker cover and sump are still part of the block; they'll be split when we design the joins.

**Status (2026-11-14): parked.** v4 is better than v3 but still not good enough: Cura shows lots of
orphan edges. Next: Marcelo will simplify the source model himself, then we try again with a
simpler approach on the simplified source.

## Version 5: virtual scan of the simplified source (2026-11-21)

**Source:** Marcelo simplified the model by hand in Blender (`work/strip1..8.blend`). `strip7.blend` is
copied to `source/engine-simplified.blend` and is the source from here on: 28 pieces, 2.2M triangles,
already upright, all pieces in their assembled position. `strip8.blend` is the same file with the cylinder
head moved aside and the rocker cover and oil cap lifted (an exploded view); the shapes are identical.

**Approach ("virtual 3D scanner", `scripts/v5/scan.py`)**, each piece on its own:
1. Scale so fan to flywheel (x) is 150 mm (factor 229.25), min corner at 0, orientation unchanged.
2. Sample the surface every G/2 into a voxel grid, 20,000 triangles at a time. G = piece size / 450, between
   0.08 and 0.25 mm (raised automatically if a rotated grid would pass 400M voxels).
3. A voxel is outside if a straight ray from it reaches open space without hitting the surface. Rays go in
   78 directions: the 6 axis directions plus 6 for each of 12 random rotations (seed 1). That carves
   pockets at an angle too, which v4's 6 directions could not.
4. Solid = not outside, plus the surface thickened to at least 0.6 mm (single-sided sheets and thin fins
   would otherwise print as nothing, and they caused v4's broken edges).
5. Mesh with OpenVDB after a light blur, adaptivity 0.1 (block: 3.1M -> 1.1M triangles, 157 -> 56 MB,
   still closed); drop loose crumbs under 1% of the biggest piece; count non-manifold edges and vertices
   (0 on every piece tested).

**Disk-full incident (2026-11-21):** the first full run sampled every point of a piece at once (the block
alone was 900M+ points) and kept them for all 12 rotations. Blender pushed 38 GB into macOS swap and the
disk filled up. Fixed: points are sampled in chunks straight into the grid, and the rotations use the
surface voxel centres (1.4M for the block) instead of the raw points. The block now peaks at 3.6 GB of
memory and takes about 70 s. Run long scans with a memory watchdog that kills Blender above 10 GB (see
the command below).

**Run** (output/ is git-ignored; `mkdir -p output/v5` first):
```
cd Models/Engine
(/Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/v5/scan.py -- source/engine-simplified.blend output/v5 [meshNN ...] > output/v5/log.txt 2>&1 & B=$!; while kill -0 $B 2>/dev/null; do [ "$(ps -o rss= -p $B | tr -d ' ')" -gt 10000000 ] && kill $B; sleep 2; done)
/Applications/Blender.app/Contents/MacOS/Blender -b output/v5/scan.blend -P scripts/v5/sheet.py -- output/v5/contact-sheet.png 4
```
Writes one STL per piece, named after the Blender object (`mesh13.stl` …), plus `scan.blend` and a contact sheet.

### v5 step 2: merge, split and name the pieces (2026-11-21)

`images/v5-source-pieces.png` numbers the 28 source pieces (biggest first). Marcelo chose:
- merge 3+10+22+20+16 into the cylinder head, with no gaps;
- merge 9+25 into the sump;
- split 4, 17, 23 and 26, which each held two separate parts.

`scripts/v5/prepare.py` does it. It bakes world transforms, joins with `object.join`, and splits by k-means on
loose-island centres weighted by island size. A plain box-overlap clustering kept the alternator in one
piece, because small bolts bridge it to the water pump. It then renames everything and writes
`source/engine-parts.blend` + `.obj`. The original `engine-simplified.blend` is never changed.
```
/Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/v5/prepare.py -- source/engine-simplified.blend source/engine-parts.blend
/Applications/Blender.app/Contents/MacOS/Blender -b source/engine-parts.blend -P scripts/v5/sheet.py -- images/v5-parts.png 4 z
```
`sheet.py ... z` orders the parts from the top of the engine down: `images/v5-parts.png`.

Gaps measured (BVH nearest point, mm): 15–16 0.0, 26–72 0.0, 72–head 0.12, which the scan's 0.6 mm wall
closes on its own. **16 (mesh74) doesn't touch the head**: it is 3.6 mm away, and it sits on mesh28
(0.34 mm), which sits on the intake manifold (0.43 mm). So it was left out of the head, pending
Marcelo's decision.

Names were proposed from position: crank axis at y 87, z 52; fan axis at y 60, z 90 (mm, in the scan
frame). The table is in `prepare.py` `NAME`, still to be confirmed by Marcelo. The guesses most likely
to be wrong are the thermostat group (mesh28/74/9) and `head_front_cover` (mesh11).

### v5 step 3: second round of merges, deletes and gap fixes (2026-11-21), 21 parts

Marcelo's decisions, all in `prepare.py`:
1. thermostat cover + ring + disc + housing are now one `thermostat_housing`. It sits on the intake
   manifold, not the head (mesh74 never touched the head).
2. The names were approved.
3. `water_pump_hub` is merged into `water_pump`. `washer` and `rear_oil_seal` are deleted: both were
   paper-thin and nothing rested on them. The exhaust manifold meets the head, and the rear plate meets
   the block and the flywheel, at 0 mm either way.
4. `crank_pulley_bolt` becomes `crank_pin`, merged into `timing_cover`. The crank pulley slides onto it.
   - The pin keeps the shank, Ø3.66 mm, from where the head ended (head cut off) back 6.2 mm.
   - The timing cover has an 11 mm hole on the crank line, and the block's crank tunnel is open behind
     it, so the pin alone touched nothing. A plug, Ø12.2 mm and 2 mm deep, fills the hole and overlaps
     its rim by 0.6 mm.
   - The pulley bore is about Ø5.5, so it has about 0.9 mm clearance on the pin.

Gaps closed with `snap()`: the smaller part moves straight along the nearest-point vector until it
touches, plus 0.05 mm of overlap.

| Part moved | Onto | Moved (mm) |
| --- | --- | --- |
| thermostat top | thermostat housing | 0.39 |
| thermostat housing | intake manifold | 0.48 |
| water pump hub | water pump | 1.40 |
| oil cap | rocker cover | 0.65 |
| oil filter | timing cover | 0.14 |
| carburettor, with the air filter | intake manifold | 1.06 |

`scripts/v5/contacts.py` lists every pair closer than 3 mm and each part's nearest neighbour.
Afterwards every static part touches at least one other. The only gap left is the crank pulley, 0.07 mm
from the timing cover, on purpose, because it spins.
```
/Applications/Blender.app/Contents/MacOS/Blender -b source/engine-parts.blend -P scripts/v5/contacts.py
```
Open point: the earlier motor plan ran a 3 mm steel axle along the crank line to turn the crank
pulley. A solid pin there means the pulley is no longer driven by that axle.

### v5 step 4: third round of merges (2026-11-21), 14 parts

Numbers are from the 21-part sheet.
1. 6+7: `cylinder_head` now includes `head_front_cover`.
2. 4+8: `intake_manifold` now includes the carburettor.
3. 11+12: `fan` now includes `fan_pulley`.
4. 13+14+16+17+20: `block` now includes the timing cover (with the crank pin), alternator, rear plate and oil filter.
5. On hold, 5 (thermostat_housing) into the head: it sits on the intake manifold and is 2.0 mm from the head.
   Suggested putting it with the intake instead.

The timing cover (0.71 mm) and the alternator (0.47 mm) had gaps to the block. They were filled with
`bridge()` instead of `snap()`, because moving the timing cover would push it into the sump and water
pump, which stay separate. `bridge()` copies every face of the part lying within 1.6 mm of the block and
extrudes it onto the block (+0.1 mm), giving closed pads. Nothing moves, and the result is invisible from
outside.

`contacts.py` afterwards: every part touches another, except the crank pulley (0.07 mm, it spins).
The flywheel touches the block (rear plate) at 0.001 mm. It spins too, so it will need clearance when
the joins are designed.

### v5 step 5: thermostat into the intake, water pump cleaned up (2026-11-21), 13 parts

1. `thermostat_housing` is merged into `intake_manifold`: it sits on the intake (0.014 mm) and is 2 mm from the head.
2. `rehome_loose('water_pump', max_size=10)` sorts the pump's loose pieces.
   - Islands count as linked when within 0.15 mm, tested both ways. One way missed contacts: a small
     island's vertex can sit on a big island's face.
   - Bits under 10 mm move to the part they touch: a 7 mm tab with a peg and a 4 mm sliver, both
     touching the block at 0 mm.
   - Bigger pieces belong to the part. They stay, and `bridge()` fills their gap to the body, up to their
     measured gap + 0.5 mm.
   - The pump in the source is a stack of pieces with real gaps between them: body, ring, rear outlet
     housing and front flange, with gaps up to 3.6 mm. Filled, it scans as 1 solid (40 crumbs dropped).
   - Bug fixed on the way: deleting the first bit renumbered the vertices, so later bits copied and
     deleted the wrong ones. It now plans every move first, copies all bits out, then deletes once.
3. `run.sh` now reads `SRC` (default `source/engine-parts.blend`), so the scan works on the prepared parts.

Lesson: other parts may also be stacks of pieces with gaps. Check each scan's `pieces` count, which
should be 1, and fix any part that comes out in more than one piece the same way.

### v5 step 6: correction, the thermostat housing belongs to the head (2026-11-21)

Marcelo asked for 6+7+5 (head + head_front_cover + thermostat_housing). I argued it sat on the intake,
because it was 0.43 mm from the intake and 1.83 mm from the head, then snapped it 0.48 mm onto the intake
and merged it there. **He was right.** A gap that is the same all the way round can mean a spigot sitting
in a hole, and nearest distance alone doesn't show which part something is fixed to. Ask, don't argue
from one measurement.

Now: no snap onto the intake, so the housing stays where the source put it. `bridge()` fills its side
gap to the head (up to 2.33 mm, 758 faces), then it is merged into `cylinder_head`. The head test-scans
as 1 solid, 0 non-manifold edges, peak 3.7 GB. Steps 4 and 5 above, which put it in the intake, are
replaced by this.

### v5 step 7: water pump into the block, alternator pin recovered (2026-11-21), 12 parts

1. 7+10: `block` now includes `water_pump` (touching, 0.001 mm).
2. **Alternator pin.** The hand simplification deleted the alternator's insides, so the pulley had nothing
   to sit on.
   - `scripts/v5/recover.py` finds islands of the original `source/engine.usdz`, which has the same
     coordinates as `engine-simplified.blend`, that lie in a region and are missing from the simplified
     file.
   - Region: a cylinder on the alternator pulley's axis (mesh120, the half with lower y), radius 15 mm,
     from the pulley's back face to 35 mm behind it.
   - `:shaft` keeps only thin pieces on the axis (radius 2.2 mm or less). They may pass through the
     pulley but not stick out in front.
   - Marcelo: "we only need the pin to be part of the alternator+block because the pulley will go onto
     the pin".
   - Result: 468 islands, 40.6 mm long, starting 4.2 mm behind the pulley's front face. Saved as
     `source/alternator-shaft.blend`, which is committed because `engine.usdz` is not.
   - Earlier tries pulled in the whole interior: 1,670 islands of rotor, windings, nut, washers and the
     original pulley's own pieces, which clashed with the separate pulley part.
   ```
   /Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/v5/recover.py -- source/engine.usdz source/engine-simplified.blend source/alternator-shaft.blend alternator_shaft "cyl:mesh120/pulley:15:35:shaft"
   ```
3. `attach_all(new, base)` splits the recovered object into pieces. Islands are linked when within
   0.15 mm, tested both ways; bounding boxes alone are not enough, because a ring's box contains
   everything inside it. Pieces touching the base join directly, and the rest are bridged nearest first,
   up to 5 mm. The shaft came as 3 pieces, all bridged, with gaps of 1.1 to 2.5 mm.
4. Scan memory cut: `seen()` and `blur()` no longer make full-size temporary copies (no `np.roll`, flipped
   views, in-place `not`), and the grid is handed to `to_mesh` without a second reference. The block
   (12-part version) scans to 1 solid, 0 non-manifold edges, peak 2.6 GB, down from >4 GB.
5. Test-scan finding, using closed solids (an inside test on the open-shell source is meaningless):
   - The pulley's back already overlaps the alternator front by up to about 2 mm in the original model,
     with or without the pin.
   - The pin scans to about Ø5 mm, against the pulley bore of Ø3.86 mm.
   - Both need clearance cuts when the joins are designed.

**In git (2026-11-21):** `source/engine-simplified.blend` (Marcelo's hand-simplified source, 65 MB) and
`source/alternator-shaft.blend` are committed. `source/engine-parts.blend` and `.obj` are git-ignored:
`prepare.py` rebuilds them, and the .obj is 181 MB, over GitHub's 100 MB file limit.

# Merge, split and rename pieces of the simplified source, as Marcelo decides them.
# Reads source/engine-simplified.blend (never changed), writes source/engine-parts.blend and .obj.
# Usage: blender -b -P prepare.py -- <in.blend> <out.blend>
#
# MERGE: new name -> source objects joined into one (numbers are from images/v5-source-pieces.png)
# SPLIT: source object -> how many parts to split it into (loose islands clustered by position;
#        the biggest N clusters are the parts, every small loose bit joins the nearest part)
# NAME:  source object -> new name, for pieces kept as they are
import sys, os
argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[:2]
import bpy, bmesh, numpy as np

MERGE = {
    'cylinder_head': ['mesh15', 'mesh16', 'mesh26', 'mesh72'],   # sheet 3+10+22+20 (16 = mesh74 kept apart: it sits on 11, not the head)
    'sump': ['mesh18', 'mesh20'],                                 # sheet 9+25 (sump + its gasket)
}
SPLIT = {'mesh131': 2, 'mesh25': 2, 'mesh120': 2, 'mesh9': 2}    # sheet 4, 17, 23, 26
NAME = {    # proposed 2026-11-21 from position (crank axis y87 z52, fan axis y60 z90, mm); Marcelo to confirm
    'mesh13': 'block', 'mesh40': 'rocker_cover', 'mesh83': 'oil_cap', 'mesh22.007': 'air_filter',
    'mesh70.007': 'carburettor', 'mesh35': 'intake_manifold', 'mesh0': 'exhaust_manifold',
    'mesh137': 'timing_cover', 'mesh11': 'head_front_cover', 'mesh2': 'oil_filter',
    'mesh115': 'flywheel', 'mesh136': 'rear_plate', 'mesh5': 'rear_oil_seal',
    'mesh17': 'fan', 'mesh138': 'fan_pulley', 'mesh131_b': 'water_pump', 'mesh25_a': 'water_pump_hub',
    'mesh131_a': 'alternator', 'mesh120_a': 'alternator_pulley',
    'mesh25_b': 'crank_pulley', 'mesh120_b': 'crank_pulley_bolt',
    'mesh28': 'thermostat_housing', 'mesh74': 'thermostat_cover', 'mesh9_a': 'thermostat_ring', 'mesh9_b': 'thermostat_disc',
    'mesh54': 'washer',
}
DELETE = ['washer', 'rear_oil_seal']   # paper-thin; nothing sits on them, so no gap is left

bpy.ops.wm.open_mainfile(filepath=SRC)
# bake world transforms into the meshes and drop the parent empties, so joins and splits are exact
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    mw = o.matrix_world.copy(); o.data = o.data.copy(); o.parent = None
    o.data.transform(mw); o.matrix_world.identity()
for o in [o for o in bpy.data.objects if o.type != 'MESH']: bpy.data.objects.remove(o)
O = bpy.data.objects

def join(names, new):
    objs = [O[n] for n in names]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join()
    objs[0].name = new; objs[0].data.name = new
    print('MERGE', new, '<-', '+'.join(names), flush=True)

def split(name, n):
    o = O[name]; me = o.data
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    # loose islands
    isl = np.full(len(bm.verts), -1); k = 0
    for v in bm.verts:
        if isl[v.index] >= 0: continue
        st = [v]; isl[v.index] = k
        while st:
            x = st.pop()
            for e in x.link_edges:
                y = e.other_vert(x)
                if isl[y.index] < 0: isl[y.index] = k; st.append(y)
        k += 1
    co = np.array([v.co for v in bm.verts]); bm.free()
    size = np.bincount(isl).astype(float)
    cen = np.array([co[isl == i].mean(0) for i in range(k)])
    # k-means on island centres, weighted by island size: parts that sit apart end up in different
    # groups even when small bits (bolts) bridge them. Seeds: the biggest island, then the farthest
    # sizeable island from the seeds already chosen.
    sizeable = size >= size.max() * 0.05
    seeds = [int(np.argmax(size))]
    while len(seeds) < n:
        d = np.min([np.linalg.norm(cen - cen[s], axis=1) for s in seeds], axis=0) * sizeable
        seeds.append(int(np.argmax(d)))
    C = cen[seeds].copy()
    for _ in range(50):
        lab = np.argmin(np.linalg.norm(cen[:, None] - C[None], axis=2), axis=1)
        C = np.array([np.average(cen[lab == p], axis=0, weights=size[lab == p]) for p in range(n)])
    part_of = {i: int(lab[i]) for i in range(k)}
    vpart = lab[isl]
    # one object per part: copy the object and delete the other parts' vertices
    for p in range(n):
        c = o.copy(); c.data = me.copy(); bpy.context.scene.collection.objects.link(c)
        c.name = f'{name}_{chr(97 + p)}'
        b2 = bmesh.new(); b2.from_mesh(c.data); b2.verts.ensure_lookup_table()
        bmesh.ops.delete(b2, geom=[v for v in b2.verts if vpart[v.index] != p], context='VERTS')
        b2.to_mesh(c.data); b2.free()
        print('SPLIT', name, '->', c.name, 'islands', int(sum(1 for i in part_of if part_of[i] == p)), 'verts', len(c.data.vertices), flush=True)
    O.remove(o)

from mathutils import Vector
from mathutils.bvhtree import BVHTree
K = 229.252                     # Blender units -> mm (fan to flywheel = 150 mm)
OVERLAP = 0.05 / K              # parts snapped together overlap by 0.05 mm, so nothing is left touching at a single point

def tree(o):
    bm = bmesh.new(); bm.from_mesh(o.data); t = BVHTree.FromBMesh(bm); bm.free(); return t

def gap(a, b):
    """Smallest distance between two parts, and the move that closes it (from a towards b)."""
    tb = tree(O[b]); best = (1e9, None)
    for v in O[a].data.vertices:
        loc, _, _, d = tb.find_nearest(v.co)
        if loc is not None and d < best[0]: best = (d, loc - v.co)
    ta = tree(O[a])
    for v in O[b].data.vertices:
        loc, _, _, d = ta.find_nearest(v.co)
        if loc is not None and d < best[0]: best = (d, v.co - loc)
    return best

def snap(a, b, also=()):
    """Move part a (the smaller one) straight towards b until they touch; parts in `also` sit on a and move with it."""
    d, mv = gap(a, b)
    if d * K < 0.01: print('SNAP', a, '->', b, 'already touching', flush=True); return
    mv = mv + mv.normalized() * OVERLAP
    for n in (a, *also): O[n].data.transform(__import__('mathutils').Matrix.Translation(mv))
    print('SNAP', a, '->', b, 'moved %.3f mm (gap was %.3f mm)' % (mv.length * K, d * K), ('with ' + ', '.join(also)) if also else '', flush=True)

def bridge(a, b, max_gap=1.6):
    """Fill the gap between part a and part b without moving either: every face of a lying within
    max_gap mm of b is copied and extruded until it reaches b (+0.1 mm), forming closed pads."""
    tb = tree(O[b]); me = O[a].data
    near = {}
    for v in me.vertices:
        loc, _, _, d = tb.find_nearest(v.co)
        if loc is not None and d * K < max_gap: near[v.index] = (loc, d)
    faces = [f for f in me.polygons if all(i in near for i in f.vertices) and max(near[i][1] for i in f.vertices) * K > 0.01]
    if not faces: print('BRIDGE', a, '->', b, 'nothing to fill', flush=True); return
    bm = bmesh.new(); vmap = {}
    for f in faces:
        for i in f.vertices:
            if i not in vmap: vmap[i] = bm.verts.new(me.vertices[i].co)
        bm.faces.new([vmap[i] for i in f.vertices])
    old = {v: i for i, v in vmap.items()}
    res = bmesh.ops.extrude_face_region(bm, geom=list(bm.faces), use_keep_orig=True)
    newv = [e for e in res['geom'] if isinstance(e, bmesh.types.BMVert)]
    # each new vertex was made from an original one at the same position: move it onto b, plus 0.1 mm
    tb2 = tb
    for v in newv:
        loc, _, _, d = tb2.find_nearest(v.co)
        if loc is not None and d > 0: v.co = loc + (loc - v.co).normalized() * (0.1 / K)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pad = bpy.data.meshes.new(a + '_bridge'); bm.to_mesh(pad); bm.free()
    po = bpy.data.objects.new(a + '_bridge', pad); bpy.context.scene.collection.objects.link(po)
    print('BRIDGE %s -> %s: %d faces within %.1f mm filled (largest gap %.2f mm)'
          % (a, b, len(faces), max_gap, max(near[i][1] for f in faces for i in f.vertices) * K), flush=True)
    join([a, a + '_bridge'], a)

def rehome_loose(part, tol=0.15, dry=False, max_size=None):
    """Find bits of `part` that touch neither the part's main body nor anything joined to it, and move
    each one into the other part it touches (within tol mm). Islands are linked when they come within
    tol mm of each other; the linked group with the most vertices is the main body."""
    me = O[part].data
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    isl = np.full(len(bm.verts), -1); k = 0
    for v in bm.verts:
        if isl[v.index] >= 0: continue
        st = [v]; isl[v.index] = k
        while st:
            x = st.pop()
            for e in x.link_edges:
                y = e.other_vert(x)
                if isl[y.index] < 0: isl[y.index] = k; st.append(y)
        k += 1
    co = np.array([v.co for v in bm.verts])
    fv = [[v.index for v in f.verts] for f in bm.faces]
    fisl = np.array([isl[f[0]] for f in fv])
    trees, lo, hi = [], [], []
    for i in range(k):
        idx = np.nonzero(isl == i)[0]; m = {g: j for j, g in enumerate(idx)}
        polys = [[m[g] for g in f] for f, fi in zip(fv, fisl) if fi == i]
        trees.append(BVHTree.FromPolygons([tuple(c) for c in co[idx]], polys) if polys else None)
        lo.append(co[idx].min(0)); hi.append(co[idx].max(0))
    lo, hi = np.array(lo), np.array(hi); t = tol / K
    par = list(range(k))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for i in range(k):
        cand = np.nonzero(np.all((lo[i] - t <= hi) & (hi[i] + t >= lo), axis=1))[0]
        for j in cand:
            if j <= i or f(i) == f(j) or trees[j] is None: continue
            # touching is tested both ways: a small island's vertex can sit on a big island's face
            # while none of the big island's vertices is near the small one
            if (trees[i] is not None and any((r := trees[i].find_nearest(Vector(c)))[0] is not None and r[3] <= t for c in co[isl == j])) \
               or any((r := trees[j].find_nearest(Vector(c)))[0] is not None and r[3] <= t for c in co[isl == i]):
                par[f(i)] = f(j)
    root = np.array([f(i) for i in range(k)])
    nverts = {r: int(np.isin(isl, np.nonzero(root == r)[0]).sum()) for r in set(root)}
    main = max(nverts, key=nverts.get)
    others = [o.name for o in O if o.type == 'MESH' and o.name != part]
    otrees = {n: tree(O[n]) for n in others}
    bm.free()
    # Plan first, change after: vertex indices are only valid until the first deletion.
    plan = []
    for r in [r for r in nverts if r != main]:
        vids = np.nonzero(np.isin(isl, np.nonzero(root == r)[0]))[0]
        best = (1e9, None)
        for n, tr in otrees.items():
            dd = min(tr.find_nearest(Vector(c))[3] for c in co[vids])
            if dd < best[0]: best = (dd, n)
        size = (co[vids].max(0) - co[vids].min(0)) * K
        big = max_size is not None and size.max() > max_size
        if dry:
            print('LOOSE-DRY %s: component %d, %d verts, %.1f x %.1f x %.1f mm, centre %s mm, nearest %s %.3f mm'
                  % (part, r, len(vids), *size, np.round(co[vids].mean(0) * K, 1), best[1], best[0] * K), flush=True)
            continue
        if not big and best[0] * K > tol:
            print('LOOSE %s: bit of %d verts (%.1f x %.1f x %.1f mm) touches nothing (nearest %s, %.2f mm); left in place'
                  % (part, len(vids), *size, best[1], best[0] * K), flush=True); continue
        plan.append((vids, big, best, size))
    if not plan: return
    # 1. copy every bit out of the untouched mesh
    bits = []
    for n_, (vids, big, best, size) in enumerate(plan):
        c = O[part].copy(); c.data = me.copy(); bpy.context.scene.collection.objects.link(c); c.name = f'{part}_bit{n_}'
        b2 = bmesh.new(); b2.from_mesh(c.data); b2.verts.ensure_lookup_table(); keep = set(vids.tolist())
        bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.index not in keep], context='VERTS'); b2.to_mesh(c.data); b2.free()
        bits.append(c.name)
    # 2. delete all of them from the part in one go
    gone = set(np.concatenate([p_[0] for p_ in plan]).tolist())
    b3 = bmesh.new(); b3.from_mesh(me); b3.verts.ensure_lookup_table()
    bmesh.ops.delete(b3, geom=[b3.verts[i] for i in gone], context='VERTS'); b3.to_mesh(me); b3.free()
    # 3. small bits join the part they touch; big pieces belong here, so fill their gap to the body and rejoin
    for name_, (vids, big, best, size) in zip(bits, plan):
        if big:
            print('LOOSE %s: piece of %d verts (%.1f x %.1f x %.1f mm) belongs here; filling its gap to the body'
                  % (part, len(vids), *size), flush=True)
            g = gap(name_, part)[0] * K
            if g > 5.0: print('LOOSE %s: piece is %.2f mm from the body, too far to fill; joined as is' % (part, g), flush=True)
            else: bridge(name_, part, max_gap=g + 0.5)
            join([part, name_], part)
        else:
            print('LOOSE %s: bit of %d verts (%.1f x %.1f x %.1f mm) moved to %s (touches at %.3f mm)'
                  % (part, len(vids), *size, best[1], best[0] * K), flush=True)
            join([best[1], name_], best[1])

def attach_all(new, base, tol=0.15, max_gap=5.0):
    """Join every loose piece of object `new` into `base` so nothing floats: pieces within tol mm of
    base (or of a piece already attached) join as they are; the rest are attached one at a time,
    nearest first, by filling their gap with bridge() - up to max_gap mm. Anything further is reported."""
    # split `new` into loose islands, then group islands that touch (bbox prefilter, BVH check both ways)
    me = O[new].data
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    lab = np.full(len(bm.verts), -1); k = 0
    for v in bm.verts:
        if lab[v.index] >= 0: continue
        st = [v]; lab[v.index] = k
        while st:
            x = st.pop()
            for e in x.link_edges:
                y = e.other_vert(x)
                if lab[y.index] < 0: lab[y.index] = k; st.append(y)
        k += 1
    bm.free()
    co = np.array([v.co for v in me.vertices])
    lo = np.array([co[lab == i].min(0) for i in range(k)]); hi = np.array([co[lab == i].max(0) for i in range(k)])
    t = tol / K
    par = list(range(k))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    # islands touch when a vertex of one is within tol of the other's surface, tested both ways
    # (boxes alone are not enough: a ring's box contains everything inside it)
    polys = {}
    for pf in me.polygons: polys.setdefault(lab[pf.vertices[0]], []).append(list(pf.vertices))
    trees = []
    for i in range(k):
        idx = np.nonzero(lab == i)[0]; m = {g: j for j, g in enumerate(idx)}
        pl = [[m[g] for g in pp] for pp in polys.get(i, [])]
        trees.append(BVHTree.FromPolygons([tuple(c) for c in co[idx]], pl) if pl else None)
    def near_(a, b):
        return trees[b] is not None and any((r := trees[b].find_nearest(Vector(c)))[0] is not None and r[3] <= t for c in co[lab == a])
    for i in range(k):
        for j in np.nonzero(np.all((lo[i] - t <= hi) & (hi[i] + t >= lo), axis=1))[0]:
            if j > i and f(i) != f(j) and (near_(i, j) or near_(j, i)): par[f(j)] = f(i)
    root = np.array([f(i) for i in range(k)])
    groups = {r: np.nonzero(np.isin(lab, np.nonzero(root == r)[0]))[0] for r in set(root)}
    # one object per piece
    names = []
    for n_, (r, vids) in enumerate(groups.items()):
        c = O[new].copy(); c.data = me.copy(); bpy.context.scene.collection.objects.link(c); c.name = f'{new}_{n_}'
        b2 = bmesh.new(); b2.from_mesh(c.data); b2.verts.ensure_lookup_table(); keep = set(vids.tolist())
        bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.index not in keep], context='VERTS'); b2.to_mesh(c.data); b2.free()
        names.append(c.name)
    O.remove(O[new])
    print('ATTACH %s: %d islands in %d pieces' % (new, k, len(names)), flush=True)
    def dist(n, tb):
        return min(tb.find_nearest(v.co)[3] for v in O[n].data.vertices) * K
    pending = list(names); touching = bridged = 0
    while pending:
        tb = tree(O[base])
        d = {n: dist(n, tb) for n in pending}
        near = [n for n in pending if d[n] <= tol]
        if near:
            join([base] + near, base); touching += len(near)
            pending = [n for n in pending if n not in near]; continue
        n = min(pending, key=d.get)
        if d[n] > max_gap:
            for m in pending: print('ATTACH %s: piece %s is %.2f mm away, not attached' % (new, m, d[m]), flush=True)
            for m in pending: O.remove(O[m])
            break
        bridge(n, base, max_gap=d[n] + 0.5); join([base, n], base); bridged += 1
        pending.remove(n)
    print('ATTACH %s -> %s: %d pieces touching, %d bridged' % (new, base, touching, bridged), flush=True)

def pin_from_bolt(bolt, targets, name):
    """Replace a bolt with a plain pin: same shank radius, starting where the head ended, running
    back along the bolt's axis until it is 1 mm inside the first target part it reaches."""
    v = np.array([x.co for x in O[bolt].data.vertices])
    lo, hi = v.min(0), v.max(0); c = (lo + hi) / 2
    ax = int(np.argmax(hi - lo))                                 # the bolt's long axis
    r = np.hypot(*(v[:, [i for i in range(3) if i != ax]] - c[[i for i in range(3) if i != ax]]).T)
    L = hi[ax] - lo[ax]; s = v[:, ax]
    head_at_low = r[s < lo[ax] + 0.25 * L].max() > r[s > hi[ax] - 0.25 * L].max()   # the head is the wide end
    tail = s > hi[ax] - 0.3 * L if head_at_low else s < lo[ax] + 0.3 * L
    shank_r = r[tail].max()                                      # widest point of the far 30%: the shank
    head = s[r > shank_r * 1.1]
    start = head.max() if head_at_low else head.min()            # where the head meets the shank
    dirn = 1.0 if head_at_low else -1.0                          # points away from the head
    q = [i for i in range(3) if i != ax]
    d = Vector((0, 0, 0)); d[ax] = dirn
    # The part behind usually has a hole on the bolt's line (the timing cover's crank seal hole), so the
    # pin alone touches nothing. Find the smallest ring of rays that all hit a target: that ring is the
    # hole's edge, and the hit distance is the depth of the face around it.
    found = None
    for t in targets:
        tr = tree(O[t])
        for rmm in np.arange(0, 15.01, 0.5):
            hits = []
            for a in np.linspace(0, 2 * np.pi, 13)[:-1]:
                p = c.copy(); p[ax] = start; p[q[0]] += rmm / K * np.cos(a); p[q[1]] += rmm / K * np.sin(a)
                h = tr.ray_cast(Vector(p), d); hits.append(h[3] if h[0] is not None else None)
            if all(h is not None for h in hits):
                if found is None or min(hits) < found[1]: found = (rmm / K, min(hits), t)
                break
    if found is None: raise SystemExit(f'pin from {bolt}: nothing behind it in {targets}')
    hole_r, face, host = found
    depth = 2.0 / K                                               # plug and pin go 2 mm past the face
    rot = {0: (0, np.pi / 2, 0), 1: (np.pi / 2, 0, 0), 2: (0, 0, 0)}[ax]
    def cylinder(r, a0, a1, nm):
        loc = c.copy(); loc[ax] = start + dirn * (a0 + a1) / 2
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=a1 - a0, location=tuple(loc), rotation=rot)
        ob = bpy.context.object; ob.name = nm; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        return nm
    cylinder(shank_r, 0.0, face + depth, name)                                    # the pin: shank only, head cut off
    cylinder(hole_r + 0.6 / K, face - OVERLAP, face + depth, name + '_plug')       # fills the hole, overlaps its rim 0.6 mm
    join([name, name + '_plug'], name)
    O.remove(O[bolt])
    print('PIN %s -> %s: radius %.2f mm, length %.2f mm; plug radius %.2f mm fills the %.1f mm hole in %s, %.2f mm behind'
          % (bolt, name, shank_r * K, (face + depth) * K, (hole_r + 0.6 / K) * K, 2 * hole_r * K, host, face * K), flush=True)
    return host

for new, names in MERGE.items(): join(names, new)
for name, n in SPLIT.items(): split(name, n)
for old, new in NAME.items():
    if old in O: O[old].name = new; O[new].data.name = new

# --- 2026-11-21, Marcelo's second round ---
for n in DELETE: O.remove(O[n]); print('DELETE', n, flush=True)
join(['thermostat_cover', 'thermostat_ring', 'thermostat_disc'], 'thermostat_top')
snap('thermostat_top', 'thermostat_housing'); join(['thermostat_housing', 'thermostat_top'], 'thermostat_housing')
# (thermostat_housing is no longer snapped onto the intake: Marcelo, 2026-11-21 - it belongs to the head)
snap('water_pump_hub', 'water_pump'); join(['water_pump', 'water_pump_hub'], 'water_pump')
host = pin_from_bolt('crank_pulley_bolt', ['timing_cover', 'block'], 'crank_pin')
join([host, 'crank_pin'], host)
# found by contacts.py: these touched nothing; move them down onto what they sit on
snap('oil_cap', 'rocker_cover')
snap('oil_filter', 'timing_cover')
snap('carburettor', 'intake_manifold', also=('air_filter',))
# --- 2026-11-21, Marcelo's third round (numbers from images/v5-parts.png, 21 parts) ---
join(['cylinder_head', 'head_front_cover'], 'cylinder_head')                       # 6+7 (5 held: it sits on the intake, 2 mm off the head)
join(['intake_manifold', 'carburettor'], 'intake_manifold')                       # 4+8, touching (0.003 mm)
join(['fan', 'fan_pulley'], 'fan')                                                # 11+12, touching (0.004 mm)
bridge('timing_cover', 'block')                                                    # 0.71 mm gap
bridge('alternator', 'block')                                                      # 0.47 mm gap
join(['block', 'timing_cover', 'alternator', 'rear_plate', 'oil_filter'], 'block')  # 13+14+16+17+20
# --- 2026-11-21, fourth round ---
# Marcelo (2026-11-21): the thermostat housing belongs to the head (his original 6+7+5), not the intake.
# Its side is 1.83 mm from the head; fill that gap and merge it into the head.
g = gap('thermostat_housing', 'cylinder_head')[0] * K
bridge('thermostat_housing', 'cylinder_head', max_gap=g + 0.5)
join(['cylinder_head', 'thermostat_housing'], 'cylinder_head')
rehome_loose('water_pump', dry=bool(os.environ.get('DRY')), max_size=10)   # bits < 10 mm go where they touch; bigger pieces stay, gap filled
# --- 2026-11-21, fifth round ---
join(['block', 'water_pump'], 'block')                                             # 7+10, touching (0.001 mm)
# The alternator's shaft was deleted in the hand simplification, leaving nothing for the pulley to sit on.
# Marcelo (2026-11-21): bring back only the pin, merged with the alternator + block; the pulley goes onto it.
# recover.py copied it from the original (source/engine.usdz, same coordinates):
#   blender -b -P scripts/v5/recover.py -- source/engine.usdz source/engine-simplified.blend \
#       source/alternator-shaft.blend alternator_shaft "cyl:mesh120/pulley:15:35:shaft"
with bpy.data.libraries.load(os.path.join(os.path.dirname(SRC), 'alternator-shaft.blend')) as (src_, dst_):
    dst_.objects = ['alternator_shaft']
for ob in dst_.objects: bpy.context.scene.collection.objects.link(ob)
if not os.environ.get('SKIP_SHAFT'): attach_all('alternator_shaft', 'block')
for o in O: o.data.name = o.name
bpy.ops.wm.save_as_mainfile(filepath=OUT)
bpy.ops.wm.obj_export(filepath=os.path.splitext(OUT)[0] + '.obj', export_materials=False)
print('PARTS', len([o for o in O if o.type == 'MESH']), flush=True)

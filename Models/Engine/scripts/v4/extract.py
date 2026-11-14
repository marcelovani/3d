# v4: take each part straight from the original model and make it a closed solid on its own.
# No boolean cuts, no decimate. Each part: sample its surface into a fine voxel grid, fill what
# is not seen from outside (6 axis directions), mesh it with OpenVDB (watertight by construction).
# The block is filled using every part's surface (so openings hidden behind add-ons stay closed),
# then the add-ons and moving parts are removed from it in voxel space.
# Usage: blender -b -P extract.py -- <scripts dir> <scene.gltf> <out dir> [part ...]
import sys, os
argv = sys.argv[sys.argv.index('--') + 1:]
SCRIPTS, SRC, OUT = argv[:3]
ONLY = set(argv[3:])
sys.path.insert(0, SCRIPTS)
from common import load, islands, bb
import bpy, bmesh, numpy as np, openvdb as vdb, time

T0 = time.time()
def log(*a): print('LOG', round(time.time() - T0), *a, flush=True)

P = load(SRC)
def mid(o): return o.name.split('.')[0]

# ---- part selection (same boxes as v3 build1.py) ----
CACHE = {}
def pick(n, cy, cz, r, x0, x1):
    got = []
    if n not in CACHE: CACHE[n] = islands(P[n])
    for p in list(CACHE[n]):
        a, b = bb(p); c = (a + b) / 2
        if x0 <= c.x <= x1 and ((c.y - cy) ** 2 + (c.z - cz) ** 2) ** .5 <= r and max(b.y - a.y, b.z - a.z) <= 2 * r + 2:
            got.append(p); CACHE[n].remove(p)
    return got
parts = {
    'flywheel': pick('115', 83, 52, 34, 136, 151),
    'crank_pulley': pick('25', 83, 52, 15, 10, 22) + pick('17', 83, 52, 8, 15, 22),
    'fan': pick('17', 56, 89, 30, 0, 12) + pick('138', 56, 89, 13, 3, 16),
}
GROUPS = {
    'air_filter':       ((46, -4, 138), (110, 57, 172)),
    'intake_manifold':  ((38, -4, 92), (134, 63, 150)),
    'alternator':       ((12, 18, 36), (58, 60, 90)),
    'oil_filter':       ((8, 93, 6), (52, 134, 82)),
    'exhaust_manifold': ((33, 101, 60), (137, 142, 130)),
}
taken = {id(p) for v in parts.values() for p in v}
def inside(a, b, lo, hi): return all(a[i] >= lo[i] for i in range(3)) and all(b[i] <= hi[i] for i in range(3))
def touches(a, b, lo, hi): return all(a[i] <= hi[i] and b[i] >= lo[i] for i in range(3))
for g in GROUPS: parts[g] = []
body = []
for o in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
    if id(o) in taken or mid(o) in ('M3',): continue          # M3 = belt (dropped)
    a, b = bb(o)
    if not any(touches(a, b, *GROUPS[g]) for g in GROUPS): body.append(o); continue
    for p in islands(o):
        pa, pb = bb(p)
        pc = (pa + pb) / 2
        for g, (lo, hi) in GROUPS.items():                      # first match wins (air filter before intake)
            # fully inside the box, or centred in it and sticking out by no more than 15 mm (carburettor bits)
            if inside(pa, pb, lo, hi) or (inside(pc, pc, lo, hi) and inside(pa, pb, [v - 15 for v in lo], [v + 15 for v in hi])):
                parts[g].append(p); break
        else: body.append(p)
parts['block'] = body
for k, v in parts.items(): log('part', k, 'objects', len(v))

# ---- surface sampling ----
def tris(objs):
    out = []
    for o in objs:
        me = o.data; me.calc_loop_triangles()
        co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        lt = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get('vertices', lt)
        out.append(co[lt.reshape(-1, 3)])
    return np.concatenate(out) if out else np.zeros((0, 3, 3), np.float32)

def sample(T, step):
    """Points on every triangle, no gap bigger than `step`."""
    e = np.maximum.reduce([np.linalg.norm(T[:, i] - T[:, (i + 1) % 3], axis=1) for i in range(3)])
    n = np.maximum(1, np.ceil(e / step)).astype(int)
    pts = [T.mean(1)]
    for k in np.unique(n):
        sel = T[n == k]
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1), indexing='ij'); m = i + j <= k
        u = (i[m] / k).astype(np.float32); w = (j[m] / k).astype(np.float32)
        pts.append((sel[:, None, 0] * (1 - u - w)[None, :, None] + sel[:, None, 1] * u[None, :, None]
                    + sel[:, None, 2] * w[None, :, None]).reshape(-1, 3))
    return np.concatenate(pts)

def surface_mask(T, org, G, shape):
    S = np.zeros(shape, bool)
    for c in range(0, len(T), 200000):
        p = sample(T[c:c + 200000], G * 0.5)
        idx = np.floor((p - org) / G).astype(int)
        ok = np.all((idx >= 0) & (idx < shape), axis=1); idx = idx[ok]
        S[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    return S

def fill(S):
    """Solid = every voxel not reachable by a straight axis ray from outside."""
    out = np.zeros(S.shape, bool)
    for ax in range(3):
        out |= ~np.logical_or.accumulate(S, axis=ax)
        out |= ~np.flip(np.logical_or.accumulate(np.flip(S, ax), axis=ax), ax)
    return ~out

def grid_for(T, G, pad=3):
    lo = T.reshape(-1, 3).min(0) - pad * G; hi = T.reshape(-1, 3).max(0) + pad * G
    return lo, tuple(np.ceil((hi - lo) / G).astype(int))

def blur(M):
    f = M.astype(np.float32)
    for ax in range(3):   # 1-2-1 smoothing along each axis
        f = (2 * f + np.roll(f, 1, ax) + np.roll(f, -1, ax)) / 4
    return f

def mesh(M, org, G, name, adapt=0.05):
    g = vdb.FloatGrid(0.5); g.copyFromArray(0.5 - blur(M)); g.transform = vdb.createLinearTransform(1.0)
    pts, tri, quad = g.convertToPolygons(isovalue=0.0, adaptivity=adapt)
    pts = pts * G + org
    faces = [tuple(f) for f in tri] + [tuple(f) for f in quad]
    me = bpy.data.meshes.new(name); me.from_pydata(pts.tolist(), [], faces)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=G * 0.01)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # drop loose crumbs (< 5% of the biggest piece: loose bolts, wires)
    isl = []; seen = set()
    for f in bm.faces:
        if f.index in seen: continue
        stack = [f]; grp = []; seen.add(f.index)
        while stack:
            x = stack.pop(); grp.append(x)
            for e in x.edges:
                for y in e.link_faces:
                    if y.index not in seen: seen.add(y.index); stack.append(y)
        isl.append(grp)
    big = max(len(i) for i in isl)
    kill = [f for i in isl if len(i) < big * 0.05 for f in i]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    log(name, 'tris', len(me.polygons), 'pieces', len(isl), 'kept', len(isl) - sum(1 for i in isl if len(i) < big * 0.05), 'non-manifold edges', nm)
    return o

os.makedirs(OUT, exist_ok=True)
def export(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.wm.stl_export(filepath=os.path.join(OUT, o.name + '.stl'), export_selected_objects=True, ascii_format=False)

RES = {'block': 0.25, 'flywheel': 0.12, 'crank_pulley': 0.1, 'fan': 0.1}
TRI = {k: tris(v) for k, v in parts.items()}
solids = {}
for k in parts:
    if k == 'block' or (ONLY and k not in ONLY): continue
    G = RES.get(k, 0.12); org, shp = grid_for(TRI[k], G)
    M = fill(surface_mask(TRI[k], org, G, shp)); solids[k] = (M, org, G)
    export(mesh(M, org, G, k))

if not ONLY or 'block' in ONLY:
    G = RES['block']; allT = np.concatenate(list(TRI.values())); org, shp = grid_for(allT, G)
    M = fill(surface_mask(allT, org, G, shp))                       # everything, so hidden openings stay closed
    for k in parts:                                                   # then take every other part out
        if k == 'block': continue
        if k not in solids:
            g2 = RES.get(k, 0.12); o2, s2 = grid_for(TRI[k], g2); solids[k] = (fill(surface_mask(TRI[k], o2, g2, s2)), o2, g2)
        m2, o2, g2 = solids[k]
        idx = np.argwhere(m2) * g2 + o2
        ii = np.floor((idx - org) / G).astype(int)
        ok = np.all((ii >= 0) & (ii < shp), axis=1); ii = ii[ok]
        M[ii[:, 0], ii[:, 1], ii[:, 2]] = False
        log('removed', k, 'from block')
    export(mesh(M, org, G, 'block', adapt=0.1))

for o in [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.name not in RES and o.name not in GROUPS]:
    bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'engine-parts.blend'))
log('done')

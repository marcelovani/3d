# v5: "virtual 3D scanner". Each piece of the simplified source is scanned on its own.
#
# A voxel is outside when a straight ray from it reaches open space without hitting the
# piece's surface. Rays are tested in 6 axis directions plus 6 per extra random rotation
# (ROTS=12 -> 78 directions), so pockets at an angle are carved too, not just straight ones.
# Solid = everything that is not outside. The surface itself is thickened to MIN_WALL so
# single-sided sheets and thin fins print, then OpenVDB meshes it (closed by construction).
#
# Usage: blender -b -P scan.py -- <source.blend> <out dir> [object names ...]
# Normally run through run.sh: one piece per Blender process, with a memory limit.
import sys, os, time
argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[:2]
ONLY = set(argv[2:])
import bpy, bmesh, numpy as np, openvdb as vdb

LENGTH = 150.0      # mm, fan to flywheel (x)
ROTS = 12           # extra scan rotations, 6 directions each
MIN_WALL = 0.6      # mm, thinnest wall after thickening
KEEP = 0.01         # drop loose pieces smaller than this share of the biggest one
ADAPT = 0.1          # OpenVDB adaptivity: merges flat areas into bigger triangles (0 = none)
T0 = time.time()
def log(*a): print('LOG', round(time.time() - T0), *a, flush=True)

bpy.ops.wm.open_mainfile(filepath=SRC)
objs = [o for o in bpy.data.objects if o.type == 'MESH']

def world_tris(o):
    me = o.data; me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    M = np.array(o.matrix_world, np.float32); co = co @ M[:3, :3].T + M[:3, 3]
    lt = np.empty(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get('vertices', lt)
    return co[lt.reshape(-1, 3)]

TR = {o.name: world_tris(o) for o in objs}
allv = np.concatenate([t.reshape(-1, 3) for t in TR.values()])
lo = allv.min(0); k = LENGTH / (allv[:, 0].max() - lo[0])
for n in TR: TR[n] = (TR[n] - lo) * k                       # mm, min corner at 0, orientation kept
log('pieces', len(TR), 'scale', round(float(k), 3))

def sample(T, step):
    e = np.maximum.reduce([np.linalg.norm(T[:, i] - T[:, (i + 1) % 3], axis=1) for i in range(3)])
    n = np.maximum(1, np.ceil(e / step)).astype(int)
    out = [T.mean(1)]
    for m in np.unique(n):
        sel = T[n == m]
        i, j = np.meshgrid(np.arange(m + 1), np.arange(m + 1), indexing='ij'); ok = i + j <= m
        u = (i[ok] / m).astype(np.float32); w = (j[ok] / m).astype(np.float32)
        out.append((sel[:, None, 0] * (1 - u - w)[None, :, None] + sel[:, None, 1] * u[None, :, None]
                    + sel[:, None, 2] * w[None, :, None]).reshape(-1, 3))
    return np.concatenate(out)

def voxelize(P, org, G, shape):
    S = np.zeros(shape, bool)
    idx = np.floor((P - org) / G).astype(np.int32)
    ok = np.all((idx >= 0) & (idx < shape), axis=1); idx = idx[ok]
    S[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    return S

def dilate(A, r):
    for _ in range(r):
        B = A.copy()
        B[1:] |= A[:-1]; B[:-1] |= A[1:]
        B[:, 1:] |= A[:, :-1]; B[:, :-1] |= A[:, 1:]
        B[:, :, 1:] |= A[:, :, :-1]; B[:, :, :-1] |= A[:, :, 1:]
        A = B
    return A

def seen(S):
    """True where a straight axis ray (6 directions) reaches the grid edge without hitting S.
    Peak memory: S, out and one work array (flipped views, in-place not)."""
    out = np.zeros(S.shape, bool)
    for ax in range(3):
        acc = np.logical_or.accumulate(S, axis=ax); np.logical_not(acc, out=acc); out |= acc; del acc
        fl = [slice(None)] * 3; fl[ax] = slice(None, None, -1); fl = tuple(fl)
        acc = np.logical_or.accumulate(S[fl], axis=ax); np.logical_not(acc, out=acc); out |= acc[fl]; del acc
    return out

def rotations(n, seed=1):
    q = np.random.default_rng(seed).normal(size=(n, 4)); q /= np.linalg.norm(q, axis=1)[:, None]
    w, x, y, z = q.T
    return np.stack([np.stack([1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], -1),
                     np.stack([2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], -1),
                     np.stack([2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)], -1)], 1).astype(np.float32)

def dilate_cube(A):
    """Grow by one voxel including diagonals (3x3x3), one axis at a time."""
    for ax in range(3):
        B = A.copy()
        a = [slice(None)] * 3; b = [slice(None)] * 3
        a[ax] = slice(1, None); b[ax] = slice(None, -1)
        B[tuple(a)] |= A[tuple(b)]; B[tuple(b)] |= A[tuple(a)]
        A = B
    return A

MAX_VOXELS = 250e6   # memory guard for the rotated grids (bool: 1 byte per voxel)

def scan(T, G):
    flat = T.reshape(-1, 3); lo_, hi_ = flat.min(0), flat.max(0)
    while np.prod(np.ceil((hi_ - lo_) * 1.8 / G)) > MAX_VOXELS: G *= 1.1   # rotated bbox can be ~1.7x per side
    pad = int(np.ceil(MIN_WALL / G)) + 4
    org = lo_ - pad * G; shape = tuple(np.ceil((hi_ - org) / G).astype(int) + pad)
    S = np.zeros(shape, bool); npts = 0
    for i in range(0, len(T), 20000):            # sample in chunks: never hold every point at once
        P = sample(T[i:i + 20000], G / 2); npts += len(P)
        idx = np.floor((P - org) / G).astype(np.int32)
        S[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    out = seen(dilate(S, 1))                     # dilate 1 so rays can't slip through gaps between samples
    V = org + (np.argwhere(S).astype(np.float32) + 0.5) * G   # surface voxel centres stand in for the points
    c = ((lo_ + hi_) / 2).astype(np.float32)
    log('  grid', shape, 'G', round(G, 3), 'points', npts, 'surface voxels', len(V), 'solid after axis rays', int((~out).sum()))
    for ri, R in enumerate(rotations(ROTS)):
        Q = (V - c) @ R.T
        o2 = Q.min(0) - 4 * G; s2 = tuple(np.ceil((Q.max(0) - o2) / G).astype(int) + 4)
        out2 = seen(dilate_cube(voxelize(Q, o2, G, s2)))   # cube dilation closes gaps left by rotating voxels
        del Q
        cand_all = np.flatnonzero(~out); carved = 0
        for j in range(0, len(cand_all), 5_000_000):
            cand = np.stack(np.unravel_index(cand_all[j:j + 5_000_000], shape), 1).astype(np.int32)
            X = (org + (cand + 0.5) * G - c) @ R.T
            ii = np.floor((X - o2) / G).astype(np.int32)
            ok = np.all((ii >= 0) & (ii < s2), axis=1)
            hit = np.zeros(len(cand), bool); hit[ok] = out2[ii[ok, 0], ii[ok, 1], ii[ok, 2]]
            out[tuple(cand[hit].T)] = True; carved += int(hit.sum())
        del out2, cand_all
        log('  rotation', ri, 'grid', s2, 'carved', carved)
    r = max(1, int(round((MIN_WALL - G) / 2 / G)))
    M = ~out | dilate(S, r)                      # every surface at least MIN_WALL thick
    return M, org, G

def blur(M):
    """1-2-1 smoothing along each axis, returned as 0.5 - value (inside negative) for OpenVDB.
    Two float arrays at most, no np.roll copies."""
    f = M.astype(np.float32)
    for ax in range(3):
        a = [slice(None)] * 3; b = [slice(None)] * 3; a[ax] = slice(1, None); b[ax] = slice(None, -1)
        g = f * 2; g[tuple(a)] += f[tuple(b)]; g[tuple(b)] += f[tuple(a)]; g *= 0.25
        f = g; del g
    f *= -1; f += 0.5
    return f

def to_mesh(holder, org, G, name):
    f = blur(holder.pop())          # holder: [M], so the caller keeps no reference and M is freed here
    g = vdb.FloatGrid(0.5); g.copyFromArray(f); del f
    pts, tri, quad = g.convertToPolygons(isovalue=0.0, adaptivity=ADAPT)
    pts = org + (pts + 0.5) * G
    del g
    # build the mesh with numpy (from_pydata on Python lists of millions of faces costs GBs)
    faces = np.concatenate([tri.reshape(-1, 3), quad[:, [0, 1, 2]], quad[:, [0, 2, 3]]]).astype(np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(pts)); me.vertices.foreach_set('co', pts.astype(np.float32).ravel())
    me.loops.add(faces.size); me.loops.foreach_set('vertex_index', faces.ravel())
    me.polygons.add(len(faces)); me.polygons.foreach_set('loop_start', np.arange(0, faces.size, 3, dtype=np.int32))
    me.update(); del pts, tri, quad, faces
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.ensure_lookup_table()
    seen_f = set(); isl = []
    for f in bm.faces:
        if f.index in seen_f: continue
        st = [f]; grp = []; seen_f.add(f.index)
        while st:
            x = st.pop(); grp.append(x)
            for e in x.edges:
                for y in e.link_faces:
                    if y.index not in seen_f: seen_f.add(y.index); st.append(y)
        isl.append(grp)
    big = max(len(i) for i in isl)
    small = [i for i in isl if len(i) < big * KEEP]
    bmesh.ops.delete(bm, geom=[f for i in small for f in i], context='FACES')
    nm_e = sum(1 for e in bm.edges if not e.is_manifold)
    nm_v = sum(1 for v in bm.verts if not v.is_manifold)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    log(name, 'G', G, 'tris', len(me.polygons), 'pieces', len(isl) - len(small), 'dropped', len(small),
        'non-manifold edges', nm_e, 'verts', nm_v)
    return o

for o in objs: bpy.data.objects.remove(o)
for o in [o for o in bpy.data.objects]: bpy.data.objects.remove(o)
os.makedirs(OUT, exist_ok=True)
for name, T in sorted(TR.items(), key=lambda kv: -len(kv[1])):
    if ONLY and name not in ONLY: continue
    if os.path.exists(os.path.join(OUT, name + '.stl')) and not ONLY: log(name, 'exists, skipped'); continue
    size = (T.reshape(-1, 3).max(0) - T.reshape(-1, 3).min(0)).max()
    G = float(np.clip(size / 450, 0.08, 0.25))
    M, org, G = scan(T, G)
    holder = [M]; del M
    o = to_mesh(holder, org, G, name)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.wm.stl_export(filepath=os.path.join(OUT, name + '.stl'), export_selected_objects=True)
    bpy.data.objects.remove(o)                         # free before the next piece

log('done')

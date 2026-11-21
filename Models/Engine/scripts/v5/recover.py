# Recover pieces deleted during the hand simplification: every loose island of the original model
# (source/engine.usdz, same coordinates as engine-simplified.blend) that lies inside a region and is not
# in the simplified file. Saves them as one object in <out.blend> (world coordinates baked).
#
# Usage: blender -b -P recover.py -- <original.usdz> <simplified.blend> <out.blend> <name> <region>
#   region = "cyl:<part>:<radius_mm>:<behind_mm>[:shaft]"  a cylinder on the axis of <part> (a pulley in the
#            simplified file, found as its round axis), from the pulley's back face, <behind_mm> deep.
#            ':shaft' keeps only thin pieces on the axis (radius <= 2.2 mm): the shaft the pulley sits on.
import sys
argv = sys.argv[sys.argv.index('--') + 1:]
ORIG, SIMP, OUT, NAME, REGION = argv[:5]
import bpy, bmesh, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
K = 229.252

def world_mesh(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world); return bm

# --- simplified file: the region, and a BVH of everything kept
bpy.ops.wm.open_mainfile(filepath=SIMP)
kind, part, r_mm, depth_mm, *mode = REGION.split(':')
SHAFT_ONLY = 'shaft' in mode          # Marcelo 2026-11-21: only the pin the pulley goes onto, not the alternator's insides
assert kind == 'cyl'
src_obj, isl_sel = part.split('/') if '/' in part else (part, None)
v = np.array([bpy.data.objects[src_obj].matrix_world @ x.co for x in bpy.data.objects[src_obj].data.vertices])
if isl_sel:   # e.g. mesh120/biggest-x-min: the pulley is one cluster of a multi-part object; pick by position
    lo_, hi_ = v.min(0), v.max(0)
    # the pulley is the cluster of mesh120 nearest the alternator: vertices with y below the object's middle
    v = v[v[:, 1] < (lo_[1] + hi_[1]) / 2]
lo, hi = v.min(0), v.max(0); c = (lo + hi) / 2
ax = int(np.argmin(hi - lo))          # a pulley is thinnest along its axis
R = float(r_mm) / K; D = float(depth_mm) / K
q = [i for i in range(3) if i != ax]
# the body is behind the pulley: towards the engine, i.e. +x for this front-mounted pulley
a_front, a_back = lo[ax], hi[ax] - 0.3 / K   # the pulley's own length
a1 = hi[ax] + D
SHAFT_R = 2.2 / K                              # thin pieces on the axis (the shaft) may run forward through the pulley
a0 = a_front
print('REGION axis', 'xyz'[ax], 'centre mm', np.round(c * K, 1), 'behind %.1f to %.1f mm (shaft from %.1f)' % (a_back * K, a1 * K, a_front * K), 'radius', r_mm, flush=True)
kept = []
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    bm = world_mesh(o); kept.append(BVHTree.FromBMesh(bm)); bm.free()

def inside(pts):
    """Behind the pulley and within R of its axis - or a thin shaft on the axis, which may pass through
    the pulley but not stick out in front of it. Nuts, washers and the original pulley's own pieces in
    front of the pulley's back face are left out: the separate pulley part takes that space."""
    a = pts[:, ax]; rr = np.hypot(pts[:, q[0]] - c[q[0]], pts[:, q[1]] - c[q[1]])
    if not np.all((a <= a1) & (rr <= R)): return False
    if SHAFT_ONLY: return bool(np.all(rr <= SHAFT_R) and np.all(a >= a_front))
    if np.all(a >= a_back): return True
    return bool(np.all(rr <= SHAFT_R) and np.all(a >= a_front))

# --- original: islands inside the region and missing from the simplified file
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.usd_import(filepath=ORIG)
out = bmesh.new(); found = 0
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    w = np.array([o.matrix_world @ x.co for x in o.data.vertices])
    if len(w) == 0: continue
    if np.any(w.max(0)[q] < c[q] - R) or np.any(w.min(0)[q] > c[q] + R) or w.max(0)[ax] < a0 or w.min(0)[ax] > a1: continue
    bm = world_mesh(o); bm.verts.ensure_lookup_table()
    lab = np.full(len(bm.verts), -1); k = 0
    for vv in bm.verts:
        if lab[vv.index] >= 0: continue
        st = [vv]; lab[vv.index] = k
        while st:
            x = st.pop()
            for e in x.link_edges:
                y = e.other_vert(x)
                if lab[y.index] < 0: lab[y.index] = k; st.append(y)
        k += 1
    co = np.array([x.co for x in bm.verts])
    for i in range(k):
        idx = np.nonzero(lab == i)[0]; pts = co[idx]
        if not inside(pts): continue
        sample = pts[::max(1, len(pts) // 50)]
        present = all(min(t.find_nearest(Vector(p))[3] for t in kept) * K < 0.01 for p in sample)
        if present: continue
        vm = {}
        for j in idx: vm[j] = out.verts.new(bm.verts[int(j)].co)
        for f in bm.faces:
            if lab[f.verts[0].index] == i:
                try: out.faces.new([vm[x.index] for x in f.verts])
                except ValueError: pass
        found += 1
        rmax = np.hypot(pts[:, q[0]] - c[q[0]], pts[:, q[1]] - c[q[1]]).max() * K
        print('FOUND %s island %d: %d verts, %.1f x %.1f x %.1f mm, reaches %.1f mm from the axis, %s'
              % (o.name, i, len(idx), *((pts.max(0) - pts.min(0)) * K), rmax, 'ON AXIS' if rmax < 4 else ''), flush=True)
    bm.free()
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new(NAME); out.to_mesh(me); out.free()
ob = bpy.data.objects.new(NAME, me); bpy.context.scene.collection.objects.link(ob)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('RECOVERED', found, 'islands into', NAME, len(me.vertices), 'verts', flush=True)

# Which parts touch which, and which have a gap. Prints every pair closer than 3 mm, then each part's
# nearest neighbour, flagging parts that touch nothing (gap > TOUCH).
# Usage: blender -b <parts.blend> -P contacts.py
import bpy, bmesh, numpy as np
from mathutils.bvhtree import BVHTree
K = 229.252; NEAR = 3.0; TOUCH = 0.05      # mm
ms = sorted([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: o.name)
V = {o.name: np.array([v.co for v in o.data.vertices]) for o in ms}
BB = {n: (v.min(0) * K, v.max(0) * K) for n, v in V.items()}
T = {}
for o in ms:
    bm = bmesh.new(); bm.from_mesh(o.data); T[o.name] = BVHTree.FromBMesh(bm); bm.free()
def gap(a, b):
    best = 1e9
    for x, y in ((a, b), (b, a)):
        vs = V[x][::max(1, len(V[x]) // 40000)]
        for p in vs:
            d = T[y].find_nearest(p)[3]
            if d is not None and d < best: best = d
    return best * K
near = {o.name: (1e9, '-') for o in ms}
for i, a in enumerate(ms):
    for b in ms[i + 1:]:
        (alo, ahi), (blo, bhi) = BB[a.name], BB[b.name]
        if np.any(alo - NEAR > bhi) or np.any(blo - NEAR > ahi): continue
        g = gap(a.name, b.name)
        if g < NEAR:
            print('PAIR %-20s %-20s %6.3f mm %s' % (a.name, b.name, g, 'touch' if g <= TOUCH else 'GAP'), flush=True)
        for x, y in ((a.name, b.name), (b.name, a.name)):
            if g < near[x][0]: near[x] = (g, y)
for n, (g, y) in near.items():
    print('PART %-20s nearest %-20s %s' % (n, y, ('%.3f mm' % g if g < 1e8 else 'nothing within 3 mm')) + ('' if g <= TOUCH else '   <-- not touching'), flush=True)

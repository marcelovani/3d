# Make scanned parts fit each other (run after the scan, on the closed STLs).
# A pulley that sits on a pin in another part (the host):
#   1. its hole is opened to the pin's radius + BORE_GAP, so it slides on;
#   2. its shape, grown by FACE_GAP, is cut out of the host, so where the original model had the pulley
#      sunk into the host (the alternator front, up to 2 mm) the host gets a matching pocket.
# Usage: blender -b -P fit.py -- <scan dir>     (rewrites the STLs it changes, in place; safe to rerun)
import sys, os
OUT = sys.argv[sys.argv.index('--') + 1]
import bpy, bmesh, numpy as np, openvdb as vdb
from mathutils import Vector
from mathutils.bvhtree import BVHTree

FITS = [('alternator_pulley', 'block'), ('crank_pulley', 'block')]   # (pulley, host with the pin)
BORE_GAP = 0.3      # mm, radial gap between pin and pulley hole
FACE_GAP = 0.25     # mm, gap between the pulley and the pocket cut for it (a little under BORE_GAP so the
                    # grown pulley never touches the pin surface: no coincident faces for the boolean)

def log(*a): print('FIT', *a, flush=True)
def load(name):
    # the .blend scan.py writes next to each STL keeps the mesh's real topology: an STL has every triangle
    # on its own, and welding it back merges surfaces that only touch, which the boolean then refuses
    with bpy.data.libraries.load(os.path.join(OUT, name + '.blend')) as (src, dst): dst.objects = [name]
    o = dst.objects[0]; bpy.context.scene.collection.objects.link(o); o.use_fake_user = False
    log(name, 'loaded, non-manifold edges', nonmanifold(o))
    return o
def save(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.wm.stl_export(filepath=os.path.join(OUT, o.name + '.stl'), export_selected_objects=True)
def verts(o): return np.array([tuple(v.co) for v in o.data.vertices])
def nonmanifold(o):
    bm = bmesh.new(); bm.from_mesh(o.data); n = sum(1 for e in bm.edges if not e.is_manifold); bm.free(); return n
def boolean(o, cutter):
    before = len(o.data.polygons)
    m = o.modifiers.new('cut', 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = cutter; m.solver = 'MANIFOLD'
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='cut')
    return len(o.data.polygons) != before
def grown(o, d, voxel=0.08):
    """o grown outwards by d mm, as a new closed mesh (OpenVDB level set of o, meshed at +d)."""
    bm = bmesh.new(); bm.from_mesh(o.data); bmesh.ops.triangulate(bm, faces=bm.faces)
    p = np.array([tuple(v.co) for v in bm.verts], np.float32)
    t = np.array([[v.index for v in f.verts] for f in bm.faces], np.uint32); bm.free()
    g = vdb.FloatGrid.createLevelSetFromPolygons(p, triangles=t, transform=vdb.createLinearTransform(voxel), halfWidth=d / voxel + 3)
    pts, tri, quad = g.convertToPolygons(isovalue=d, adaptivity=0.0)
    faces = np.concatenate([tri.reshape(-1, 3), quad[:, [0, 1, 2]], quad[:, [0, 2, 3]]]).astype(np.int32)
    me = bpy.data.meshes.new(o.name + '_grown')
    me.vertices.add(len(pts)); me.vertices.foreach_set('co', pts.astype(np.float32).ravel())
    me.loops.add(faces.size); me.loops.foreach_set('vertex_index', faces.ravel())
    me.polygons.add(len(faces)); me.polygons.foreach_set('loop_start', np.arange(0, faces.size, 3, dtype=np.int32)); me.update()
    g2 = bpy.data.objects.new(o.name + '_grown', me); bpy.context.scene.collection.objects.link(g2)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return g2
def overlap(a, b):
    """Volume (mm3) a and b share: intersect copies with the Manifold solver. (A nearest-face inside test
    is fooled at sharp corners; this is not.)"""
    c = b.copy(); c.data = b.data.copy(); bpy.context.scene.collection.objects.link(c)
    m = c.modifiers.new('i', 'BOOLEAN'); m.operation = 'INTERSECT'; m.object = a; m.solver = 'MANIFOLD'
    bpy.context.view_layer.objects.active = c; bpy.ops.object.modifier_apply(modifier='i')
    bm = bmesh.new(); bm.from_mesh(c.data); v = bm.calc_volume(signed=False); bm.free(); bpy.data.objects.remove(c)
    return v

bpy.ops.wm.read_factory_settings(use_empty=True)
cache = {}
for pul, host in FITS:
    if not all(os.path.exists(os.path.join(OUT, n + '.stl')) for n in (pul, host)):
        log(pul, host, 'skipped: scan both first'); continue
    for n in (pul, host):
        if n not in cache: cache[n] = load(n)
    P, H = cache[pul], cache[host]
    pv = verts(P); lo, hi = pv.min(0), pv.max(0); ax = int(np.argmin(hi - lo)); q = [i for i in range(3) if i != ax]
    c = (lo + hi) / 2
    # which end is the front (away from the host)? the end farther from the host's middle. (Counting host
    # material near each end picked the wrong end once the block's inside was reshaped.)
    hv = verts(H); rr = np.hypot(hv[:, q[0]] - c[q[0]], hv[:, q[1]] - c[q[1]])
    L = hi[ax] - lo[ax]; hc = (hv[:, ax].min() + hv[:, ax].max()) / 2
    front, back = (lo[ax], hi[ax]) if abs(lo[ax] - hc) > abs(hi[ax] - hc) else (hi[ax], lo[ax])
    sgn = 1.0 if back > front else -1.0
    # pin radius: measured over the first 2.5 mm from the pin's tip, where only the pin is near the axis
    # (further back the host itself - e.g. the alternator front - reaches into the pulley's length)
    s = (hv[:, ax] - front) * sgn
    tip = (rr < 3.0) & (s > 0) & (s < L)
    if not tip.any(): log(pul, 'no pin found inside it; skipped'); continue
    s_tip = float(s[tip].min())
    zone = (rr < 4.5) & (s >= s_tip) & (s <= s_tip + 2.5)
    r_pin = float(rr[zone].max())
    log(pul, 'pin tip %.1f mm behind the pulley front' % s_tip)
    bore = float(np.hypot(pv[:, q[0]] - c[q[0]], pv[:, q[1]] - c[q[1]]).min())
    v0 = overlap(P, H)
    log(pul, 'on %s: pin radius %.2f mm, hole radius %.2f mm; overlaps %s by %.1f mm3' % ('xyz'[ax], r_pin, bore, host, v0))
    # 1. open the hole
    loc = c.copy(); loc[ax] = (front + back) / 2
    rot = {0: (0, np.pi / 2, 0), 1: (np.pi / 2, 0, 0), 2: (0, 0, 0)}[ax]
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=r_pin + BORE_GAP, depth=L + 2, location=tuple(loc), rotation=rot)
    cyl = bpy.context.object; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    boolean(P, cyl); bpy.data.objects.remove(cyl)
    # 2. pocket in the host for the pulley
    G = grown(P, FACE_GAP); changed = boolean(H, G); bpy.data.objects.remove(G)
    v1 = overlap(P, H)
    log(pul, 'hole now radius %.2f mm (pin %.2f + %.2f gap); pocket cut in %s: %s; overlap now %.3f mm3'
        % (r_pin + BORE_GAP, r_pin, BORE_GAP, host, 'yes' if changed else 'nothing to cut', v1))
for o in cache.values():
    log(o.name, 'non-manifold edges', nonmanifold(o)); save(o)
    bpy.data.libraries.write(os.path.join(OUT, o.name + '.blend'), {o}, fake_user=True)

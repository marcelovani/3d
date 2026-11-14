# Render every part in a .blend on its own, from two angles. partviews.py -- <out dir>
import bpy, sys, math, os
from mathutils import Vector
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.show_cavity = True; sh.color_type = 'SINGLE'; sh.single_color = (0.85, 0.55, 0.3)
sc.render.resolution_x = 800; sc.render.resolution_y = 600
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.clip_end = 5000
ms = [o for o in sc.objects if o.type == 'MESH']
for o in ms:
    for p in ms: p.hide_render = p is not o
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    c = sum(pts, Vector()) / 8; r = max((p - c).length for p in pts)
    for k, d in {'a': Vector((-1, -1.2, 0.8)), 'b': Vector((1, 1.2, 0.6))}.items():
        cam.location = c + d.normalized() * r * 3.2
        cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(out, f'{o.name}_{k}.png'); bpy.ops.render.render(write_still=True)

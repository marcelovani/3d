# Contact sheet: every mesh in the open .blend, numbered, biggest first. Each tile has two views:
# the piece alone, and the whole engine with that piece in orange (the rest grey) to show where it sits.
# Usage: blender -b <file.blend> -P sheet.py -- <out.png> [cols] [size|z]   (z = top of the engine first)
import bpy, sys, os, numpy as np, tempfile
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
OUTPNG = argv[0]; COLS = int(argv[1]) if len(argv) > 1 else 4
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'STUDIO'; sh.show_cavity = True; sh.color_type = 'OBJECT'
sh.background_type = 'VIEWPORT'; sh.background_color = (0.16, 0.16, 0.18)
W = 420; sc.render.resolution_x = sc.render.resolution_y = W
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.clip_start = 1e-5; cam.data.clip_end = 1e5
ms = [o for o in sc.objects if o.type == 'MESH']
ORDER = argv[2] if len(argv) > 2 else 'size'
def centre(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]; return sum(pts, Vector()) / 8
if ORDER == 'z': ms.sort(key=lambda o: -centre(o).z)          # top of the engine first
else: ms.sort(key=lambda o: -len(o.data.polygons))          # biggest first
ORANGE = (0.95, 0.5, 0.15, 1); GREY = (0.55, 0.55, 0.58, 1)

def frame(objs, d, f=2.6):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    c = sum(pts, Vector()) / len(pts); r = max((p - c).length for p in pts)
    cam.location = c + d.normalized() * r * f
    cam.rotation_euler = (c - cam.location).to_track_quat('-Z', 'Y').to_euler()

tmp = tempfile.mkdtemp(); f = os.path.join(tmp, 'x.png')
def shot():
    sc.render.filepath = f; bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(f); a = np.array(im.pixels[:], np.float32).reshape(W, W, 4); bpy.data.images.remove(im)
    return a

F5x7 = {
 'a':'00000 00000 01110 00001 01111 10001 01111', 'b':'10000 10000 10110 11001 10001 10001 11110',
 'c':'00000 00000 01110 10000 10000 10001 01110', 'd':'00001 00001 01101 10011 10001 10001 01111',
 'e':'00000 00000 01110 10001 11111 10000 01110', 'f':'00110 01001 01000 11100 01000 01000 01000',
 'g':'00000 01111 10001 10001 01111 00001 01110', 'h':'10000 10000 10110 11001 10001 10001 10001',
 'i':'00100 00000 01100 00100 00100 00100 01110', 'j':'00010 00000 00110 00010 00010 10010 01100',
 'k':'10000 10000 10010 10100 11000 10100 10010', 'l':'01100 00100 00100 00100 00100 00100 01110',
 'm':'00000 00000 11010 10101 10101 10101 10101', 'n':'00000 00000 10110 11001 10001 10001 10001',
 'o':'00000 00000 01110 10001 10001 10001 01110', 'p':'00000 00000 11110 10001 11110 10000 10000',
 'q':'00000 00000 01101 10011 01111 00001 00001', 'r':'00000 00000 10110 11001 10000 10000 10000',
 's':'00000 00000 01111 10000 01110 00001 11110', 't':'01000 01000 11100 01000 01000 01001 00110',
 'u':'00000 00000 10001 10001 10001 10011 01101', 'v':'00000 00000 10001 10001 10001 01010 00100',
 'w':'00000 00000 10001 10001 10101 10101 01010', 'x':'00000 00000 10001 01010 00100 01010 10001',
 'y':'00000 00000 10001 10001 01111 00001 01110', 'z':'00000 00000 11111 00010 00100 01000 11111',
 '0':'01110 10001 10011 10101 11001 10001 01110', '1':'00100 01100 00100 00100 00100 00100 01110',
 '2':'01110 10001 00001 00010 00100 01000 11111', '3':'11111 00010 00100 00010 00001 10001 01110',
 '4':'00010 00110 01010 10010 11111 00010 00010', '5':'11111 10000 11110 00001 00001 10001 01110',
 '6':'00110 01000 10000 11110 10001 10001 01110', '7':'11111 00001 00010 00100 01000 01000 01000',
 '8':'01110 10001 10001 01110 10001 10001 01110', '9':'01110 10001 10001 01111 00001 00010 01100',
 '.':'00000 00000 00000 00000 00000 01100 01100', '_':'00000 00000 00000 00000 00000 00000 11111',
 '+':'00000 00100 00100 11111 00100 00100 00000', '-':'00000 00000 00000 11111 00000 00000 00000',
 '?':'01110 10001 00001 00010 00100 00000 00100', '(':'00010 00100 01000 01000 01000 00100 00010',
 ')':'01000 00100 00010 00010 00010 00100 01000'}
FONT = {k: v.split() for k, v in F5x7.items()}
def label(t, text, S=4):
    wpx = len(text) * 6 * S + 2 * S
    t[t.shape[0] - 9 * S - 8:t.shape[0] - 4, 4:4 + wpx, :3] = 1.0          # white box, top-left
    x0 = 4 + S
    for ch in text:
        g = FONT.get(ch)
        if g:
            for yy, line in enumerate(g):
                for xx, b in enumerate(line):
                    if b == '1':
                        y = t.shape[0] - 8 - (yy + 1) * S
                        t[y:y + S, x0 + xx * S:x0 + (xx + 1) * S, :3] = 0
        x0 += 6 * S

tiles = []
for n, o in enumerate(ms, 1):
    for p in ms: p.color = GREY; p.hide_render = p is not o
    o.color = ORANGE
    frame([o], Vector((-1, -1.2, 0.8))); a = shot()
    for p in ms: p.hide_render = False
    frame(ms, Vector((-1, -1.2, 0.9)), 2.2); b = shot()
    t = np.concatenate([a, b], 1); label(t, f'{n} {o.name}')
    t[:, :2, :3] = 1; t[:, -2:, :3] = 1; t[:2, :, :3] = 1; t[-2:, :, :3] = 1   # white border
    tiles.append(t)
    print('TILE', n, o.name, flush=True)
rows = []
for i in range(0, len(tiles), COLS):
    r = tiles[i:i + COLS]
    while len(r) < COLS: r.append(np.ones_like(tiles[0]))
    rows.append(np.concatenate(r, 1))
sheet = np.concatenate(rows[::-1], 0)           # first row on top (pixels are bottom-up)
h, w = sheet.shape[:2]
img = bpy.data.images.new('sheet', w, h); img.pixels = sheet.ravel()
img.filepath_raw = OUTPNG; img.file_format = 'PNG'; img.save()
print('SHEET', OUTPNG, w, h)

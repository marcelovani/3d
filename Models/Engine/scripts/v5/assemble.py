# Put every scanned part together, in place, in its print colour (colours.py):
#   <scan dir>/engine.blend          every part, a collection per colour, millimetre units
#   <scan dir>/engine-<colour>.stl   every part of that colour in one STL (an STL has no colour of its own)
# Parts come from the <part>.blend files scan.py writes (and fit.py updates), not from the STLs.
# Usage: blender -b -P assemble.py -- <scan dir>
import sys, os, glob
OUT = sys.argv[sys.argv.index('--') + 1]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, colours

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0     # no engine.blend1 backups
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'; sc.unit_settings.scale_length = 0.001; sc.unit_settings.length_unit = 'MILLIMETERS'
names = sorted(n for n in (os.path.basename(f)[:-4] for f in glob.glob(os.path.join(OUT, '*.stl')))
               if not n.startswith('engine-') and os.path.exists(os.path.join(OUT, n + '.blend')))
objs = []
for n in names:
    with bpy.data.libraries.load(os.path.join(OUT, n + '.blend')) as (src, dst): dst.objects = [n]
    o = dst.objects[0]; o.use_fake_user = False; sc.collection.objects.link(o); objs.append(o)
colours.apply(objs)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'engine.blend'))
for c in colours.RGBA:
    sel = [o for o in objs if colours.colour_of(o.name) == c]
    if not sel: continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in sel: o.select_set(True)
    bpy.context.view_layer.objects.active = sel[0]
    bpy.ops.wm.stl_export(filepath=os.path.join(OUT, 'engine-%s.stl' % c), export_selected_objects=True)
    print('ASSEMBLE %-5s %s' % (c, ', '.join(o.name for o in sel)), flush=True)
print('ASSEMBLE', len(objs), 'parts ->', os.path.join(OUT, 'engine.blend'), flush=True)

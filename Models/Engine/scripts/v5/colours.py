# Print colour of each part (Marcelo 2026-11-21, by the numbers in images/v5-parts.png):
#   1 oil_cap, 3 rocker_cover, 6 exhaust_manifold, 8 alternator_pulley, 10 crank_pulley, 11 flywheel: black
#   2 air_filter, 7 fan, 12 sump: red
#   the rest (4 intake_manifold, 5 cylinder_head, 9 block): grey
#
# apply(objects) gives each part a material in its colour (Blender's Solid view shows it) and puts it in a
# collection per colour. Run on its own, it colours the open file and saves it:
#   blender -b source/engine-parts.blend -P scripts/v5/colours.py
import bpy

RGBA = {'black': (0.03, 0.03, 0.03, 1), 'red': (0.65, 0.04, 0.03, 1), 'grey': (0.55, 0.55, 0.57, 1)}
COLOUR = {
    'oil_cap': 'black', 'rocker_cover': 'black', 'exhaust_manifold': 'black',
    'alternator_pulley': 'black', 'crank_pulley': 'black', 'flywheel': 'black',
    'air_filter': 'red', 'fan': 'red', 'sump': 'red',
    'intake_manifold': 'grey', 'cylinder_head': 'grey', 'block': 'grey',
}


def colour_of(name): return COLOUR.get(name, 'grey')


def apply(objects):
    scene = bpy.context.scene
    for c in RGBA:
        if c not in bpy.data.materials:
            m = bpy.data.materials.new(c); m.diffuse_color = RGBA[c]   # viewport (Solid) colour
            try:                                                       # rendered colour too
                m.use_nodes = True
                bsdf = m.node_tree.nodes.get('Principled BSDF')
                bsdf.inputs['Base Color'].default_value = RGBA[c]; bsdf.inputs['Roughness'].default_value = 0.5
            except Exception: pass
        if c not in bpy.data.collections: scene.collection.children.link(bpy.data.collections.new(c))
    for o in objects:
        if o.type != 'MESH': continue
        c = colour_of(o.name)
        o.data.materials.clear(); o.data.materials.append(bpy.data.materials[c]); o.color = RGBA[c]
        for coll in list(o.users_collection): coll.objects.unlink(o)
        bpy.data.collections[c].objects.link(o)


if __name__ == '__main__':
    apply(list(bpy.data.objects))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_mainfile()
    print('COLOURED', bpy.data.filepath, flush=True)

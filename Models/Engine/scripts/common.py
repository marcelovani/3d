import bpy, math
from mathutils import Vector, Matrix
def load(src, L=150.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    sc=bpy.context.scene
    RX=Matrix.Rotation(math.pi,4,'X')
    for o in sc.objects:
        if o.parent is None: o.matrix_world=RX@o.matrix_world
    bpy.context.view_layer.update()
    ms=[o for o in sc.objects if o.type=='MESH']
    pts=[o.matrix_world@Vector(c) for o in ms for c in o.bound_box]
    mn=Vector(map(min,*pts)); mx=Vector(map(max,*pts)); k=L/(mx.x-mn.x)
    T=Matrix.Scale(k,4)@Matrix.Translation(-mn)
    for o in sc.objects:
        if o.parent is None: o.matrix_world=T@o.matrix_world
    bpy.context.view_layer.update()
    # bake transforms, unparent, name by mesh id
    out={}
    for o in ms:
        mw=o.matrix_world.copy(); o.parent=None; o.matrix_world=mw
    for o in ms:
        o.data=o.data.copy(); o.data.transform(o.matrix_world); o.matrix_world=Matrix()
        n=o.name.split('_')[1].split('.')[0]; o.name='M'+n; out[n]=o
    for o in list(sc.objects):
        if o.type!='MESH': bpy.data.objects.remove(o)
    return out
def islands(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.separate(type='LOOSE'); bpy.ops.object.mode_set(mode='OBJECT')
    return list(bpy.context.selected_objects)
def bb(o):
    vs=[v.co for v in o.data.vertices]
    a=Vector((min(v.x for v in vs),min(v.y for v in vs),min(v.z for v in vs))); b=Vector((max(v.x for v in vs),max(v.y for v in vs),max(v.z for v in vs)))
    return a,b

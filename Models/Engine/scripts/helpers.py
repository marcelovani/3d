import bpy, time, math
O=bpy.data.objects; T0=time.time()
def log(*a): print('LOG',round(time.time()-T0),*a, flush=True)
def act(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
def apply(o,m): act(o); bpy.ops.object.modifier_apply(modifier=m.name)
def ntri(o): return sum(len(p.vertices)-2 for p in o.data.polygons)
def boolean(o,cutter,op):
    before=ntri(o); m=o.modifiers.new('b','BOOLEAN'); m.operation=op; m.object=cutter; m.solver='MANIFOLD'; apply(o,m)
    if ntri(o)==before: log('WARN boolean no change',o.name,cutter.name,op)
def cyl(r,depth,loc,axis='Z',name='c',verts=64):
    rot={'X':(0,math.pi/2,0),'Y':(math.pi/2,0,0),'Z':(0,0,0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc,rotation=rot); o=bpy.context.object; o.name=name; return o
def box(a,b,name='b'):
    bpy.ops.mesh.primitive_cube_add(size=1,location=tuple((a[i]+b[i])/2 for i in range(3))); o=bpy.context.object
    o.scale=tuple(b[i]-a[i] for i in range(3)); bpy.ops.object.transform_apply(scale=True); o.name=name; return o

def to_mesh(mask,org,G,name,radius):
    """Voxel mask -> smooth closed mesh via Geometry Nodes (points -> volume -> mesh)."""
    import numpy as np
    pts=np.argwhere(mask).astype(np.float32)*G+np.asarray(org,dtype=np.float32)
    me=bpy.data.meshes.new(name); me.vertices.add(len(pts)); me.vertices.foreach_set('co',pts.ravel())
    o=O.new(name,me); bpy.context.scene.collection.objects.link(o)
    ng=bpy.data.node_groups.new(name+'_ng','GeometryNodeTree')
    ng.interface.new_socket('Geometry',in_out='INPUT',socket_type='NodeSocketGeometry'); ng.interface.new_socket('Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    N=ng.nodes; gi=N.new('NodeGroupInput'); go=N.new('NodeGroupOutput')
    m2p=N.new('GeometryNodeMeshToPoints'); p2v=N.new('GeometryNodePointsToVolume'); v2m=N.new('GeometryNodeVolumeToMesh')
    p2v.inputs['Radius'].default_value=radius
    try: p2v.inputs['Voxel Size'].default_value=G*0.5
    except Exception: pass
    L=ng.links; L.new(gi.outputs[0],m2p.inputs[0]); L.new(m2p.outputs[0],p2v.inputs[0]); L.new(p2v.outputs[0],v2m.inputs[0]); L.new(v2m.outputs[0],go.inputs[0])
    md=o.modifiers.new('gn','NODES'); md.node_group=ng; apply(o,md)
    return o

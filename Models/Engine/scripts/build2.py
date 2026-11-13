import bpy, bmesh, sys, time, math
import numpy as np
from mathutils import Vector, Matrix
OUT=sys.argv[-1]; t0=time.time()
sc=bpy.context.scene; O=bpy.data.objects
def log(*a): print('LOG',round(time.time()-t0),*a, flush=True)
def act(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
def apply(o,m): act(o); bpy.ops.object.modifier_apply(modifier=m.name)
def ntri(o): return sum(len(p.vertices)-2 for p in o.data.polygons)
def boolean(o,cutter,op):
    before=ntri(o); m=o.modifiers.new('b','BOOLEAN'); m.operation=op; m.object=cutter; m.solver='MANIFOLD'; apply(o,m)
    after=ntri(o)
    if after==before: log('WARN boolean no change',o.name,cutter.name,op)
def cyl(r,depth,loc,axis='Z',name='c',verts=64):
    rot={'X':(0,math.pi/2,0),'Y':(math.pi/2,0,0),'Z':(0,0,0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc,rotation=rot); o=bpy.context.object; o.name=name; return o
def box(a,b,name='b'):
    bpy.ops.mesh.primitive_cube_add(size=1,location=tuple((a[i]+b[i])/2 for i in range(3))); o=bpy.context.object
    o.scale=tuple(b[i]-a[i] for i in range(3)); bpy.ops.object.transform_apply(scale=True); o.name=name; return o
B=O['body']
# 1. drop small floating shells (internal leftovers, loose bolts); keep shells >= 20k verts
bm=bmesh.new(); bm.from_mesh(B.data); bm.verts.ensure_lookup_table()
seen=np.zeros(len(bm.verts),bool); kill=[]
for v in bm.verts:
    if seen[v.index]: continue
    st=[v]; seen[v.index]=True; comp=[]
    while st:
        a=st.pop(); comp.append(a)
        for e in a.link_edges:
            b=e.other_vert(a)
            if not seen[b.index]: seen[b.index]=True; st.append(b)
    if len(comp)<20000: kill+=comp
bmesh.ops.delete(bm,geom=kill,context='VERTS'); bm.to_mesh(B.data); bm.free()
log('shells cleaned',ntri(B))
# 1b. close the window in the sump floor: 2D holes in the floor footprint
from mathutils.bvhtree import BVHTree
import bmesh as _bm
tree=BVHTree.FromObject(B,bpy.context.evaluated_depsgraph_get())
X0_,Y0_=20,30; nx,ny=140,110
hz=np.full((nx,ny),1e9)
for i in range(nx):
    for j in range(ny):
        h=tree.ray_cast(Vector((X0_+i+.5,Y0_+j+.5,-20)),Vector((0,0,1)))
        if h[0] is not None: hz[i,j]=h[0].z
floor=hz<25
outside=np.zeros((nx,ny),bool); outside[0,:]=outside[-1,:]=outside[:,0]=outside[:,-1]=True; outside&=~floor
while True:
    n=outside.copy(); n[1:]|=outside[:-1]; n[:-1]|=outside[1:]; n[:,1:]|=outside[:,:-1]; n[:,:-1]|=outside[:,1:]; n&=~floor
    if n.sum()==outside.sum(): break
    outside=n
hole=~floor&~outside
log('sump window cells',int(hole.sum()))
if hole.any():
    # grow 2 cells under the floor so the plate overlaps the existing floor
    g=hole.copy()
    for _ in range(2):
        n=g.copy(); n[1:]|=g[:-1]; n[:-1]|=g[1:]; n[:,1:]|=g[:,:-1]; n[:,:-1]|=g[:,1:]; g=n&(floor|hole)
    ring=g&floor
    z0=float(np.median(hz[ring])) if ring.any() else 0.6
    log('plate z0',round(z0,1))
    bmx=_bm.new()
    for i,j in np.argwhere(g):
        _bm.ops.create_cube(bmx,size=1.0,matrix=Matrix.Translation((X0_+i+.5,Y0_+j+.5,z0+1.5))@Matrix.Diagonal((1,1,3,1)))
    me=bpy.data.meshes.new('plate'); bmx.to_mesh(me); pl=O.new('plate',me); sc.collection.objects.link(pl)
    m=pl.modifiers.new('r','REMESH'); m.mode='VOXEL'; m.voxel_size=0.5; apply(pl,m)
    boolean(B,pl,'UNION'); O.remove(pl)
# 1c. plug the rear main-seal opening left by the removed crankshaft (hidden behind the flywheel)
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=11,depth=7,location=(134.5,83,52),rotation=(0,math.pi/2,0)); pg=bpy.context.object
boolean(B,pg,'UNION'); O.remove(pg)
# 2. voxel occupancy of the surface at G mm, flood-fill exterior
G=1.0
def dil(a):
    r=a.copy()
    r[1:]|=a[:-1]; r[:-1]|=a[1:]; r[:,1:]|=a[:,:-1]; r[:,:-1]|=a[:,1:]; r[:,:,1:]|=a[:,:,:-1]; r[:,:,:-1]|=a[:,:,1:]
    return r
co=np.empty(len(B.data.vertices)*3); B.data.vertices.foreach_get('co',co); co=co.reshape(-1,3)
org=np.array([-3,-3,-3.0]); dims=np.ceil((co.max(0)-org+3)/G).astype(int)+1
surf=np.zeros(dims,bool); idx=((co-org)/G).astype(int); surf[idx[:,0],idx[:,1],idx[:,2]]=True
cc=np.empty(len(O['crank'].data.vertices)*3); O['crank'].data.vertices.foreach_get('co',cc); cc=cc.reshape(-1,3)
ci=np.clip(((cc-org)/G).astype(int),0,dims-1); surf[ci[:,0],ci[:,1],ci[:,2]]=True
surfc1=dil(surf)
def _dil_placeholder(a):
    r=a.copy()
    r[1:]|=a[:-1]; r[:-1]|=a[1:]; r[:,1:]|=a[:,:-1]; r[:,:-1]|=a[:,1:]; r[:,:,1:]|=a[:,:,:-1]; r[:,:,:-1]|=a[:,:,1:]
    return r
# outside = seen from any of the 6 axis directions before hitting the (slightly closed) surface
ext=np.zeros(dims,bool)
for ax in range(3):
    ext|=~np.logical_or.accumulate(surfc1,axis=ax)
    ext|=np.flip(~np.logical_or.accumulate(np.flip(surfc1,axis=ax),axis=ax),axis=ax)
solid=~ext
log('solid voxels',int(solid.sum()),'dims',dims.tolist())
def erode(a,k):
    for _ in range(k):
        r=a.copy()
        for ax in range(3):
            for s in (1,-1): r&=np.roll(a,s,axis=ax)
        # diagonals in-plane for a rounder erosion
        for ax1,ax2 in ((0,1),(0,2),(1,2)):
            for s1 in (1,-1):
                for s2 in (1,-1): r&=np.roll(np.roll(a,s1,axis=ax1),s2,axis=ax2)
        a=r
    return a
def to_mesh(mask,name,radius):
    pts=np.argwhere(mask).astype(np.float32)*G+org.astype(np.float32)
    me=bpy.data.meshes.new(name); me.vertices.add(len(pts)); me.vertices.foreach_set('co',pts.ravel())
    o=O.new(name,me); sc.collection.objects.link(o)
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
# 3. filler: solid eroded 1 voxel, unioned in so the inside becomes solid
filler=to_mesh(erode(solid,3),'filler',G*0.75)
log('filler tris',ntri(filler))
boolean(B,filler,'UNION'); O.remove(filler)
log('filled',ntri(B))
# 4. cavity: >=3 mm from the outside, inside the core box, connected to the block centre
WALL=4
cav=erode(solid,WALL)
core=np.zeros(dims,bool)
def ix(x,y,z): return tuple(int((v-o)/G) for v,o in zip((x,y,z),org))
a=ix(30,48,3); b=ix(138,118,148); core[a[0]:b[0],a[1]:b[1],a[2]:b[2]]=True
cav&=core
pts=np.argwhere(cav)
if len(pts)==0: raise SystemExit('no cavity')
c=np.array(ix(85,83,80)); s=tuple(pts[np.argmin(((pts-c)**2).sum(1))])
seed=np.zeros(dims,bool); seed[s]=True; log('seed',(np.array(s)*G+org).round().tolist())
comp=seed&cav
while True:
    n=dil(comp)&cav
    if n.sum()==comp.sum(): break
    comp=n
log('cavity voxels',int(comp.sum()),'of',int(cav.sum()))
np.save(OUT+'.cav.npy',comp); np.save(OUT+'.solid.npy',solid); np.save(OUT+'.org.npy',org)
C=to_mesh(comp,'cavity',G*0.75)
m=C.modifiers.new('s','SMOOTH'); m.iterations=3; apply(C,m)
log('cavity tris',ntri(C))
bpy.ops.wm.save_as_mainfile(filepath=OUT)
log('saved')

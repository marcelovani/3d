# Stage 6: screw starter holes (1.5 mm) joining the separate parts to the block.
#  - sump (split z=36) and rocker cover (split z=127): 4 vertical holes each through the joint, placed in solid wall
#  - add-on parts: 2 holes each where the part touches the block (air filter -> intake), along the block's surface normal
import bpy, sys, math
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,sys.argv[-3]); from helpers import *
WORK=sys.argv[-2]; OUT=sys.argv[-1]
solid=np.load(WORK+'/stage2.blend.solid.npy'); cav=np.load(WORK+'/stage2.blend.cav.npy'); org=np.load(WORK+'/stage2.blend.org.npy')
R=0.75   # 1.5 mm starter hole
def clear(target,part,g=0.3):
    cu=part.copy(); cu.data=part.data.copy(); bpy.context.scene.collection.objects.link(cu)
    d=cu.modifiers.new('grow','DISPLACE'); d.direction='NORMAL'; d.strength=g; d.mid_level=0; apply(cu,d)
    r=cu.modifiers.new('r','REMESH'); r.mode='VOXEL'; r.voxel_size=0.3; apply(cu,r)
    boolean(target,cu,'DIFFERENCE'); O.remove(cu)
for n in ('exhaust_manifold','intake_manifold','alternator','oil_filter'): clear(O['block'],O[n])
clear(O['intake_manifold'],O['air_filter'])
clear(O['rocker_cover'],O['chamber_cap'])
log('clearances cut')
def drill(objs,p,n,out_len=10,in_len=8,name='screw'):
    p=Vector(p); n=Vector(n).normalized(); a=p+n*out_len; b=p-n*in_len
    c=cyl(R,(a-b).length,(a+b)/2,'Z',name,24); c.rotation_euler=n.to_track_quat('Z','Y').to_euler(); bpy.context.view_layer.update()
    act(c); bpy.ops.object.transform_apply(rotation=True)
    for o in objs: boolean(o,c,'DIFFERENCE')
    O.remove(c)
def grow(m,k):
    for _ in range(k):
        d=m.copy()
        for ax in range(3):
            d|=np.roll(m,1,axis=ax); d|=np.roll(m,-1,axis=ax)
        m=d
    return m
near_cav=grow(cav,3)
def ijk(x,y,z): return int(round(x-org[0])),int(round(y-org[1])),int(round(z-org[2]))
def plane_holes(part,zs,box):
    cands=[]
    for x in range(int(box[0][0]),int(box[1][0])):
        for y in range(int(box[0][1]),int(box[1][1])):
            ok=True
            for z in (zs-6,zs-3,zs,zs+3,zs+6):
                i,j,k=ijk(x,y,z)
                if not solid[i,j,k] or near_cav[i,j,k]: ok=False; break
            if ok: cands.append((x,y))
    if not cands: log('WARN no hole spots for',part.name); return
    c=np.array(cands,float); picks=[c[np.argmin(c[:,0]+c[:,1])],c[np.argmax(c[:,0]+c[:,1])],c[np.argmin(c[:,0]-c[:,1])],c[np.argmax(c[:,0]-c[:,1])]]
    for x,y in picks: drill([O['block'],part],(x,y,zs),(0,0,1),8,8)
    log('holes',part.name,[(round(x),round(y)) for x,y in picks])
plane_holes(O['sump'],36.0,((30,52,0),(144,116,0)))
plane_holes(O['rocker_cover'],127.0,((22,60,0),(141,105,0)))
def contact_holes(part,target):
    t=BVHTree.FromObject(target,bpy.context.evaluated_depsgraph_get())
    vs=part.data.vertices; step=max(1,len(vs)//20000); pts=[]
    for i in range(0,len(vs),step):
        co=vs[i].co; h=t.find_nearest(co)
        if h[0] is not None and h[3]<0.35: pts.append((h[0],h[1]))
    if len(pts)<2: log('WARN no contact for',part.name); return
    P=np.array([[p.x,p.y,p.z] for p,_ in pts]); i=0; j=int(np.argmax(((P-P[0])**2).sum(1))); i=int(np.argmax(((P-P[j])**2).sum(1)))
    for k in (i,j):
        p,n=pts[k]; p2=Vector(P[k])+(Vector(P[(k+len(P)//2)%len(P)])-Vector(P[k]))*0.08   # nudge 8% inwards from the very edge
        drill([part,target],p2,n,14,10)
    log('holes',part.name,'->',target.name,[P[i].round().tolist(),P[j].round().tolist()])
for nm in ('exhaust_manifold','intake_manifold','alternator','oil_filter'): contact_holes(O[nm],O['block'])
contact_holes(O['air_filter'],O['intake_manifold'])
bpy.ops.wm.save_as_mainfile(filepath=OUT); log('saved')

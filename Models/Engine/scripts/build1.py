# Stage 1: upright, 150 mm, split moving parts, voxel-fuse body. Saves stage1.blend
import sys; sys.path.insert(0,sys.argv[-2])
from common import *
import bpy, time
t0=time.time()
P=load(sys.argv[-1])
CACHE={}
def pick(n,cy,cz,r,x0,x1):
    got=[]
    if n not in CACHE: CACHE[n]=islands(P[n])
    for p in [q for q in CACHE[n] if q.name in bpy.data.objects and q.users]:
        a,b=bb(p); c=(a+b)/2
        if x0<=c.x<=x1 and ((c.y-cy)**2+(c.z-cz)**2)**.5<=r and max(b.y-a.y,b.z-a.z)<=2*r+2: got.append(p); CACHE[n]=[q for q in CACHE[n] if q is not p]
    return got
def join(objs,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]; bpy.ops.object.join(); objs[0].name=name; return objs[0]
fly=pick('115',83,52,34,136,151)
crank=pick('25',83,52,15,10,22)+pick('17',83,52,8,15,22)
fan=pick('17',56,89,30,0,12)+pick('138',56,89,13,3,16)
print('picked',len(fly),len(crank),len(fan))
parts={'flywheel':join(fly,'flywheel'),'crank_pulley':join(crank,'crank_pulley'),'fan':join(fan,'fan')}
# body = everything else except belt and crankshaft
def mid(o): return o.name.split('.')[0]
src=[o for o in bpy.context.scene.objects if o.type=='MESH' and mid(o)=='M0']
mcopy=[]
for o in src:
    c=o.copy(); c.data=o.data.copy(); bpy.context.scene.collection.objects.link(c); mcopy.append(c)
MAN=join(mcopy,'manifold_src')
body=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in parts and o.name!='manifold_src' and mid(o) not in ('M3','M104')]
for o in [o for o in bpy.context.scene.objects if mid(o)=='M3']: bpy.data.objects.remove(o)
B=join(body,'body')
join([o for o in bpy.context.scene.objects if o.name.startswith('M104')],'crank')
def remesh(o,vs):
    m=o.modifiers.new('r','REMESH'); m.mode='VOXEL'; m.voxel_size=vs; m.adaptivity=0
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier='r')
for name,o in parts.items(): remesh(o,0.2)
remesh(MAN,0.25); MAN.hide_render=True
remesh(B,0.3)
print('body tris after remesh',len(B.data.polygons),'t',round(time.time()-t0))
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-3])

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
# --- add-on parts printed separately (own colour, screwed on): islands fully inside a box go to that part
GROUPS={  # name: (min xyz, max xyz) in mm, upright model
 'air_filter':      ((46,-4,138),(110,57,172)),
 'intake_manifold': ((38,-4,92),(134,63,150)),
 'alternator':      ((12,18,36),(58,60,90)),
 'oil_filter':      ((8,93,6),(52,134,82)),
 'exhaust_manifold':((33,101,60),(137,142,130)),
}
def inside(a,b,lo,hi): return all(a[i]>=lo[i] for i in range(3)) and all(b[i]<=hi[i] for i in range(3))
def touches(a,b,lo,hi): return all(a[i]<=hi[i] and b[i]>=lo[i] for i in range(3))
cand=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in parts and o.name!='manifold_src' and mid(o) not in ('M3','M104')]
got={g:[] for g in GROUPS}
for o in cand:
    a,b=bb(o)
    if not any(touches(a,b,*GROUPS[g]) for g in GROUPS): continue
    for p in islands(o):
        pa,pb=bb(p)
        for g,(lo,hi) in GROUPS.items():      # first matching box wins (air filter before intake)
            if inside(pa,pb,lo,hi): got[g].append(p); p.name='G_'+g; break
for g,objs in got.items():
    print('GROUP',g,len(objs))
    if objs: parts[g]=join(objs,g)
body=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name not in parts and not o.name.startswith('G_') and o.name!='manifold_src' and mid(o) not in ('M3','M104')]
for o in [o for o in bpy.context.scene.objects if mid(o)=='M3']: bpy.data.objects.remove(o)
# fuse the block WITH the add-ons (they plug its openings, so the voxel fuse keeps every wall), cut them out after
gcopies=[]
for g in GROUPS:
    if g in parts:
        c=parts[g].copy(); c.data=parts[g].data.copy(); bpy.context.scene.collection.objects.link(c); gcopies.append(c)
B=join(body+gcopies,'body')
join([o for o in bpy.context.scene.objects if o.name.startswith('M104')],'crank')
def remesh(o,vs):
    m=o.modifiers.new('r','REMESH'); m.mode='VOXEL'; m.voxel_size=vs; m.adaptivity=0
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier='r')
for name,o in parts.items(): remesh(o,0.2 if name in ('flywheel','crank_pulley','fan') else 0.25)
remesh(MAN,0.25); MAN.hide_render=True
remesh(B,0.3)
for g in GROUPS:
    if g in parts:
        # cutter = the add-on grown 0.4 mm (also the fitting gap), re-voxelised so it is a clean closed mesh
        cu=parts[g].copy(); cu.data=parts[g].data.copy(); bpy.context.scene.collection.objects.link(cu)
        d=cu.modifiers.new('grow','DISPLACE'); d.direction='NORMAL'; d.strength=0.4; d.mid_level=0
        bpy.context.view_layer.objects.active=cu; bpy.ops.object.modifier_apply(modifier='grow')
        remesh(cu,0.25)
        m=B.modifiers.new('cut','BOOLEAN'); m.operation='DIFFERENCE'; m.object=cu; m.solver='MANIFOLD'
        bpy.context.view_layer.objects.active=B; bpy.ops.object.modifier_apply(modifier='cut')
        bpy.data.objects.remove(cu)
print('body tris after remesh',len(B.data.polygons),'t',round(time.time()-t0))
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-3])

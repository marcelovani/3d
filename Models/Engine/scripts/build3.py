import bpy, sys, time, math
from mathutils import Vector
OUT=sys.argv[-1]; t0=time.time(); sc=bpy.context.scene; O=bpy.data.objects
sys.path.insert(0,sys.argv[-2]); from helpers import *
B=O['body']; cav=O['cavity']
if 'crank' in O: O.remove(O['crank'])
cut=[cav,
 cyl(1.7,175,(75,83,52),'X','axle'),
 cyl(1.0,26,(12,56,89),'X','fanpin'),
 cyl(4.0,30,(80,83,0),'Z','wires')]
CAPX,CAPY=90.5,76.5
capcut=cyl(8.6,20,(CAPX,CAPY,156),'Z','capcut')
cap=B.copy(); cap.data=B.data.copy(); sc.collection.objects.link(cap); cap.name='oil_cap'
boolean(cap,capcut,'INTERSECT')
peg=cyl(3.05,5.5,(CAPX,CAPY,143.75),'Z','peg'); boolean(cap,peg,'UNION'); O.remove(peg)
boolean(B,capcut,'DIFFERENCE'); O.remove(capcut)
cut+=[cyl(3.25,6.0,(CAPX,CAPY,143.0),'Z','capseat'), cyl(2.1,40,(CAPX,CAPY,125),'Z','hose')]
for c in cut: boolean(B,c,'DIFFERENCE'); log('cut',c.name,ntri(B))
for c in cut: O.remove(c)
SPLIT=36
bx=box((28,50,-10),(146,118,SPLIT),'sumpbox')
sump=B.copy(); sump.data=B.data.copy(); sc.collection.objects.link(sump); sump.name='sump'
boolean(sump,bx,'INTERSECT'); boolean(B,bx,'DIFFERENCE'); O.remove(bx); B.name='block'
hub=cyl(4.5,6,(16,83,52),'X','hub'); boolean(O['crank_pulley'],hub,'UNION'); O.remove(hub)
for n,loc,r in (('flywheel',(146,83,52),1.0),('crank_pulley',(16,83,52),1.0),('fan',(8,56,89),1.0)):   # 2 mm starter holes, drill to suit the rod
    f=cyl(r,40,loc,'X','bore'); boolean(O[n],f,'DIFFERENCE'); O.remove(f)
for n in ('flywheel','crank_pulley','fan'):
    cu=O[n].copy(); cu.data=O[n].data.copy(); bpy.context.scene.collection.objects.link(cu)
    d=cu.modifiers.new('grow','DISPLACE'); d.direction='NORMAL'; d.strength=0.5; d.mid_level=0; apply(cu,d)
    r=cu.modifiers.new('r','REMESH'); r.mode='VOXEL'; r.voxel_size=0.25; apply(cu,r)
    boolean(B,cu,'DIFFERENCE'); O.remove(cu)
log('parts',{o.name:ntri(o) for o in O if o.type=='MESH'})
bpy.ops.wm.save_as_mainfile(filepath=OUT)

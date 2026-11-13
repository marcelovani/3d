# render current blend objects from 2 views: view.py -- out_prefix
import bpy, sys
from mathutils import Vector
out=sys.argv[-1]; sc=bpy.context.scene
cols={'air_filter':(0.15,0.15,0.15,1),'intake_manifold':(0.75,0.75,0.8,1),'alternator':(0.9,0.5,0.1,1),'oil_filter':(0.1,0.5,0.9,1),'exhaust_manifold':(0.6,0.3,0.2,1),'rocker_cover':(0.8,0.1,0.1,1),'flywheel':(0.1,0.35,1,1),'fan':(0.1,0.8,0.2,1),'crank_pulley':(1,0.8,0,1),'sump':(0.9,0.6,0.4,1),'oil_cap':(1,0.2,0.2,1)}
ms=[o for o in sc.objects if o.type=='MESH' and not o.hide_render and o.name not in ('manifold_src','crank','motor_preview')]
for o in sc.objects:
    if o.type=='MESH' and o.name in ('manifold_src','crank','motor_preview'): o.hide_render=True
for o in ms: o.color=cols.get(o.name.split('.')[0],(0.55,0.6,0.55,1))
pts=[o.matrix_world@Vector(c) for o in ms for c in o.bound_box]
mn=Vector(map(min,*pts)); mx=Vector(map(max,*pts)); C=(mn+mx)/2; R=(mx-mn).length
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True
sc.render.resolution_x=sc.render.resolution_y=900
views=[('a',(1,-1.2,0.8)),('b',(-1,1.2,0.8))]
if len(sys.argv)>sys.argv.index('--')+2: views=[('a',(1,-1.2,0.8)),('b',(-1,1.2,0.8)),('c',(0.2,0.3,-1))]
for k,d in views:
    cam.location=C+Vector(d).normalized()*R*1.4
    cam.rotation_euler=(C-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=f"{out}_{k}.png"; bpy.ops.render.render(write_still=True)

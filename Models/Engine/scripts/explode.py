import bpy, sys
from mathutils import Vector
sc=bpy.context.scene; O=bpy.data.objects
off={'sump':(0,0,-45),'oil_cap':(0,0,35),'flywheel':(35,0,0),'crank_pulley':(-30,0,0),'fan':(-60,0,0)}
for n,d in off.items(): O[n].location=Vector(d)
cols={'flywheel':(0.1,0.35,1,1),'fan':(0.1,0.8,0.2,1),'crank_pulley':(1,0.8,0,1),'sump':(0.9,0.6,0.4,1),'oil_cap':(1,0.2,0.2,1)}
for o in O:
    if o.type=='MESH': o.color=cols.get(o.name,(0.82,0.82,0.82,1))
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True
sc.render.resolution_x=1200; sc.render.resolution_y=900
C=Vector((60,83,75)); cam.location=C+Vector((-0.6,1,0.45)).normalized()*420
cam.rotation_euler=(C-cam.location).to_track_quat('-Z','Y').to_euler()
sc.render.filepath=sys.argv[-1]; bpy.ops.render.render(write_still=True)

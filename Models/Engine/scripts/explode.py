# Exploded, coloured preview of all exported parts. explode.py -- <out.png>
import bpy, sys
from mathutils import Vector
sc=bpy.context.scene; O=bpy.data.objects
off={'sump':(0,0,-45),'rocker_cover':(0,0,40),'oil_cap':(0,0,70),'flywheel':(40,0,0),'crank_pulley':(-30,0,0),'fan':(-60,0,0),
     'air_filter':(0,-40,60),'intake_manifold':(0,-40,10),'alternator':(-20,-45,0),'oil_filter':(-20,40,-20),'exhaust_manifold':(0,45,0),
     'gear_axle':(0,0,0),'gear_motor':(0,0,0),'smoke_module':(0,0,95),'blower_lid':(25,0,95),'impeller':(12,0,95),'chamber_cap':(0,0,120)}
cols={'air_filter':(0.12,0.12,0.12,1),'intake_manifold':(0.78,0.78,0.82,1),'alternator':(0.9,0.55,0.1,1),'oil_filter':(0.1,0.45,0.9,1),
      'exhaust_manifold':(0.55,0.28,0.18,1),'rocker_cover':(0.8,0.1,0.1,1),'oil_cap':(0.95,0.85,0.1,1),'flywheel':(0.25,0.25,0.3,1),
      'fan':(0.1,0.75,0.25,1),'smoke_module':(0.6,0.2,0.8,1),'crank_pulley':(0.95,0.8,0.1,1),'sump':(0.25,0.25,0.3,1)}
for o in O:
    if o.type!='MESH': continue
    if o.name in ('motor_preview','manifold_src','crank'): o.hide_render=True; continue
    o.location=Vector(off.get(o.name,(0,0,0))); o.color=cols.get(o.name,(0.55,0.6,0.55,1))
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True
sc.render.resolution_x=1600; sc.render.resolution_y=1100
for k,d in (('a',(-0.6,-1,0.45)),('b',(0.6,1,0.45))):
    C=Vector((60,66,85)); cam.location=C+Vector(d).normalized()*520
    cam.rotation_euler=(C-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=sys.argv[-1].replace('.png',f'_{k}.png'); bpy.ops.render.render(write_still=True)

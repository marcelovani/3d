import bpy, sys
sys.path.insert(0,sys.argv[-2]); from helpers import *
from mathutils import Vector
out=sys.argv[-1]; sc=bpy.context.scene
for n in ('fan','sump','oil_cap'): O[n].hide_render=True
cols={'gear_axle':(1,0.8,0,1),'gear_motor':(1,0.5,0,1),'motor_preview':(1,0.1,0.1,1),'flywheel':(0.1,0.35,1,1),'crank_pulley':(1,0.8,0,1)}
for o in [o for o in O if o.type=='MESH']: o.color=cols.get(o.name,(0.82,0.82,0.82,1))
b=box((-10,-10,58),(170,200,200),'k'); boolean(O['block'],b,'DIFFERENCE'); O.remove(b)
r=cyl(1.5,150,(75,83,52),'X','rod'); r.color=(0.2,0.2,0.2,1)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True
sc.render.resolution_x=1400; sc.render.resolution_y=900
for k,d,dist in (('a',(0.35,0.25,1),170),('b',(0.5,-0.35,0.8),120)):
    C=Vector((95,72,48)); cam.location=C+Vector(d).normalized()*dist
    cam.rotation_euler=(C-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=out+k+'.png'; bpy.ops.render.render(write_still=True)

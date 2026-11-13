import bpy, sys
sys.path.insert(0,sys.argv[-2]); from helpers import *
from mathutils import Vector
out=sys.argv[-1]; sc=bpy.context.scene
for n in ('fan','flywheel','crank_pulley'): O[n].hide_render=True
cols={'sump':(0.9,0.6,0.4,1),'oil_cap':(1,0.2,0.2,1)}
for o in [o for o in O if o.type=='MESH']: o.color=cols.get(o.name,(0.82,0.82,0.82,1))
for n in ('block','sump','oil_cap'):
    b=box((-10,86,-10),(170,200,200),'k'); boolean(O[n],b,'DIFFERENCE'); O.remove(b)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.color_type='OBJECT'; sh.show_cavity=True
sc.render.resolution_x=sc.render.resolution_y=900
C=Vector((75,83,82)); cam.location=C+Vector((0.15,1,0.25)).normalized()*300
cam.rotation_euler=(C-cam.location).to_track_quat('-Z','Y').to_euler()
sc.render.filepath=out; bpy.ops.render.render(write_still=True)

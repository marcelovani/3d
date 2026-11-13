import bpy, sys
from mathutils import Vector
sc=bpy.context.scene; O=bpy.data.objects
for o in O:
    if o.type=='MESH': o.hide_render = o.name!='sump'
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.show_cavity=True
sc.render.resolution_x=sc.render.resolution_y=700
for k,d in (('bot',(0.1,0.2,-1)),('top',(0.1,0.2,1))):
    C=Vector((80,83,18)); cam.location=C+Vector(d).normalized()*260
    cam.rotation_euler=(C-cam.location).to_track_quat('-Z','Y').to_euler()
    sc.render.filepath=sys.argv[-1]+k+'.png'; bpy.ops.render.render(write_still=True)

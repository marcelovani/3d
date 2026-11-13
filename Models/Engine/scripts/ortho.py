# Orthographic views with a 10 mm grid, for locating parts. ortho.py -- <out_prefix> [hide,names]
import bpy, sys, math
from mathutils import Vector, Euler
out=sys.argv[sys.argv.index('--')+1]; hide=(sys.argv[sys.argv.index('--')+2].split(',') if len(sys.argv)>sys.argv.index('--')+2 else [])
sc=bpy.context.scene; O=bpy.data.objects
for o in O:
    if o.type=='MESH': o.hide_render = o.name in hide or o.name in ('motor_preview','manifold_src')
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=180
sc.render.engine='BLENDER_WORKBENCH'; sh=sc.display.shading; sh.light='STUDIO'; sh.show_cavity=True
sc.render.resolution_x=sc.render.resolution_y=900
C=Vector((75,66,82))
V={'left':((C.x,-200,C.z),(math.pi/2,0,0)),        # looking +y : x right, z up
   'right':((C.x,350,C.z),(math.pi/2,0,math.pi)),  # looking -y : x left,  z up
   'top':((C.x,C.y,400),(0,0,0)),                  # looking -z : x right, y up
   'front':((-200,C.y,C.z),(math.pi/2,0,-math.pi/2))} # looking +x : y left?, z up
for k,(loc,rot) in V.items():
    cam.location=loc; cam.rotation_euler=Euler(rot)
    sc.render.filepath=f'{out}_{k}.png'; bpy.ops.render.render(write_still=True)

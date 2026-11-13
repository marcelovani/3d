# Make a saved .blend open nicely: millimetre units, view framed on the engine, far clip distance.
import bpy
from mathutils import Vector
def setup_view(center=(75,66,82),distance=420):
    sc=bpy.context.scene
    sc.unit_settings.system='METRIC'; sc.unit_settings.scale_length=0.001; sc.unit_settings.length_unit='MILLIMETERS'
    for scr in bpy.data.screens:
        for area in scr.areas:
            if area.type!='VIEW_3D': continue
            for sp in area.spaces:
                if sp.type!='VIEW_3D': continue
                sp.clip_start=0.5; sp.clip_end=20000
                sp.overlay.grid_scale=10
                r=sp.region_3d; r.view_location=Vector(center); r.view_distance=distance
if __name__=='__main__':
    import sys; setup_view(); bpy.ops.wm.save_mainfile()

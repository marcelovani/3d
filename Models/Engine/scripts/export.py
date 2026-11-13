import bpy, bmesh, sys, os
import numpy as np
sys.path.insert(0,sys.argv[-2]); from helpers import *
OUT=os.path.expanduser(sys.argv[-1]); os.makedirs(OUT,exist_ok=True)
targets={'block':1300000,'sump':400000,'flywheel':300000,'fan':200000,'crank_pulley':100000,'oil_cap':40000,'gear_axle':50000,'gear_motor':50000,'rocker_cover':300000,'pulley_crank_inner':20000,'pulley_intermediate':20000,'pulley_blower':10000,'impeller':20000,'blower_lid':10000,'chamber_cap':10000,'exhaust_manifold':250000,'intake_manifold':300000,'air_filter':250000,'alternator':150000,'oil_filter':100000,'smoke_module':150000}
for n,t in targets.items():
    o=O[n]
    bm=bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    seen=np.zeros(len(bm.verts),bool); comps=[]
    for v in bm.verts:
        if seen[v.index]: continue
        st=[v]; seen[v.index]=True; c=[]
        while st:
            a=st.pop(); c.append(a)
            for e in a.link_edges:
                b=e.other_vert(a)
                if not seen[b.index]: seen[b.index]=True; st.append(b)
        comps.append(c)
    big=max(len(c) for c in comps)
    kill=[v for c in comps if len(c)<0.01*big for v in c]
    bmesh.ops.delete(bm,geom=kill,context='VERTS'); bm.to_mesh(o.data); bm.free()
    r=min(1,t/ntri(o))
    if r<1:
        m=o.modifiers.new('d','DECIMATE'); m.ratio=r; apply(o,m)
    act(o); bpy.ops.wm.stl_export(filepath=f'{OUT}/{n}.stl',export_selected_objects=True)
    log(n,'pieces',len(comps),'kept',sum(1 for c in comps if len(c)>=0.01*big),'tris',ntri(o))
for o in O:
    o.select_set(o.type=='MESH' and o.name!='motor_preview')
bpy.ops.wm.usd_export(filepath=f'{OUT}/engine-assembly.usdz',selected_objects_only=True)
from viewsetup import setup_view
setup_view()
bpy.ops.wm.save_as_mainfile(filepath=f'{OUT}/engine.blend')
log('exported')

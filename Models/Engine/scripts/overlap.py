# Report pairs of parts whose surfaces intersect (they should only touch with a gap).
import bpy, itertools
from mathutils.bvhtree import BVHTree
dg=bpy.context.evaluated_depsgraph_get()
skip={'motor_preview','manifold_src','crank'}
ms=[o for o in bpy.data.objects if o.type=='MESH' and o.name not in skip]
def wtree(o):
    mw=o.matrix_world; vs=[mw@v.co for v in o.data.vertices]; return BVHTree.FromPolygons(vs,[p.vertices[:] for p in o.data.polygons])
T={o.name:wtree(o) for o in ms}
for a,b in itertools.combinations(sorted(T),2):
    n=len(T[a].overlap(T[b]))
    if n: print('OVERLAP',a,b,n)
print('OVERLAP done')

# Stage 4: N20 motor sleeve fused to the block + pair of printed 16T module-1 spur gears.
import bpy, bmesh, sys, math
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
sys.path.insert(0,sys.argv[-2]); from helpers import *
OUT=sys.argv[-1]; sc=bpy.context.scene
AX=(83.0,52.0)                      # crank/axle line (y,z)
CD=16.2                             # gear centre distance (16 + 0.2 print clearance)
ANG=math.radians(210)               # motor position around the axle (found by cavity search)
MY,MZ=AX[0]+CD*math.cos(ANG),AX[1]+CD*math.sin(ANG)
GX0,GX1=98.5,103.5                  # gear faces (5 mm wide)
FACE=95.0                           # N20 gearbox face (shaft side)
MLEN=24.0; MW,MH=12.0,10.0          # N20 body: 12 x 10 x 24 mm
log('motor axis y,z',round(MY,2),round(MZ,2))
B=O['block']
def gear(name,teeth,m,width,x0,cy,cz,bore,dflat=None):
    pa=math.radians(20); rp=m*teeth/2; rb=rp*math.cos(pa); ra=rp+m; rf=rp-1.25*m
    inv=lambda a: math.tan(a)-a
    # half tooth angle at pitch circle, minus 0.1 mm backlash
    half=(math.pi/teeth)/2 - 0.05/rp
    pts=[]
    for k in range(teeth):
        c=2*math.pi*k/teeth
        prof=[]
        for i in range(9):
            r=rb+(ra-rb)*i/8 if rb>rf else rf+(ra-rf)*i/8
            r=max(r,rb); a=math.acos(rb/r); prof.append((r,half+inv(pa)-inv(a)))
        left=[(r,c-t) for r,t in prof]; right=[(r,c+t) for r,t in reversed(prof)]
        pts+= [(rf,c-half-inv(pa)-0.02)] + left + right + [(rf,c+half+inv(pa)+0.02)]
    bm=bmesh.new()
    vs0=[bm.verts.new((x0,cy+r*math.cos(t),cz+r*math.sin(t))) for r,t in pts]
    f=bm.faces.new(vs0)
    ext=bmesh.ops.extrude_face_region(bm,geom=[f]); 
    bmesh.ops.translate(bm,vec=(width,0,0),verts=[v for v in ext['geom'] if isinstance(v,bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    me=bpy.data.meshes.new(name); bm.to_mesh(me); o=O.new(name,me); sc.collection.objects.link(o)
    h=cyl(bore/2,width+4,(x0+width/2,cy,cz),'X','bore',48)
    if dflat:   # D-shaped bore: add back a flat
        fl=box((x0-3,cy-3,cz+dflat-bore/2),(x0+width+3,cy+3,cz+3),'flat'); boolean(h,fl,'DIFFERENCE'); O.remove(fl)
    boolean(o,h,'DIFFERENCE'); O.remove(h)
    return o
g1=gear('gear_axle',16,1.0,5.0,GX0,AX[0],AX[1],3.1)
hub=cyl(4,4,(GX0-2,AX[0],AX[1]),'X','hub'); h=cyl(1.55,10,(GX0-2,AX[0],AX[1]),'X','hb'); boolean(hub,h,'DIFFERENCE'); O.remove(h)
boolean(g1,hub,'UNION'); O.remove(hub)
g2=gear('gear_motor',16,1.0,5.0,GX0,MY,MZ,3.1,dflat=2.6)
# --- clearance pocket around both gears and the motor
pocket=[cyl(10.5,GX1-GX0+3,((GX0+GX1)/2,AX[0],AX[1]),'X','p1'), cyl(10.5,GX1-GX0+3,((GX0+GX1)/2,MY,MZ),'X','p2'),
        box((FACE-MLEN-4,MY-MW/2-1,MZ-MH/2-1),(GX0,MY+MW/2+1,MZ+MH/2+1),'p3')]
for p in pocket: boolean(B,p,'DIFFERENCE'); O.remove(p)
# --- sleeve: 1.6 mm walls, open at the front end, lip with 5 mm hole at the gearbox face
W=1.6; SX0=FACE-20
sleeve=box((SX0,MY-MW/2-0.2-W,MZ-MH/2-0.2-W),(FACE+W,MY+MW/2+0.2+W,MZ+MH/2+0.2+W),'sleeve')
# web from the sleeve to the nearest side wall (-y), found by raycast
t=BVHTree.FromObject(B,bpy.context.evaluated_depsgraph_get())
ys=[]
for x in range(int(SX0)+2,int(FACE),3):
    for dz in (-3,0,3):
        h=t.ray_cast(Vector((x,MY,MZ+dz)),Vector((0,-1,0)))
        if h[0]: ys.append(h[0].y)
wall=max(ys) if ys else MY-12
log('side wall at y',round(wall,1))
web=box((SX0+3,wall-1.5,MZ-3),(FACE-3,MY-MW/2,MZ+3),'web')
boolean(sleeve,web,'UNION'); O.remove(web)
inner=box((SX0-1,MY-MW/2-0.2,MZ-MH/2-0.2),(FACE,MY+MW/2+0.2,MZ+MH/2+0.2),'inner')
boolean(sleeve,inner,'DIFFERENCE'); O.remove(inner)
sh=cyl(2.5,10,(FACE+W/2,MY,MZ),'X','shaft'); boolean(sleeve,sh,'DIFFERENCE'); O.remove(sh)
boolean(B,sleeve,'UNION'); O.remove(sleeve)
# axle hole again (pocket/union may have touched it)
a=cyl(1.7,175,(75,AX[0],AX[1]),'X','axle'); boolean(B,a,'DIFFERENCE'); O.remove(a)
# placeholder motor for previews only (not exported)
m=box((FACE-MLEN,MY-MW/2,MZ-MH/2),(FACE,MY+MW/2,MZ+MH/2),'motor_preview')
bpy.ops.wm.save_as_mainfile(filepath=OUT); log('saved')

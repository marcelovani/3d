# Stage 5: smoke system.
#  - removable rocker cover (split at z=127)
#  - blower: plate fused across the upper block, scroll housing in the head, impeller + lid
#  - two rubber-band step-up stages on the front side of the plate (crank -> intermediate -> blower)
#  - atomizer chamber (vertical) fed by the blower, smoke gallery along the head to the 4 exhaust ports
#  - hollow exhaust manifold + exhaust stub out behind the flywheel
#  - air intake: hole down through the air filter into the cavity
import bpy, bmesh, sys, math
import numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0,sys.argv[-3]); from helpers import *
WORK=sys.argv[-2]; OUT=sys.argv[-1]; sc=bpy.context.scene
cav=np.load(WORK+'/stage2.blend.cav.npy'); solid=np.load(WORK+'/stage2.blend.solid.npy'); org=np.load(WORK+'/stage2.blend.org.npy')
def erode(a,k):
    for _ in range(k):
        r=a.copy()
        for ax in range(3):
            for s in (1,-1): r&=np.roll(a,s,axis=ax)
        a=r
    return a
safe=erode(solid,2)                       # >= ~2 mm from the outside: safe to cut
def ijk(p): return tuple(int(round(p[n]-org[n])) for n in range(3))
def cutcheck(name,pts):
    bad=[p for p in pts if not safe[ijk(p)]]
    log('wallcheck',name,'unsafe %d/%d'%(len(bad),len(pts)), bad[:3])
def cylpts(c,r,x0,x1,axis='X'):
    out=[]
    for x in np.arange(x0,x1+0.01,1.0):
        for rr in np.arange(0,r+0.01,1.0):
            for t in np.linspace(0,2*math.pi,max(6,int(rr*6)),endpoint=False):
                a,b=c[0]+rr*math.cos(t),c[1]+rr*math.sin(t)
                out.append((x,a,b) if axis=='X' else (a,b,x))
    return out
def hull(objs,name):
    bm=bmesh.new()
    for o in objs:
        for v in o.data.vertices: bm.verts.new(o.matrix_world@v.co)
        O.remove(o)
    bmesh.ops.convex_hull(bm,input=bm.verts)
    me=bpy.data.meshes.new(name); bm.to_mesh(me); o=O.new(name,me); sc.collection.objects.link(o); return o
def tube_x(r_out,r_in,x0,x1,y,z,name):
    o=cyl(r_out,x1-x0,((x0+x1)/2,y,z),'X',name); i=cyl(r_in,x1-x0+2,((x0+x1)/2,y,z),'X','i'); boolean(o,i,'DIFFERENCE'); O.remove(i); return o
def pulley(name,x0,w,r,y,z,bore,flange=1.0):
    p=cyl(r,w,(x0+w/2,y,z),'X',name)
    for xx in (x0+0.4,x0+w-0.4):
        f=cyl(r+flange,0.8,(xx,y,z),'X','f'); boolean(p,f,'UNION'); O.remove(f)
    b=cyl(bore/2,w+4,(x0+w/2,y,z),'X','b'); boolean(p,b,'DIFFERENCE'); O.remove(b); return p
B=O['block']
AX=(83.0,52.0)            # crank axle (y,z)
INT=(84.0,85.0)           # intermediate rod
BLW=(80.0,118.0)          # blower rod
PX0,PX1=62.0,65.0         # plate
# ---------- 1. rocker cover split
SPLITZ=127.0
cb=box((20,58,SPLITZ),(143,107,170),'coverbox')
cover=B.copy(); cover.data=B.data.copy(); sc.collection.objects.link(cover); cover.name='rocker_cover'
boolean(cover,cb,'INTERSECT'); boolean(B,cb,'DIFFERENCE'); O.remove(cb)
log('cover split',ntri(cover))
# ---------- 2. clearance pockets (checked against the outside)
p1=hull([cyl(15.5,7,(58,AX[0],AX[1]),'X','a'),cyl(6,7,(58,INT[0],INT[1]),'X','b')],'belt1')
p2=hull([cyl(13,7,(52,INT[0],INT[1]),'X','a'),cyl(6,7,(52,BLW[0],BLW[1]),'X','b')],'belt2')
cutcheck('belt1',[ (x,AX[0]+t*(INT[0]-AX[0])+dy,AX[1]+t*(INT[1]-AX[1])) for x in (55,58,61) for t in np.linspace(0,1,12) for dy in (-12,0,12)])
cutcheck('belt2',[ (x,INT[0]+t*(BLW[0]-INT[0])+dy,INT[1]+t*(BLW[1]-INT[1])) for x in (49,52,55) for t in np.linspace(0,1,12) for dy in (-10,0,10)])
cutcheck('housing',cylpts(BLW,12.5,66,76)); cutcheck('chamber',cylpts((84,93),5.3,104,126,'Z'))
for p in (p1,p2): boolean(B,p,'DIFFERENCE'); O.remove(p)
# ---------- 3. SMOKE MODULE (separate part, assembled on the bench, lowered in from the top, screwed through the block wall)
# plate = the cavity cross-section at x 62..65 shrunk 1 voxel (≈0.5-1 mm all round, so it drops in), z 70..SPLITZ
i0,i1=ijk((PX0,0,0))[0],ijk((PX1,0,0))[0]
m=np.zeros_like(cav); sl=cav[i0:i1+1].copy()
e=sl.copy(); e[:,1:]&=sl[:,:-1]; e[:,:-1]&=sl[:,1:]; e[:,:,1:]&=sl[:,:,:-1]; e[:,:,:-1]&=sl[:,:,1:]
m[i0:i1+1]=e
zz=np.arange(m.shape[2])+org[2]; m[:,:,(zz<70)|(zz>SPLITZ-0.5)]=False
mod=to_mesh(m,org,1.0,'smoke_module',0.6)
for c,rr,x0,x1 in ((INT,4.5,PX0,PX1+6),(BLW,4.5,PX0-4,PX1)):        # rod bosses
    bo=cyl(rr,x1-x0,((x0+x1)/2,c[0],c[1]),'X','boss'); boolean(mod,bo,'UNION'); O.remove(bo)
# blower housing behind the plate, open at x=76 for the lid
HX0,HX1=PX1,76.0; HR=12.5
hs=cyl(HR+1.6,HX1-HX0,((HX0+HX1)/2,BLW[0],BLW[1]),'X','housing'); boolean(mod,hs,'UNION'); O.remove(hs)
# atomizer chamber: vertical tube ID 10.6, z 105..SPLITZ, at (84,89) — clear of the gallery in the block
CH=(84.0,89.0); CZ0=98.0
ch=cyl(7.0,SPLITZ-CZ0,(CH[0],CH[1],(SPLITZ+CZ0)/2),'Z','chamber'); boolean(mod,ch,'UNION'); O.remove(ch)
du=box((70,84,119),(80,95,SPLITZ),'duct'); boolean(mod,du,'UNION'); O.remove(du)                      # housing -> chamber
cn=cyl(2.5,9,(CH[0]+7+3.5,CH[1],CZ0+4),'X','cnip'); boolean(mod,cn,'UNION'); O.remove(cn)               # smoke outlet nipple (+x), below the atomizer
for c in [cyl(HR,HX1-HX0,((HX0+1+HX1)/2+0.5,BLW[0],BLW[1]),'X','housingin'),
          cyl(5.3,SPLITZ-CZ0+2,(CH[0],CH[1],(SPLITZ+CZ0+4)/2),'Z','chin'),
          box((71,86,121),(CH[0],93,SPLITZ-1.5),'ductin'),
          cyl(1.5,14,(CH[0]+7+2,CH[1],CZ0+4),'X','cnipin'),
          cyl(1.0,20,((PX0-4+PX1)/2,BLW[0],BLW[1]),'X','blowerbearing'),
          cyl(1.0,14,(PX0+3,INT[0],INT[1]),'X','introd')]:
    boolean(mod,c,'DIFFERENCE'); O.remove(c)
# keep the module clear of the block: cut a 0.4 mm-grown copy of it out of the block
cu=mod.copy(); cu.data=mod.data.copy(); sc.collection.objects.link(cu)
d=cu.modifiers.new('grow','DISPLACE'); d.direction='NORMAL'; d.strength=0.4; d.mid_level=0; apply(cu,d)
r=cu.modifiers.new('r','REMESH'); r.mode='VOXEL'; r.voxel_size=0.3; apply(cu,r)
boolean(B,cu,'DIFFERENCE'); O.remove(cu)
# 2 screw starter holes through the block side wall into the plate edge (-y side), at z 80 and 115
for zh in (75.0,88.0):   # below the intake manifold (z >= 92)
    hole=cyl(0.75,36,((PX0+PX1)/2,58,zh),'Y','modscrew',24)   # y 40..76
    boolean(B,hole,'DIFFERENCE'); boolean(mod,hole,'DIFFERENCE'); O.remove(hole)
log('smoke module',ntri(mod))
# ---------- 4. smoke gallery in the block: tube along x at (y100,z106), inlet nipple pointing up at x 72
GY,GZ=100.0,106.0
ga=cyl(3.8,83,(90.5,GY,GZ),'X','gallery'); boolean(B,ga,'UNION'); O.remove(ga)
gn=cyl(2.5,7,(72,GY,GZ+3.8+3),'Z','gnip'); boolean(B,gn,'UNION'); O.remove(gn)
for c in [cyl(2.25,81,(90.5,GY,GZ),'X','galin'), cyl(1.5,12,(72,GY,GZ+5),'Z','gnipin')]:
    boolean(B,c,'DIFFERENCE'); O.remove(c)
gc=cyl(4.3,90,(90.5,GY,GZ),'X','galclear'); boolean(mod,gc,'DIFFERENCE'); O.remove(gc)   # notch the module where the gallery passes
log('gallery done')
# ---------- 6. hollow exhaust manifold: voxelise the closed copy, erode 1.2 mm -> channel
from mathutils.bvhtree import BVHTree
M=O['manifold_src']; t=BVHTree.FromObject(M,bpy.context.evaluated_depsgraph_get())
vs=np.array([v.co for v in M.data.vertices]); lo=vs.min(0)-1; hi=vs.max(0)+1; G=0.4
dims=np.ceil((hi-lo)/G).astype(int)
occ=np.zeros(dims,bool)
for i in range(dims[0]):
    for j in range(dims[1]):
        x,y=lo[0]+(i+.5)*G, lo[1]+(j+.5)*G; hz=[]; p=Vector((x,y,lo[2]-1))
        while len(hz)<64:
            h=t.ray_cast(p,Vector((0,0,1)))
            if not h[0]: break
            hz.append(h[0].z); p=Vector((x,y,h[0].z+1e-4))
        for a,b in zip(hz[0::2],hz[1::2]):
            k0=int(np.ceil((a-lo[2])/G-.5)); k1=int(np.floor((b-lo[2])/G-.5)); occ[i,j,max(k0,0):k1+1]=True
chan=erode(occ,3)
log('manifold occ',int(occ.sum()),'channel',int(chan.sum()))
cpts=np.argwhere(chan)*G+lo+G/2
# outlet = lowest channel point; ports = channel points nearest the head (smallest y), clustered by x
low=cpts[cpts[:,2]<cpts[:,2].min()+1.5]; OUTL=low.mean(0); log('collector outlet',OUTL.round(1).tolist())
near=cpts[cpts[:,1]<cpts[:,1].min()+3]
xs=np.sort(near[:,0]); groups=np.split(xs,np.where(np.diff(xs)>4)[0]+1)
PORTS=[]
for g in groups:
    sel=near[(near[:,0]>=g.min())&(near[:,0]<=g.max())]; PORTS.append(sel.mean(0))
log('ports',[p.round(1).tolist() for p in PORTS])
mch=to_mesh(chan,lo+G/2,G,'manifold_channel',G*0.8)
EM=O['exhaust_manifold']
boolean(EM,mch,'DIFFERENCE'); O.remove(mch)
# ports: gallery -> each manifold pipe start
for p in PORTS:
    a=cyl(1.75,1,(p[0],GY,GZ),'Y','pa'); b=cyl(1.75,1,(p[0],p[1]+2,p[2]),'Y','pb')
    h=hull([a,b],'port'); boolean(B,h,'DIFFERENCE'); boolean(EM,h,'DIFFERENCE'); O.remove(h)
# ---------- 7. exhaust stub: down from the collector, then back past the flywheel
SX,SY,SZ=OUTL; Z2=58.0; XEND=152.0   # z 58 keeps it above the sump and outside the flywheel rim
legs=[cyl(3.5,SZ-Z2+3.5,(SX,SY,(SZ+Z2)/2-1),'Z','leg1'), cyl(3.5,XEND-SX,((SX+XEND)/2,SY,Z2),'X','leg2')]
for l in legs: boolean(EM,l,'UNION'); O.remove(l)
bores=[cyl(2.0,SZ-Z2+4,(SX,SY,(SZ+Z2)/2+1),'Z','b1'), cyl(2.0,XEND-SX+4,((SX+XEND)/2+1,SY,Z2),'X','b2')]
for b in bores: boolean(EM,b,'DIFFERENCE'); O.remove(b)
# ---------- 8. air intake: down through the air filter lid, across into the cavity
best=None
for x in (60,64,70,76,82,88):
    for zc in (110,114,118,122):
        path=[(x,26,z) for z in np.arange(zc,160,1.0)]+[(x,y,zc) for y in np.arange(26,58,1.0)]
        ok=sum(1 for q in path if safe[ijk(q)])/len(path)
        if best is None or ok>best[0]: best=(ok,x,zc)
log('intake best',best)
IX,IZ=best[1],best[2]
for c in (cyl(2.5,170-IZ,(IX,26,(170+IZ)/2),'Z','in1'), hull([cyl(2.5,1,(IX,26,IZ),'Y','a'),cyl(2.5,1,(IX,64,IZ),'Y','b')],'in2')):
    for tgt in (B,O['intake_manifold'],O['air_filter']): boolean(tgt,c,'DIFFERENCE')
    O.remove(c)
# ---------- 9. separate moving / loose parts
pulley('pulley_crank_inner',55.0,6.0,14.0,AX[0],AX[1],2.0)
pi=pulley('pulley_intermediate',55.0,6.0,4.0,INT[0],INT[1],2.0)
pb=pulley('pi_big',49.0,6.0,11.0,INT[0],INT[1],2.0); boolean(pi,pb,'UNION'); O.remove(pb)
pulley('pulley_blower',49.0,6.0,4.0,BLW[0],BLW[1],2.0)
# impeller: back disc + 8 radial blades + hub, x 66.5..74.5, radius 11
im=cyl(11,1.2,(67.1,BLW[0],BLW[1]),'X','impeller')  # x 66.5..73.4, lid plug starts at 73.8
for k in range(8):
    a=2*math.pi*k/8
    bl=box((67.6,-0.6,3.5),(73.4,0.6,11),'blade')
    bl.matrix_world=Matrix.Translation((0,BLW[0],BLW[1]))@Matrix.Rotation(a,4,'X'); act(bl); bpy.ops.object.transform_apply(location=True,rotation=True)
    boolean(im,bl,'UNION'); O.remove(bl)
hb=cyl(3.5,6.8,(70.0,BLW[0],BLW[1]),'X','hub'); boolean(im,hb,'UNION'); O.remove(hb)
b=cyl(1.0,12,(70.5,BLW[0],BLW[1]),'X','b'); boolean(im,b,'DIFFERENCE'); O.remove(b)
# housing lid: plug into the open housing face, 9 mm inlet
lid=cyl(HR-0.15,2.0,(HX1-1.0,BLW[0],BLW[1]),'X','blower_lid')   # push-in plug x 74..76
lh=cyl(4.5,10,(HX1,BLW[0],BLW[1]),'X','lh'); boolean(lid,lh,'DIFFERENCE'); O.remove(lh)
# chamber cap: plug with glycerin hose nipple (4 mm hose) and a wire slot
cap=cyl(7.0,1.6,(CH[0],CH[1],SPLITZ+0.8),'Z','chamber_cap'); pl=cyl(5.15,3.4,(CH[0],CH[1],SPLITZ-1.5),'Z','pl'); boolean(cap,pl,'UNION'); O.remove(pl)
nip=cyl(1.4,6,(CH[0]-2,CH[1],SPLITZ+4.4),'Z','nip'); boolean(cap,nip,'UNION'); O.remove(nip)
nb=cyl(0.8,20,(CH[0]-2,CH[1],SPLITZ),'Z','nb'); boolean(cap,nb,'DIFFERENCE'); O.remove(nb)
ws=box((CH[0]+1.5,CH[1]-1.5,SPLITZ-5),(CH[0]+4.0,CH[1]+1.5,SPLITZ+3),'ws'); boolean(cap,ws,'DIFFERENCE'); O.remove(ws)
O.remove(M)
bpy.ops.wm.save_as_mainfile(filepath=OUT); log('saved')

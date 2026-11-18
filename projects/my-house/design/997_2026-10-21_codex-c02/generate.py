"""Exploratory C02 room solver. Side-boundary frame ONLY; no road-default call.

Uses explicit room topology, CP-SAT NoOverlap2D, aligned three-level core,
screened service access, then the shared canonical assembler and checks.
"""
import argparse
import json
import math
import time
from itertools import combinations
from pathlib import Path

import ortools
from ortools.sat.python import cp_model
from shapely.geometry import Polygon
from shapely.ops import unary_union

from house_ai.domain.model import OpeningKind, Operation
from house_ai.domain.program import SpaceFunction as F, SpaceProgram
from house_ai.domain.site import Site
from house_ai.domain.plan import PlanVersion, GenerationRecord
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, Provenance
from house_ai.domain.integrity import check_model
from house_ai.domain.records import Assumption
from house_ai.domain.terrain import elevation_at
from house_ai.generation.frame import DesignFrame, Ground
from house_ai.generation.solver2d import PlacedRoom2D, SharedWall, Solution2D
from house_ai.generation.assemble2d import Builder2D
from house_ai.render2d.plan_svg import render_plan_svg
from house_ai.storage import ProjectStore

ROOT=Path(__file__).resolve().parent
store=ProjectStore(ROOT.parents[1])
actor=Actor(kind=ActorKind.AGENT,id='codex')
sref=store.latest(ArtifactKind.SITE,'site')
pref=store.latest(ArtifactKind.SPACE_PROGRAM,'program')
site=store.get(sref,Site);program=store.get(pref,SpaceProgram)
nw,sw,se,ne=site.boundary.outer
dist=math.dist(nw,ne); east=((ne[0]-nw[0])/dist,(ne[1]-nw[1])/dist)
south=(east[1],-east[0])
# Move western face from C01's 5.5m to 3.0m along the long edge.
# The approach must subsequently pass an actual vehicle sweep test.
origin=(nw[0]+3*east[0]+1.2*south[0],nw[1]+3*east[1]+1.2*south[1])
frame=DesignFrame(origin,east,south,'Owner-required long-side-boundary alignment; u downhill ENE, v toward south',None,None)
z=elevation_at(site.terrain.surface,((nw[0]+sw[0])/2,(nw[1]+sw[1])/2))

def solve(option,width,height,seconds=60):
    day='lv-entry' if option=='a' else 'lv-lower'
    night='lv-lower' if option=='a' else 'lv-entry'
    levels=['lv-lower','lv-entry','lv-upper']
    # centimetre-neutral decimetre grid, illustrative 0.6m eastward steps.
    bounds={'lv-upper':(0,120),'lv-entry':(6,width),'lv-lower':(12,width+6)}
    md=cp_model.CpModel();rooms={};vs={};links=[];objective=[]
    def add(key,name,fn,lv,target,minw,maxw=None,pid=None):
        a,b=bounds[lv]
        pairs=[]
        if fn==F.STAIR:pairs=[(26,50)]
        elif fn==F.LIFT:pairs=[(20,22)]
        elif fn==F.GARAGE:pairs=[(65,70),(66,70),(65,72)]
        else:
            low=math.ceil(target*.91*100);high=math.ceil(target*1.13*100)
            for w in range(minw,min(b-a,maxw or b-a)+1,2):
                for h in range(minw,height+1,2):
                    if low<=w*h<=high and max(w,h)<=min(w,h)*(1.75 if fn in [F.HALL,F.ENTRY] else 2.25):pairs.append((w,h))
        if not pairs:raise ValueError(key)
        x=md.NewIntVar(a,b,key+'x');y=md.NewIntVar(0,height,key+'y')
        w=md.NewIntVar(min(p[0] for p in pairs),max(p[0] for p in pairs),key+'w')
        h=md.NewIntVar(min(p[1] for p in pairs),max(p[1] for p in pairs),key+'h')
        xe=md.NewIntVar(a,b,key+'xe');ye=md.NewIntVar(0,height,key+'ye')
        md.Add(xe==x+w);md.Add(ye==y+h)
        area=md.NewIntVar(1,30000,key+'area');md.AddMultiplicationEquality(area,[w,h])
        md.AddAllowedAssignments([w,h],pairs)
        dev=md.NewIntVar(0,30000,key+'dev');md.AddAbsEquality(dev,area-round(target*100));objective.append(dev)
        rooms[key]={'name':name,'fn':fn,'lv':lv,'pid':pid or 'pi-'+key,'target':target}
        vs[key]=(x,y,xe,ye,w,h,area)
    def touch(a,b,span=12):
        xa,ya,ea,na,*_=vs[a];xb,yb,eb,nb,*_=vs[b]
        flags=[]
        for label,eq,lo1,hi1,lo2,hi2 in [('e',ea==xb,ya,na,yb,nb),('w',eb==xa,ya,na,yb,nb),('n',na==yb,xa,ea,xb,eb),('s',nb==ya,xa,ea,xb,eb)]:
            f=md.NewBoolVar(a+b+label);md.Add(eq).OnlyEnforceIf(f)
            md.Add(hi1-lo2>=span).OnlyEnforceIf(f);md.Add(hi2-lo1>=span).OnlyEnforceIf(f)
            flags.append(f)
        guard=md.NewBoolVar('required-'+a+'--'+b);md.AddBoolOr(flags).OnlyEnforceIf(guard);md.AddAssumption(guard);links.append((a,b))
    def exterior(k,edge=None):
        x,y,xe,ye,*_=vs[k];a,b=bounds[rooms[k]['lv']]
        eqs={'west':x==a,'east':xe==b,'north':y==0,'south':ye==height}
        if edge:md.Add(eqs[edge]);return
        fs=[]
        for n,eq in eqs.items():
            f=md.NewBoolVar(k+'ext'+n);md.Add(eq).OnlyEnforceIf(f);fs.append(f)
        md.AddBoolOr(fs)

    for lv in levels:
        add('stair-'+lv,'Shared stair',F.STAIR,lv,13,26,pid='pi-stair')
        add('lift-'+lv,'Lift',F.LIFT,lv,4.4,20,pid='pi-lift')
    for k in ['stair-','lift-']:
        for lv in levels[1:]:
            for i in [0,1,2,3]:md.Add(vs[k+lv][i]==vs[k+levels[0]][i])
    add('garage','Two-car garage',F.GARAGE,'lv-upper',45.5,65,pid='pi-garage')
    add('office','Quiet office',F.STUDY,'lv-upper',12,28,pid='pi-study-1')
    add('plant','Plant / utilities',F.MECHANICAL,'lv-upper',5,20,pid='pi-mechanical')
    add('top-lobby','Lift lobby',F.HALL,'lv-upper',10,24)
    exterior('garage','west');exterior('office')
    for k in ['garage','stair-lv-upper','lift-lv-upper']:touch('top-lobby',k)
    touch('garage','plant');touch('top-lobby','office')
    # Deliberately no direct toilet/day-room door and no kitchen/living aperture.
    add('living','Living',F.LIVING,day,34,44,pid='pi-living')
    add('dining','Dining',F.DINING,day,15,30,pid='pi-dining')
    add('kitchen','Kitchen + daily eating',F.KITCHEN,day,22,36,pid='pi-kitchen')
    add('pantry','Pantry',F.PANTRY,day,4,18,pid='pi-pantry')
    add('day-lobby','Entrance / shared landing',F.HALL,day,11,28)
    add('bath-vest','Screened vestibule',F.HALL,day,3,14)
    add('day-bath','Shower / WC',F.BATHROOM,day,5.5,20,pid='pi-bath-2')
    add('store','Store',F.STORAGE,day,4,18,pid='pi-storage')
    for a,b,span in [('living','dining',24),('dining','kitchen',16),('kitchen','pantry',12),('kitchen','day-lobby',12),('day-lobby','living',12),('day-lobby','bath-vest',12),('bath-vest','day-bath',12),('bath-vest','store',12),('day-lobby','stair-'+day,12),('day-lobby','lift-'+day,12)]:touch(a,b,span)
    exterior('living','east');exterior('kitchen')
    # Enclosed kitchen, but two routes at different interfaces; cooking activity screened.
    add('main-bed','Parents',F.BEDROOM,night,17,34,pid='pi-bed-main')
    add('elder-bed','Grandparents',F.BEDROOM,night,16,34,pid='pi-bed-elder-1')
    add('boys','Boys / two beds',F.BEDROOM,night,15,32,pid='pi-bed-child-1')
    add('girls','Girls / two beds',F.BEDROOM,night,15,32,pid='pi-bed-child-2')
    add('ensuite','En-suite',F.BATHROOM,night,6,24,pid='pi-bath-ensuite')
    add('night-bath','Shared bathroom',F.BATHROOM,night,6.5,22,pid='pi-bath-1')
    add('laundry','Laundry',F.LAUNDRY,night,4.5,20,pid='pi-laundry')
    add('night-lobby','Private family landing',F.HALL,night,8,24)
    add('adult-vest','Adult bedroom vestibule',F.HALL,night,3.5,16)
    add('child-vest','Children bedroom vestibule',F.HALL,night,3.5,16)
    for k in ['stair-'+night,'lift-'+night,'adult-vest','child-vest']:touch('night-lobby',k)
    for k in ['main-bed','elder-bed','night-bath']:touch('adult-vest',k)
    for k in ['boys','girls','laundry']:touch('child-vest',k)
    touch('main-bed','ensuite')
    for k in ['main-bed','elder-bed','boys','girls']:exterior(k)
    # Balcony is reached from a communal room/landing, never through a bedroom.
    add('main-entry','Screened entrance',F.ENTRY,'lv-entry',4.5,18,pid='pi-entry')
    touch('main-entry','day-lobby' if day=='lv-entry' else 'night-lobby')
    exterior('main-entry','south')
    if option=='a':
        add('lower-entry','Garden entrance',F.ENTRY,'lv-lower',3.5,16)
        touch('lower-entry','night-lobby')
        exterior('lower-entry','south')
    for lv in levels:
        ks=[k for k,r in rooms.items() if r['lv']==lv]
        ix=[];iy=[]
        for k in ks:
            x,y,xe,ye,w,h,area=vs[k]
            ix.append(md.NewIntervalVar(x,w,xe,k+'ix'));iy.append(md.NewIntervalVar(y,h,ye,k+'iy'))
        md.AddNoOverlap2D(ix,iy)
        # Avoid a loosely scattered collection; quantify rather than hide leftover space.
        a,b=bounds[lv]
        md.Add(sum(vs[k][6] for k in ks)>=int((b-a)*height*(.68 if lv=='lv-upper' else .77)))
    md.Minimize(sum(objective))
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1
    solver.parameters.random_seed=18;solver.parameters.max_time_in_seconds=seconds
    solver.parameters.log_search_progress=False
    start=time.monotonic();status=solver.Solve(md)
    info={'status':solver.StatusName(status),'width_dm':width,'height_dm':height,'wall_time_s':time.monotonic()-start}
    print(json.dumps(info),flush=True)
    if status not in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
        return None,info
    placed=[]
    for k,r in rooms.items():
        x,y,xe,ye,*_=vs[k]
        placed.append(PlacedRoom2D('sp-'+k,r['name'],r['fn'],r['lv'],*[solver.Value(v) for v in [x,y,xe,ye]],r['pid'],'z-private' if r['lv']==night else 'z-day'))
    by={r.space_id[3:]:r for r in placed};shared=[]
    for a,b in links:
        ra,rb=by[a],by[b]
        if ra.u1==rb.u0 or rb.u1==ra.u0:
            o='v';c=ra.u1 if ra.u1==rb.u0 else rb.u1;lo=max(ra.v0,rb.v0);hi=min(ra.v1,rb.v1)
        else:o='h';c=ra.v1 if ra.v1==rb.v0 else rb.v1;lo=max(ra.u0,rb.u0);hi=min(ra.u1,rb.u1)
        shared.append(SharedWall(ra.space_id,rb.space_id,ra.level_id,o,c,lo,hi,True))
    # Balcony geometry derives from the solved communal east face.
    access=by['living'] if day=='lv-entry' else by['main-entry']
    if option=='a':
        balcony=PlacedRoom2D('sp-balcony','Upper residential balcony',F.TERRACE,'lv-entry',access.u1,access.v0,access.u1+20,access.v1,'pi-balcony','z-outdoor')
        shared.append(SharedWall(access.space_id,balcony.space_id,'lv-entry','v',access.u1,access.v0,access.v1,True))
    else:
        balcony=PlacedRoom2D('sp-balcony','Upper south balcony / ENE outlook',F.TERRACE,'lv-entry',access.u0,access.v1,access.u0+60,access.v1+20,'pi-balcony','z-outdoor')
        shared.append(SharedWall(access.space_id,balcony.space_id,'lv-entry','h',access.v1,access.u0,access.u1,True))
    placed.append(balcony)
    ext=['sp-garage','sp-main-entry','sp-living']
    sol=Solution2D(status=solver.StatusName(status),objective=solver.ObjectiveValue(),rooms=placed,shared_walls=shared,
        circulation_rooms=[],levels=levels,deterministic_time=solver.deterministic_time,wall_time_s=info['wall_time_s'],seed=18,
        platform_info='local',strategy='corridor_free',circulation_share=0,has_stairs=True,exterior_connections=ext,
        level_elevations_m={'lv-upper':z,'lv-entry':z-3,'lv-lower':z-6})
    return (sol,day,night,bounds),info

class Builder(Builder2D):
    def build_openings(self):
        # Explicit door graph, with exterior edges selected by architectural role.
        entry='sp-main-entry'
        for sid,edge,width in [('sp-garage','west',5.5),(entry if day=='lv-entry' else 'sp-balcony','south',1.1),('sp-living','east',2.4)]:
            segs=self._walls_between(sid,None)
            # The assembler chooses by available span; constrain candidates temporarily
            # to the intended facade without moving any solved geometry.
            target=[w for w in segs if (w.orient=='v' if edge in ['west','east'] else w.orient=='h')]
            if target:
                c=(min if edge in ['west','north'] else max)(w.c for w in target)
                target=[w for w in target if w.c==c]
            old=self.walls
            self.walls=[w for w in old if w not in segs or w in target]
            self.place_opening(sid,None,OpeningKind.DOOR,width_m=width,operation=Operation.SLIDING,prefix='d-exterior')
            self.walls=old
        if day=='lv-entry':
            self.place_opening('sp-lower-entry',None,OpeningKind.DOOR,width_m=1.0,operation=Operation.SLIDING,prefix='d-garden')
        for sw in self.sol.shared_walls:
            pair={sw.room_a,sw.room_b}
            open_pair=pair in [{'sp-living','sp-dining'},{'sp-day-lobby','sp-living'}]
            balcony='sp-balcony' in pair
            width=3 if pair=={'sp-living','sp-dining'} else (1.1 if balcony and day!='lv-entry' else (1.8 if open_pair or balcony else .9))
            self.place_opening(sw.room_a,sw.room_b,OpeningKind.OPENING if open_pair else OpeningKind.DOOR,
                width_m=width,operation=Operation.NONE if open_pair else Operation.SLIDING,prefix='op' if open_pair else 'd')
        for r in self.sol.rooms:
            if r.function in [F.BEDROOM,F.KITCHEN,F.LIVING,F.STUDY,F.FAMILY]:
                self.place_opening(r.space_id,None,OpeningKind.WINDOW,width_m=1.8,height_m=1.4,sill_m=.8,operation=Operation.SLIDING,prefix='win')

parser=argparse.ArgumentParser();parser.add_argument('--option',choices=['a','b'],required=True);parser.add_argument('--time',type=int,default=60)
args=parser.parse_args();folder=ROOT/('codex-c02-'+args.option);folder.mkdir(exist_ok=True)
attempts=[];result=None
for w,h in [(130,104),(136,108),(142,110)]:
    result,info=solve(args.option,w,h,args.time);attempts.append(info)
    (folder/'solver-attempts.json').write_text(json.dumps(attempts,indent=2))
    if result:break
if not result:raise SystemExit('No layout found in tested ranges; see solver-attempts.json')
sol,day,night,bounds=result
builder=Builder(sol,site,frame,Ground(site,frame),program,actor)
model=builder.build_model('codex-c02-'+args.option,'Codex C02-'+args.option.upper(),sref,pref)
model.assumptions=[Assumption(id='c02-basis',statement='Exploratory solver geometry; strict side-boundary alignment. Floor levels use an assumed western TIN reference and 3m intervals, not measured road thresholds. Core/room dimensions are initial design assumptions.',made_by=actor)]
for lv in model.levels:lv.name={'lv-upper':'Road — garage','lv-entry':'Upper residential','lv-lower':'Lower residential'}[lv.id]
plan=PlanVersion(option_id=model.id,label=model.name,strategy='side-boundary-compact-core',model=model,
    provenance=Provenance(created_at=store.clock(),created_by=actor,method='cpsat_explicit_topology',inputs=[sref,pref]),
    generation=GenerationRecord(generator='codex-c02-project-solver',generator_version='1',solver='ortools-cp-sat',solver_version=ortools.__version__,solver_status=sol.status,objective=sol.objective,seed=18,deterministic_time_limit=max(sol.deterministic_time,0.1)))
(folder/'plan.json').write_text(plan.model_dump_json(indent=2)+'\n')
findings=check_model(model,site,program)
(folder/'violations.json').write_text(json.dumps([f.model_dump(mode='json') for f in findings],indent=2)+'\n')
(folder/'placement.json').write_text(json.dumps({'bounds':bounds,'frame':{'origin':frame.origin,'u':frame.u_dir,'v':frame.v_dir},'rooms':[r.__dict__ for r in sol.rooms]},indent=2,default=str))
print('EXPORTED',folder,'findings',len(findings),flush=True)

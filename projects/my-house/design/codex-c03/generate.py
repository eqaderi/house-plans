"""Exploratory C03 room solver. Side-boundary frame ONLY; no road-default call.

Uses explicit room topology, CP-SAT NoOverlap2D, aligned three-level core,
screened service access, then the shared canonical assembler and checks.
"""
import os
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

from house_ai.domain.model import Opening, OpeningKind, Operation, WallKind
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
# Reference origin is 3 m along the long edge and 1.2 m inward.
# Actual tier faces are solver bounds relative to this origin.
origin=(nw[0]+3*east[0]+1.2*south[0],nw[1]+3*east[1]+1.2*south[1])
frame=DesignFrame(origin,east,south,'Owner-required long-side-boundary alignment; u downhill ENE, v toward south',None,None)
z=elevation_at(site.terrain.surface,((nw[0]+sw[0])/2,(nw[1]+sw[1])/2))

def solve(option,width,height,seconds=60):
    day='lv-entry';night='lv-lower';levels=['lv-lower','lv-entry','lv-upper']
    step=30 if option=='a' else 42
    bounds={'lv-upper':(-24 if option=='a' else -12,152),'lv-entry':(20,20+width),'lv-lower':(20+step,20+step+width)}
    vbounds={'lv-upper':(0,120),'lv-entry':(10,height-20),'lv-lower':(-5,height)}
    md=cp_model.CpModel();rooms={};vs={};links=[];objective=[]
    seed=int(os.environ.get('C03_SEED','18'))
    def add(key,name,fn,lv,target,minw,pid=None):
        a,b=bounds[lv];c,d=vbounds[lv]
        if fn==F.STAIR:pairs=[(26,50),(50,26)]
        elif fn==F.LIFT:pairs=[(26,22)]
        elif fn==F.GARAGE:pairs=[(74,66)]
        else:
            pairs=[(w,h) for w in range(minw,b-a+1,2) for h in range(minw,d-c+1,2)
                   if target*.90*100<=w*h<=target*1.18*100 and max(w,h)<=min(w,h)*(1.4 if fn==F.BEDROOM else 2.0)]
        if not pairs:raise ValueError(key)
        x=md.NewIntVar(a,b,key+'x');y=md.NewIntVar(c,d,key+'y')
        w=md.NewIntVar(min(q[0] for q in pairs),max(q[0] for q in pairs),key+'w')
        h=md.NewIntVar(min(q[1] for q in pairs),max(q[1] for q in pairs),key+'h')
        xe=md.NewIntVar(a,b,key+'xe');ye=md.NewIntVar(c,d,key+'ye')
        md.Add(xe==x+w);md.Add(ye==y+h);md.AddAllowedAssignments([w,h],pairs)
        ar=md.NewIntVar(1,30000,key+'area');md.AddMultiplicationEquality(ar,[w,h])
        dev=md.NewIntVar(0,30000,key+'dev');md.AddAbsEquality(dev,ar-round(target*100));objective.append(dev)
        rooms[key]=dict(name=name,fn=fn,lv=lv,pid=pid or 'pi-'+key)
        vs[key]=(x,y,xe,ye,w,h,ar)
    def edge(k,side=None):
        x,y,xe,ye,*_=vs[k];a,b=bounds[rooms[k]['lv']];c,d=vbounds[rooms[k]['lv']]
        eqs={'west':x==a,'east':xe==b,'north':y==c,'south':ye==d}
        if side:md.Add(eqs[side]);return
        fs=[]
        for n,eq in eqs.items():
            f=md.NewBoolVar(k+n);md.Add(eq).OnlyEnforceIf(f);fs.append(f)
        md.AddBoolOr(fs)
    def touch(a,b,span=12):
        xa,ya,ea,na,*_=vs[a];xb,yb,eb,nb,*_=vs[b];flags=[]
        for n,eq,l1,h1,l2,h2 in [('e',ea==xb,ya,na,yb,nb),('w',eb==xa,ya,na,yb,nb),('n',na==yb,xa,ea,xb,eb),('s',nb==ya,xa,ea,xb,eb)]:
            f=md.NewBoolVar(a+b+n);md.Add(eq).OnlyEnforceIf(f);md.Add(h1-l2>=span).OnlyEnforceIf(f);md.Add(h2-l1>=span).OnlyEnforceIf(f);flags.append(f)
        md.AddBoolOr(flags);links.append((a,b))
    for lv in levels:
        add('stair-'+lv,'Shared stair',F.STAIR,lv,13,26,'pi-stair')
        add('lift-'+lv,'Lift reserve',F.LIFT,lv,5.72,22,'pi-lift')
    for kind in ['stair-','lift-']:
        for lv in levels[1:]:
            for i in range(4):md.Add(vs[kind+lv][i]==vs[kind+levels[0]][i])
    edge('stair-lv-lower','west');edge('lift-lv-lower','west')
    add('garage','Two-car garage',F.GARAGE,'lv-upper',46.2,66,'pi-garage');edge('garage','west')
    add('office','Quiet office',F.STUDY,'lv-upper',12,28,'pi-study-1');edge('office')
    add('plant','Plant / utilities',F.MECHANICAL,'lv-upper',5,20,'pi-mechanical')
    add('top-lobby','Lift lobby',F.HALL,'lv-upper',12,26)
    for k in ['garage','office','stair-lv-upper','lift-lv-upper']:touch('top-lobby',k)
    touch('garage','plant')
    for key,name,fn,area,mw,pid in [
        ('dining','Dining',F.DINING,16,32,'pi-dining'),('kitchen','Kitchen / breakfast',F.KITCHEN,23,38,'pi-kitchen'),
        ('pantry','Pantry',F.PANTRY,4,18,'pi-pantry'),('day-bath','Shower / WC',F.BATHROOM,5.5,20,'pi-bath-2'),
        ('bath-vest','Screened service entry',F.HALL,3,14,None),('store','Store',F.STORAGE,4,18,'pi-storage'),
        ('main-entry','Entrance',F.ENTRY,5,20,'pi-entry')]:
        add(key,name,fn,day,area,mw,pid)
    edge('kitchen','south');edge('main-entry','south')
    md.Add(vs['kitchen'][2]>=bounds[night][0]+24);md.Add(vs['main-entry'][0]>=bounds[night][0])
    touch('kitchen','dining',18);touch('kitchen','pantry');touch('bath-vest','day-bath');touch('bath-vest','store');touch('bath-vest','dining');touch('main-entry','dining');touch('lift-lv-entry','dining')
    for key,name,fn,area,mw,pid in [
        ('main-bed','Parents',F.BEDROOM,21,38,'pi-bed-main'),('elder-bed','Grandparents',F.BEDROOM,20,38,'pi-bed-elder-1'),
        ('boys','Boys / two beds',F.BEDROOM,20,38,'pi-bed-child-1'),('girls','Girls / two beds',F.BEDROOM,20,38,'pi-bed-child-2'),
        ('ensuite','En-suite',F.BATHROOM,6.5,24,'pi-bath-ensuite'),('night-bath','Shared bathroom',F.BATHROOM,7,24,'pi-bath-1'),
        ('laundry','Laundry / linen',F.LAUNDRY,7,24,'pi-laundry')]:
        add(key,name,fn,night,area,mw,pid)
        if fn==F.BEDROOM:edge(key)
    touch('main-bed','ensuite')
    edge('main-bed','north');edge('elder-bed','north');edge('boys','south');edge('girls','south')
    # Reserve a proper room-sized contiguous heart; remaining unassigned cells
    # join this one physical open room, rather than becoming unnamed voids.
    add('_day-anchor','Reserved living area',F.LIVING,day,27,38);edge('_day-anchor','east')
    touch('dining','_day-anchor',24)
    add('_night-anchor','Reserved family area',F.FAMILY,night,16,38)
    md.Add(vs['_night-anchor'][1]>=35);md.Add(vs['_night-anchor'][3]<=height-28)
    touch('night-bath','_night-anchor');touch('laundry','_night-anchor')
    for lv in levels:
        ks=[k for k,r in rooms.items() if r['lv']==lv];ix=[];iy=[]
        for k in ks:
            x,y,xe,ye,w,h,_=vs[k];ix.append(md.NewIntervalVar(x,w,xe,k+'ix'));iy.append(md.NewIntervalVar(y,h,ye,k+'iy'))
        md.AddNoOverlap2D(ix,iy)
        # Keep a 1.2 m clear zone along each common-room core face. Open
        # living-area anchors may overlap it; enclosed rooms may not.
        if lv!='lv-upper':
            closed=[k for k in ks if not k.startswith('_')]
            for core in ['stair-'+lv]+(['lift-'+lv] if lv==night else []):
                x,y,xe,ye,w,h,_=vs[core]
                re=md.NewIntVar(bounds[lv][0],bounds[lv][1],core+'clear-end')
                md.Add(re==xe+12)
                ri=md.NewIntervalVar(xe,12,re,core+'clear-x')
                rj=md.NewIntervalVar(y,h,ye,core+'clear-y')
                ci=[md.NewIntervalVar(vs[k][0],vs[k][4],vs[k][2],core+k+'cx') for k in closed]
                cj=[md.NewIntervalVar(vs[k][1],vs[k][5],vs[k][3],core+k+'cy') for k in closed]
                md.AddNoOverlap2D([*ci,ri],[*cj,rj])
    md.Minimize(sum(objective)+sum(vs[k][0] for k in ['day-bath','store','night-bath','laundry']))
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1;solver.parameters.random_seed=seed
    solver.parameters.max_time_in_seconds=seconds
    start=time.monotonic();status=solver.Solve(md)
    info=dict(status=solver.StatusName(status),width_dm=width,height_dm=height,seed=seed,wall_time_s=time.monotonic()-start)
    print(json.dumps(info),flush=True)
    if status not in [cp_model.OPTIMAL,cp_model.FEASIBLE]:return None,info
    placed=[]
    for k,r in rooms.items():
        if k.startswith('_'):continue
        placed.append(PlacedRoom2D('sp-'+k,r['name'],r['fn'],r['lv'],*[solver.Value(q) for q in vs[k][:4]],r['pid'],'z-private' if r['lv']==night else 'z-day'))
    # Orthogonal decomposition of exact residual floor geometry into sub-rects.
    for lv,key,name,fn,pid in [(day,'living','Open living / arrival',F.LIVING,'pi-living'),(night,'night-lobby','Family sitting / reading',F.HALL,None)]:
        a,b=bounds[lv];c,d=vbounds[lv]
        occupied=unary_union([Polygon([(r.u0,r.v0),(r.u1,r.v0),(r.u1,r.v1),(r.u0,r.v1)]) for r in placed if r.level_id==lv])
        residual=__import__('shapely').geometry.box(a,c,b,d).difference(occupied)
        if residual.geom_type!='Polygon':
            pieces=sorted([g for g in residual.geoms if g.geom_type=='Polygon'],key=lambda g:-g.area)
            residual=pieces[0]
            # Deterministic region growth: solver-created peripheral pockets enlarge
            # the adjacent room instead of becoming unnamed external recesses.
            for pocket in pieces[1:]:
                candidates=[]
                for rr in placed:
                    if rr.level_id!=lv or rr.function in [F.STAIR,F.LIFT]:continue
                    gg=unary_union([__import__('shapely').geometry.box(*q) for q in (rr.sub_rects or [(rr.u0,rr.v0,rr.u1,rr.v1)])])
                    shared_length=gg.boundary.intersection(pocket.boundary).length
                    if shared_length>1:candidates.append((shared_length,rr,gg))
                if not candidates:info['rejected']='unassignable disconnected pocket';return None,info
                _,rr,gg=max(candidates,key=lambda q:q[0]);joined=gg.union(pocket)
                if joined.geom_type!='Polygon':info['rejected']='room extension disconnected';return None,info
                xx=sorted({q[0] for q in joined.exterior.coords});yy=sorted({q[1] for q in joined.exterior.coords})
                rr.sub_rects=[(int(x0),int(y0),int(x1),int(y1)) for x0,x1 in zip(xx,xx[1:]) for y0,y1 in zip(yy,yy[1:]) if joined.covers(__import__('shapely').geometry.box(x0,y0,x1,y1))]
                rr.u0,rr.v0,rr.u1,rr.v1=map(int,joined.bounds)

        xs=sorted({a,b,*[q[0] for q in residual.exterior.coords],*[q[0] for ring in residual.interiors for q in ring.coords]})
        ys=sorted({c,d,*[q[1] for q in residual.exterior.coords],*[q[1] for ring in residual.interiors for q in ring.coords]})
        sub=[]
        from shapely.geometry import box
        for x0,x1 in zip(xs,xs[1:]):
            for y0,y1 in zip(ys,ys[1:]):
                cell=box(x0,y0,x1,y1)
                if residual.covers(cell):sub.append((int(x0),int(y0),int(x1),int(y1)))
        placed.append(PlacedRoom2D('sp-'+key,name,fn,lv,a,c,b,d,pid,'z-private' if lv==night else 'z-day',sub_rects=sub))
        # Each occupied room needs a usable interface to the shared heart unless
        # deliberately reached through a pantry, bathroom vestibule or en-suite.
        indirect={'kitchen','pantry','day-bath','store','bath-vest','main-entry','ensuite'}
        for r in placed:
            if r.level_id==lv and r.space_id!='sp-'+key and r.space_id[3:] not in indirect and not (lv==day and r.function==F.LIFT):
                g=unary_union([box(*q) for q in (r.sub_rects or [(r.u0,r.v0,r.u1,r.v1)])])
                shared=g.boundary.intersection(residual.boundary)
                lines=[q for q in getattr(shared,'geoms',[shared]) if q.geom_type=='LineString']
                if not lines or max(q.length for q in lines)<12:
                    info['rejected']='no usable shared-heart access: '+r.space_id;return None,info
                links.append((r.space_id[3:],key))
    by={r.space_id[3:]:r for r in placed};shared=[]
    def parts(r):return r.sub_rects or [(r.u0,r.v0,r.u1,r.v1)]
    from shapely.geometry import box
    for ka,kb in links:
        if ka.startswith('_') or kb.startswith('_'):continue
        ra,rb=by[ka],by[kb]
        ga=unary_union([box(*q) for q in parts(ra)]);gb=unary_union([box(*q) for q in parts(rb)])
        inter=ga.boundary.intersection(gb.boundary)
        lines=[q for q in getattr(inter,'geoms',[inter]) if q.geom_type=='LineString' and q.length>=12]
        if not lines:info['rejected']='missing interface '+ka+' / '+kb;return None,info
        seg=max(lines,key=lambda q:q.length);x0,y0,x1,y1=seg.bounds
        shared.append(SharedWall(ra.space_id,rb.space_id,ra.level_id,'v' if x0==x1 else 'h',int(x0 if x0==x1 else y0),int(y0 if x0==x1 else x0),int(y1 if x0==x1 else x1),True))
    a,b=bounds[day];la,lb=bounds[night];c,d=vbounds[day];lc,ld=vbounds[night]
    terraces=[PlacedRoom2D('sp-terrace-east','East roof terrace',F.TERRACE,day,b,lc,lb,ld,'pi-balcony','z-outdoor'),
              PlacedRoom2D('sp-terrace-south','South kitchen terrace',F.TERRACE,day,la,d,b,ld,None,'z-outdoor'),
              PlacedRoom2D('sp-terrace-north','North terrace walk',F.TERRACE,day,la,lc,b,c,None,'z-outdoor')]
    for tr in terraces:
        gt=box(tr.u0,tr.v0,tr.u1,tr.v1)
        for r in placed:
            if r.level_id!=day or r.function not in [F.LIVING,F.KITCHEN,F.DINING,F.ENTRY,F.TERRACE]:continue
            inter=unary_union([box(*q) for q in parts(r)]).boundary.intersection(gt.boundary)
            ls=[q for q in getattr(inter,'geoms',[inter]) if q.geom_type=='LineString' and q.length>=12]
            if ls:
                q=max(ls,key=lambda q:q.length);x0,y0,x1,y1=q.bounds
                shared.append(SharedWall(r.space_id,tr.space_id,day,'v' if x0==x1 else 'h',int(x0 if x0==x1 else y0),int(y0 if x0==x1 else x0),int(y1 if x0==x1 else x1),True))
        placed.append(tr)
    assert any({w.room_a,w.room_b}=={'sp-kitchen','sp-terrace-south'} for w in shared)
    sol=Solution2D(status=solver.StatusName(status),objective=solver.ObjectiveValue(),rooms=placed,shared_walls=shared,circulation_rooms=[],levels=levels,deterministic_time=solver.deterministic_time,wall_time_s=info['wall_time_s'],seed=seed,platform_info='local',strategy='corridor_free',circulation_share=0,has_stairs=True,exterior_connections=['sp-garage','sp-main-entry','sp-night-lobby'],level_elevations_m={'lv-upper':z,'lv-entry':z-3,'lv-lower':z-6})
    return (sol,day,night,bounds),info

class Builder(Builder2D):
    def wall_model(self, seg):
        wall=super().wall_model(seg)
        if seg.neg and seg.pos and all(sid.startswith('sp-terrace-') for sid in [seg.neg,seg.pos]):
            wall.kind=WallKind.PARAPET;wall.height_m=1.0
        return wall
    def build_openings(self):
        # Explicit door graph, with exterior edges selected by architectural role.
        entry='sp-main-entry'
        for sid,edge,width in [('sp-garage','west',5.5),('sp-terrace-south','south',1.1),('sp-plant','west',.9)]:
            segs=self._walls_between(sid,None)
            # The assembler chooses by available span; constrain candidates temporarily
            # to the intended facade without moving any solved geometry.
            target=[w for w in segs if (w.orient=='v' if edge in ['west','east'] else w.orient=='h')]
            if target:
                c=(min if edge in ['west','north'] else max)(w.c for w in target)
                target=[w for w in target if w.c==c]
            old=self.walls
            self.walls=[w for w in old if w not in segs or w in target]
            self.place_opening(sid,None,OpeningKind.OPENING if 'terrace' in sid else OpeningKind.DOOR,width_m=width,height_m=1.0 if 'terrace' in sid else 2.1,operation=Operation.NONE if 'terrace' in sid else Operation.SLIDING,prefix='d-exterior')
            self.walls=old
        if day=='lv-entry':
            self.place_opening('sp-night-lobby',None,OpeningKind.DOOR,width_m=1.0,operation=Operation.SLIDING,prefix='d-garden')
        for sw in self.sol.shared_walls:
            pair={sw.room_a,sw.room_b}
            if pair=={'sp-garage','sp-plant'}:continue
            open_pair=pair=={'sp-living','sp-dining'}
            if all(sid.startswith('sp-terrace-') for sid in pair):
                seg=max(self._walls_between(sw.room_a,sw.room_b),key=lambda w:w.length_dm)
                self.openings.append(Opening(id='op-terrace-'+str(len(self.openings)),host_wall_id=seg.id,kind=OpeningKind.OPENING,offset_m=0,width_m=seg.length_m,height_m=1.0,connects=(sw.room_a,sw.room_b),operation=Operation.NONE))
                seg.used.append((0,seg.length_dm));continue
            balcony=any('sp-terrace-' in sid for sid in pair)
            width=4 if pair=={'sp-living','sp-dining'} else (1.1 if balcony and day!='lv-entry' else (1.8 if open_pair or balcony else .9))
            self.place_opening(sw.room_a,sw.room_b,OpeningKind.OPENING if open_pair else OpeningKind.DOOR,
                width_m=width,operation=Operation.NONE if open_pair else Operation.SLIDING,material='m-window' if balcony else None,prefix='op' if open_pair else 'd')
        for r in self.sol.rooms:
            if r.function in [F.BEDROOM,F.KITCHEN,F.LIVING,F.STUDY,F.FAMILY]:
                self.place_opening(r.space_id,None,OpeningKind.WINDOW,width_m=1.8,height_m=1.4,sill_m=.8,operation=Operation.SLIDING,prefix='win')

parser=argparse.ArgumentParser();parser.add_argument('--option',choices=['a','b'],required=True);parser.add_argument('--time',type=int,default=60)
args=parser.parse_args();folder=ROOT/('codex-c03-'+args.option);folder.mkdir(exist_ok=True)
attempts=[];result=None
for trial in range(12):
    w,h=(138 if args.option=='a' else 146),124
    os.environ['C03_SEED']=str(18+trial)
    result,info=solve(args.option,w,h,args.time);attempts.append(info)
    (folder/'solver-attempts.json').write_text(json.dumps(attempts,indent=2))
    if result:break
if not result:raise SystemExit('No layout found in tested ranges; see solver-attempts.json')
sol,day,night,bounds=result
builder=Builder(sol,site,frame,Ground(site,frame),program,actor)
model=builder.build_model('codex-c03-'+args.option,'Codex C03-'+args.option.upper(),sref,pref)
model.assumptions=[Assumption(id='c03-basis',statement='Exploratory solver geometry; strict side-boundary alignment. Floor levels use an assumed western TIN reference and 3m intervals, not measured road thresholds. Core/room dimensions are initial design assumptions.',made_by=actor)]
for lv in model.levels:lv.name={'lv-upper':'Road — garage','lv-entry':'Upper residential','lv-lower':'Lower residential'}[lv.id]
plan=PlanVersion(option_id=model.id,label=model.name,strategy='stepped-roof-terraces-no-voids',model=model,
    provenance=Provenance(created_at=store.clock(),created_by=actor,method='cpsat_with_deterministic_orthogonal_partition',inputs=[sref,pref]),
    generation=GenerationRecord(generator='codex-c03-project-solver',generator_version='1',solver='ortools-cp-sat',solver_version=ortools.__version__,solver_status=sol.status,objective=sol.objective,seed=18,deterministic_time_limit=max(sol.deterministic_time,0.1)))
(folder/'plan.json').write_text(plan.model_dump_json(indent=2)+'\n')
findings=check_model(model,site,program)
(folder/'violations.json').write_text(json.dumps([f.model_dump(mode='json') for f in findings],indent=2)+'\n')
(folder/'placement.json').write_text(json.dumps({'bounds':bounds,'frame':{'origin':frame.origin,'u':frame.u_dir,'v':frame.v_dir},'rooms':[r.__dict__ for r in sol.rooms]},indent=2,default=str))
print('EXPORTED',folder,'findings',len(findings),flush=True)

"""Read-only independent review of frozen 0109-R5; no house authoring."""
import csv, hashlib, html, json, math, platform, re, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch, FancyBboxPatch
import numpy as np
from shapely.geometry import shape, Polygon, Point, LineString
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from verified_site import verified_site, terrain_mesh
from site_boundary_gate import inspect_works
OUT=Path(__file__).parent
if (OUT/'verification.json').exists():
    raise SystemExit('Finalized review: use a new versioned directory, never overwrite this issue.')
BASE=ROOT/'outputs/redesign-0109-r5'
J=json.loads((BASE/'geometry.json').read_text())
P=next(x for x in J['proposals'] if x['code']=='B')
S=verified_site()
INK='#203b43'; RED='#b23c32'; BLUE='#226c9d'; GOLD='#b47c20'; GREEN='#387860'
COL={'sleep':'#dce7ef','wet':'#d9eeee','living':'#f6e9cd','service':'#e7e7df','circulation':'#f4f4ed','work':'#e9e0ed'}
FIGURES=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def geom(ax,g,fc='none',ec=INK,lw=1,alpha=1,hatch=None,z=1):
    if isinstance(g,dict):g=shape(g)
    for q in getattr(g,'geoms',[g]):
        if q.is_empty:continue
        if q.geom_type=='Polygon':
            ax.add_patch(Patch(np.array(q.exterior.coords),facecolor=fc,edgecolor=ec,lw=lw,alpha=alpha,hatch=hatch,zorder=z))
            for ring in q.interiors:ax.add_patch(Patch(np.array(ring.coords),facecolor='white',edgecolor=ec,lw=.5,zorder=z+.1))
        elif q.geom_type in ('LineString','LinearRing'):ax.plot(*q.xy,color=ec,lw=lw,alpha=alpha,zorder=z)
def xy(v):
    p=S.to_project(Point(*v));return p.x,p.y
def sheet(title,subtitle,notes):
    fig=plt.figure(figsize=(16,10),facecolor='#fffefa')
    ax=fig.add_axes([.035,.10,.67,.76]);ax.set_aspect('equal');ax.axis('off')
    fig.text(.035,.94,title,fontsize=21,weight='bold',color=INK)
    fig.text(.035,.903,subtitle,fontsize=10,color='#596c73')
    y=.84
    import textwrap
    for head,body in notes:
        fig.text(.735,y,head,fontsize=11,weight='bold',color=RED if head.startswith('C') else INK)
        lines=textwrap.wrap(body,43)
        fig.text(.735,y-.027,'\n'.join(lines),fontsize=10,linespacing=1.45,color=INK,va='top')
        y-=.055+len(lines)*.021
    fig.text(.035,.035,'0110-R1 | 17 OCT 2026 | REVIEW MARKS ONLY | 0109-R5 GEOMETRY UNCHANGED | NO APPROVAL',fontsize=9,color=INK)
    return fig,ax
def save(fig,name):
    for ext in ['svg','png']:fig.savefig(OUT/(name+'.'+ext),dpi=130,facecolor=fig.get_facecolor())
    plt.close(fig);FIGURES.append(name)
def finish_plan(ax,gs,north_x=.95):
    allg=unary_union(gs);a,b,c,d=allg.bounds;pad=1.3
    ax.set_xlim(a-pad,c+pad);ax.set_ylim(b-pad,d+pad)
    ax.annotate('N*',xy=(north_x,.94),xytext=(north_x,.80),xycoords='axes fraction',textcoords='axes fraction',ha='center',arrowprops={'arrowstyle':'->','color':INK},fontsize=11)
    ax.text(.02,.01,'*Inherited project north; absolute control unresolved',transform=ax.transAxes,fontsize=8,color=INK)
def tag(ax,at,label,color=RED):
    ax.text(*xy(at),label,color=color,fontsize=10,weight='bold',ha='center',va='center',bbox={'boxstyle':'round,pad=.25','fc':'white','ec':color,'alpha':.96},zorder=20)
def route(ax,points,color=BLUE,ls='-',arrow=True):
    arr=np.array([xy(p) for p in points]);ax.plot(arr[:,0],arr[:,1],ls=ls,color=color,lw=2,zorder=10)
    if arrow and len(arr)>1:ax.annotate('',xy=arr[-1],xytext=arr[-2],arrowprops={'arrowstyle':'->','color':color,'lw':2},zorder=11)
def plan(ax,level):
    f=P['floors'][level];fg=S.to_project(shape(f['footprint']));geom(ax,fg,'#f7f7f1')
    for q in f['rooms']+f['zones']:
        g=S.to_project(shape(q['g']));geom(ax,g,COL.get(q['kind'],'#eee'),lw=.7)
        c=g.representative_point();name=q['id'].replace('SCREENED MULTIUSE LOBBY','WET LOBBY').replace('DINING 6 / EXTENDS TO 8','DINING 6 (+2?)').replace('EAST FAMILY LIVING','MAIN LIVING')
        ax.text(c.x,c.y,name,fontsize=6.8,ha='center',va='center',zorder=3)
    for q in f['furniture']:geom(ax,S.to_project(shape(q['g'])),'#cfd8da',lw=.35,alpha=.7,z=4)
    for w in f['windows']:geom(ax,S.to_project(shape(w['line'])),ec=BLUE,lw=2,z=5)
    for d in f['doors']:geom(ax,S.to_project(shape(d['cut'])),'white','white',lw=0,z=6)
    for key in ['west','east','turn','void']:
        geom(ax,S.to_project(shape(f['stair'][key])),'#e3e5e1',lw=.6,z=5)
    geom(ax,S.to_project(shape(f['lift']['envelope'])),'#e0d5e8',lw=.7,z=5)
    footprint=shape(f['footprint'])
    shell=footprint.difference(footprint.buffer(-.30,join_style=2))
    rings=[shape(q['g']).buffer(.10,join_style=2).difference(shape(q['g'])) for q in f['rooms']]
    core=shape(f['stair']['envelope']);core=core.buffer(.10,join_style=2).difference(core)
    lift=shape(f['lift']['envelope']).difference(shape(f['lift']['cabin']))
    wall=unary_union([shell,core,lift,*rings,*[shape(q) for q in f['partitions']]])
    for d in f['doors']:wall=wall.difference(shape(d['cut']))
    for w in f['windows']:wall=wall.difference(shape(w['line']).buffer(.33,cap_style=2))
    geom(ax,S.to_project(wall),INK,INK,lw=.2,z=7)
    c=S.to_project(shape(f['lift']['envelope'])).centroid;ax.text(c.x,c.y,'LIFT',ha='center',fontsize=8,zorder=6)
    finish_plan(ax,[fg]);return f

# Independent evidence: exact polygon intersections, original route results, TIN only.
r=P['floors']['road'];cab=next(q for q in r['furniture'] if q['id']=='Six helmets / sports / bins')
conflicts=[]
for d in P['vehicle']['door_envelopes']:
    a=shape(cab['g']).intersection(shape(d['g'])).area
    if a>0:conflicts.append({'storage':cab['id'],'door':d['id'],'overlap_m2':a})
M=terrain_mesh(S)
ret=[]
for key,g0 in P['works'].items():
    if 'retaining' not in key and key not in ['main-soil-garden','upper-arrival-garden-earthworks','lower-enclosure']:continue
    g=shape(g0);values=[];unknown=0
    for tri in M['triangles']:
        q=g.intersection(Polygon([M['vertices'][i][:2] for i in tri]))
        for part in getattr(q,'geoms',[q]):
            if part.is_empty:continue
            pts=list(part.exterior.coords) if part.geom_type=='Polygon' else list(part.coords) if hasattr(part,'coords') else []
            for x,y in pts:
                z=S.terrain(x,y)
                if z is None:unknown+=1
                else:values.append(z)
    ret.append({'id':key,'ground_min_m':min(values) if values else None,'ground_max_m':max(values) if values else None,'unsupported_evaluation_points':unknown,'plan_area_m2':g.area,'scope':'TIN-intersection vertices only; wall/footing levels and engineering heights unknown'})
over=[]
for lower,upper in [('upper','road'),('lower','upper')]:
    for a in P['floors'][lower]['rooms']+P['floors'][lower]['zones']:
        if a['kind']!='sleep' and a['id']!='GARDEN LOUNGE':continue
        for b in P['floors'][upper]['rooms']+P['floors'][upper]['zones']:
            area=shape(a['g']).intersection(shape(b['g'])).area
            if area>.01:over.append({'below_floor':lower,'below_room':a['id'],'above_room':b['id'],'overlap_m2':area})
routes=[{'floor':lev,'id':q['id'],'length_m':q['result']['length_m'],'disc_m':q['diameter'],'passed':q['result']['passed']} for lev,f in P['floors'].items() for q in f['routes']]
court=shape(P['works']['north-wet-court']);cover=court.intersection(shape(P['floors']['upper']['footprint'])).area
gates={q['code']:inspect_works({k:S.to_project(shape(v)) for k,v in q['works'].items()},q['necessary_access_crossings']) for q in J['proposals']}
E={'review':'0110-R1','reviewed_candidate':'0109-R5 / B in depth; A/C comparison','geometry_sha256':sha(BASE/'geometry.json'),'frame':J['frame'],'source_evidence':J['source_evidence'],'door_storage_conflicts':conflicts,'routes':routes,'retaining_and_platforms':ret,'acoustic_floor_overlaps':over,'north_wet_court':{'area_m2':court.area,'under_upper_footprint_m2':cover,'scope':'Plan projection only; no sky/daylight calculation'},'strict_existing_supplied_gates':gates,'missing_groups_each':15,'new_works':False,'approval':'not_approved','scope':'Architectural critique. No new layout, engineering sizing, model promotion or regulatory determination.','metadata_conflict':{'works_z_road_enclosure':P['works_z']['road-enclosure'],'road_floor_z':r['z'],'disposition':'Do not use works_z as a coordinated elevation schedule.'},'runtime':{'python':platform.python_version(),'matplotlib':matplotlib.__version__},'producer_sha256':sha(__file__)}
(OUT/'evidence.json').write_text(json.dumps(E,indent=2)+'\n')
for name,rows in [('retaining-evidence',ret),('route-evidence',routes),('acoustic-overlaps',over)]:
    with (OUT/(name+'.csv')).open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

fig,ax=sheet('01 / Road floor: conflicts and safety boundaries','Proposed FFL 1677.50 m; road tie, fire products and real vehicle variants unresolved',[
 ('I09 • MAJOR / HIGH','Second-car north door space intersects the sports/bin cabinet by 0.5075 m². The 0.30 m parked gap is not the proposed 0.65 m door space.'),
 ('I07 / I08 • CRITICAL / LOW','Garage separation, CO strategy and lift evacuation need a coordinated fire design. Open placeholder core passages are not protected exits.'),
 ('I20 / I22 • MAJOR','Six-bike fit, bin collection route, plant replacement and electrical/EV access remain product and operation dependent.')])
plan(ax,'road')
for d in P['vehicle']['door_envelopes']:geom(ax,S.to_project(shape(d['g'])),'#ffb67c',RED,.6,alpha=.6,z=7)
hit=shape(cab['g']).intersection(shape(P['vehicle']['door_envelopes'][2]['g']));geom(ax,S.to_project(hit),'#d84b3d',RED,z=9)
tag(ax,(-.5,2.55),'I09');tag(ax,(5.25,-2.3),'I07');tag(ax,(4.1,.2),'I08');tag(ax,(7.,-4.5),'I20')
save(fig,'01-road-annotated')

fig,ax=sheet('02 / Upper floor: daily life and vulnerable interfaces','Proposed FFL 1673.60 m; annotations use the frozen plan polygons',[
 ('I11 • MODERATE / HIGH','Stored 0.60 m walking-disc route from wudu to prayer is 18.55 m. The proposed screen creates a long return through family circulation.'),
 ('I15 / I30 • MAJOR / MEDIUM','Garage/unloading partly over parents; public south terrace also passes their glazing. Test noise and night privacy.'),
 ('I14 / I26 • MAJOR','Six dining chairs are drawn. Eight occupied chairs, dishwasher operation, waste sorting and simultaneous cooking need a furnished check.'),
 ('P1 / P3 • POSITIVE / HIGH','Preserve parents on living level and screened open-door WC approaches. Fix convenience without removing privacy.')])
f=plan(ax,'upper');rr=next(q for q in f['routes'] if q['id']=='Same-floor wudu to prayer');route(ax,rr['result']['path'],GOLD)
tag(ax,(11.,.1),'I11');tag(ax,(15.5,-6.8),'I14');tag(ax,(2.5,-6.5),'I15 / I30');tag(ax,(11.0,-6.1),'I26')
save(fig,'02-upper-annotated')

fig,ax=sheet('03 / Lower floor: guest, laundry and escape','Proposed FFL 1670.00 m; external links are review evidence, not certified escape',[
 ('I06 • CRITICAL / LOW','South escape link is about 0.70 m in its own polygon; adjacent grade zone is 0.80 m. Actual clear route, guards, drains and rescue use unverified.'),
 ('I10 • MAJOR / HIGH','Lower guests have only a shared squat WC. Stored guest-to-lift path is 19.45 m, then one level to the private parents ensuite.'),
 ('I12 / I15 • MAJOR','No defined hanging/sorting system; kitchen/ensuite/dining overlap children below. Open stair passages connect noise between levels.'),
 ('P2 • POSITIVE / HIGH','Four separate desks/wardrobes and direct same-level garden lounge deserve preservation.')])
f=plan(ax,'lower');rr=next(q for q in f['routes'] if q['id']=='Guest to lift');route(ax,rr['result']['path'],BLUE)
geom(ax,S.to_project(shape(P['works']['south-lower-escape-link'])),'#f4c5bc',RED,z=3)
tag(ax,(13.,-12.6),'I06');tag(ax,(16.5,-9.7),'I10');tag(ax,(6.9,-4.4),'I12');tag(ax,(11.8,0),'I16')
save(fig,'03-lower-annotated')

def site_plan(ax):
    geom(ax,S.field,'#faf8ef',RED,1.5)
    for level,col in [('lower','#d4e0ea'),('upper','#eadfca'),('road','#c0cbd1')]:geom(ax,S.to_project(shape(P['floors'][level]['footprint'])),col,alpha=.55)
    for k in ['main-soil-garden','upper-arrival-garden-earthworks']:geom(ax,S.to_project(shape(P['works'][k])),'#cbdcbb',GREEN,lw=.9)
    for k in ['east-terrace','south-terrace']:geom(ax,S.to_project(shape(P['works'][k])),'#efe5ce',GOLD,.6,alpha=.5)
    for k,g in P['works'].items():
        if 'retaining' in k:geom(ax,S.to_project(shape(g)),RED,RED,alpha=.6)
    finish_plan(ax,[S.field],north_x=.10)
fig,ax=sheet('04 / Water-risk plan: every collector stops at an unknown','Arrows identify risks and required trace directions; no drain route/outfall is adopted',[
 ('I03 • CRITICAL / LOW','W1 uphill/road runoff; W2 roofs; W3 terraces; W4 retained gardens; W5 courts/groundwater. Every receiving invert and legal outfall is unresolved.'),
 ('I04 • CRITICAL / LOW','Primary collection alone is insufficient. Each basin needs an independent safe overflow below vulnerable threshold/structural flood levels.'),
 ('I02 • CRITICAL / LOW','Flat lower garden: 219.29 m³ geometric fill prism. Natural ground below east wall is roughly 3.82–4.59 m below garden target, before footings.'),
 ('NO DISCHARGE ARROW','No arrow crosses the parcel to suggest an authorized outlet. Surface, roof, groundwater and foul systems require separate verification.')])
site_plan(ax)
for k in ['separate-roof-water-collector','garden-water-collector','upper-bulk-water-collector','south-daylight-drain']:geom(ax,S.to_project(shape(P['works'][k])),BLUE,BLUE,1.5,z=5)
route(ax,[(-4.,-7.),(-2.,-7.)],BLUE,ls='--');tag(ax,(-4.,-7.),'W1')
tag(ax,(10.,-5.),'W2');tag(ax,(17.,-10.5),'W3');tag(ax,(24.,0.),'W4');tag(ax,(11.,3.6),'W5')
tag(ax,(20.,-6.),'OUTFALL ?',RED)
save(fig,'04-water-risk-plan')

fig,ax=sheet('05 / Water-risk section: held at unresolved interfaces','Actual W–E trace y = −5.20 m in the explicit 0093 building frame; equal horizontal/vertical scale',[
 ('I01 / I02','Brown: unchanged TIN interpolation. Green: proposed retained garden. Neither soil strata nor foundations are invented.'),
 ('I03 / I04','Red points: uphill wall/slab, terrace threshold, terrace above occupied lower floor, garden retention. Trace rain/air/vapour/thermal continuity here.'),
 ('OVERFLOW / GROUNDWATER','No gravity outlet or groundwater elevation is known. Pump dependency, backup and safe exceedance require a design before detailed documents.'),
 ('BUILDABILITY','Positive-side membrane inspection must precede protection/backfill. All shoring, footing and working-space footprints remain unknown.')])
ax.set_position([.075,.10,.63,.76]);ax.axis('on');xx=np.linspace(-8,29,500);zz=[S.terrain(float(x),-5.2) for x in xx]
valid=np.array([np.nan if z is None else z for z in zz]);ax.plot(xx,valid,'--',color=GOLD,lw=2,label='Stored TIN natural ground')
ax.fill_between(xx,1663,valid,color='#e9deca',alpha=.45)
for level in ['lower','upper','road']:
    f=P['floors'][level];g=shape(f['footprint']).intersection(LineString([(-50,-5.2),(50,-5.2)]))
    for q in getattr(g,'geoms',[g]):
        if q.is_empty:continue
        a,b=q.bounds[0],q.bounds[2];ax.plot([a,b],[f['z']]*2,color=INK,lw=6);ax.text((a+b)/2,f['z']+.25,level.upper(),ha='center',fontsize=9)
for k in ['main-soil-garden','east-terrace']:
    g=shape(P['works'][k]).intersection(LineString([(-50,-5.2),(50,-5.2)]))
    if not g.is_empty:
        a,b=g.bounds[0],g.bounds[2];z=1670 if k=='main-soil-garden' else 1673.6
        ax.plot([a,b],[z,z],color=GREEN,lw=4)
        if k=='main-soil-garden':
            tx=np.linspace(a,b,70);tz=np.array([S.terrain(float(x),-5.2) for x in tx]);ax.fill_between(tx,tz,z,color='#bcd2a2',alpha=.6)
for x,z,t in [(0,1673.6,'retained wall'),(17.8,1673.6,'threshold / terrace'),(19.2,1670,'lower wall / floor'),(23.9,1670,'garden edge')]:
    ax.plot(x,z,'o',color=RED);ax.annotate(t,(x,z),(x-2,z+1.2),fontsize=8,color=RED,arrowprops={'arrowstyle':'->','color':RED})
ax.set_xlim(-8,29);ax.set_ylim(1664,1681);ax.set_xlabel('Building east–west station / m');ax.set_ylabel('Supplied survey Z / m; datum uncertified');ax.grid(alpha=.15)
save(fig,'05-water-risk-section')

def network(title,subtitle,rows,links,notes,name):
    fig,ax=sheet(title,subtitle,notes);ax.set_aspect('auto');ax.set_xlim(0,10);ax.set_ylim(0,10)
    loc={}
    for y,nodes in rows:
        for x,key,text,color in nodes:
            loc[key]=(x,y);ax.add_patch(FancyBboxPatch((x-1.1,y-.55),2.2,1.1,boxstyle='round,pad=.12',fc=color,ec=INK,lw=.8,zorder=3));ax.text(x,y,text,ha='center',va='center',fontsize=9,zorder=4)
    for a,b,text,col,dash in links:
        x,y=loc[a];X,Y=loc[b];dx,dy=X-x,Y-y
        t=min(1.23/abs(dx) if dx else 100,.68/abs(dy) if dy else 100)
        ax.annotate('',(X-t*dx,Y-t*dy),(x+t*dx,y+t*dy),arrowprops={'arrowstyle':'->','color':col,'lw':2,'ls':dash,'shrinkA':1,'shrinkB':1},zorder=5)
        ax.text((x+X)/2,(y+Y)/2+.19,text,fontsize=7.6,color=col,ha='center',bbox={'fc':'white','ec':'none','alpha':.92},zorder=6)
    save(fig,name)
network('06 / Family-flow diagram','A stated weekday scenario; flight counts are one-way traversals, not a behavioural forecast',[
 (8.5,[(1.5,'car','ROAD\nCars / coats / bags','#dce7ef'),(5,'roadlift','Lift / 2-flight stair\nRoad ↔ upper','#e0d5e8'),(8.5,'office','Office / plant\nRoad tier','#e9e0ed')]),
 (5,[(1.5,'pantry','UPPER\nPantry / parents','#dce7ef'),(5,'kitchen','Kitchen / breakfast\nMain living','#f6e9cd'),(8.5,'prayer','Wudu → prayer\n18.55 m stored route','#f6e9cd')]),
 (1.5,[(1.5,'children','LOWER\n4 children / guest','#dce7ef'),(5,'laundry','Laundry / shared WC\nLower lounge','#d9eeee'),(8.5,'garden','Same-level soil garden\nNot road-level exit','#cbdcbb')])],
 [('car','roadlift','queue / unloading',BLUE,'-'),('roadlift','pantry','lift or 2 flights',BLUE,'-'),('pantry','kitchen','separate pantry leg',GOLD,'-'),('children','kitchen','2 flights each way',RED,'-'),('children','laundry','same level',BLUE,'-'),('laundry','garden','level-door intent',GREEN,'-'),('pantry','laundry','parents laundry: 2 flights',GOLD,'--'),('kitchen','prayer','shared sound / circulation',GOLD,'--')],
 [('I13 • MORNING','Four lower children: up for breakfast, down for bags/teeth, then up through living to road = 10 flights per child; 40 child-flight traversals. Bringing bags up initially reduces this to 24.'),('I12 • LAUNDRY','Children stay on lower level. Parents dirty laundry goes down one level; clean returns up. Hanging/sorting and leak containment unproven.'),('I11 • PRAYER','18.55 m is a stored bounded walking check. Real route and screen adjustment need plan revision; privacy must survive.')],'06-family-flow')
network('07 / Accessibility diagram','Step-free spatial intent is not proven independent use; no ADA applicability claimed',[
 (8.5,[(1.6,'park','PARK / ENTER\nTransfer + road tie ?','#f6e9cd'),(5,'lift','ESSENTIAL LIFT\nPower / rescue ?','#f4c5bc'),(8.4,'road','ROAD EXIT\nNo level residential suite','#e4e5e4')]),
 (5,[(1.6,'parents','UPPER: sleep + seated WC\nPrivate parents suite','#dce7ef'),(5,'daily','Cook / eat / living\nUsable controls ?','#f6e9cd'),(8.4,'terrace','Upper terrace\nThreshold/falls ?','#cbdcbb')]),
 (1.5,[(1.6,'guest','LOWER guest\nNo seated shared WC','#f4c5bc'),(5,'lower','Lower lounge / garden\nDoor/route validation ?','#cbdcbb'),(8.4,'escape','PUBLIC WAY\nStairs / assisted exit ?','#f4c5bc')])],
 [('park','lift','unproven transfer',RED,'--'),('lift','daily','normal lift service only',GOLD,'--'),('parents','daily','same floor',GREEN,'-'),('daily','terrace','same floor intent',GREEN,'--'),('guest','lift','19.45 m + level change',RED,'--'),('guest','lower','same floor intent',GREEN,'--'),('lower','escape','not step-free proven',RED,'--'),('lift','road','power-failure gap',RED,'--')],
 [('I08 • CRITICAL / LOW','Normal lift service cannot establish emergency escape. Select real lift, pit/overrun, rescue and independent assisted-evacuation strategy.'),('I10 • MAJOR / HIGH','Both shared WCs are squat. Guest/recovering child must use private parents ensuite upstairs; no independent seated guest provision.'),('P1 • POSITIVE / HIGH','Parents can potentially sleep, bathe, eat, live and reach a terrace on one residential floor. Controls, transfers and thresholds remain to prove.')],'07-accessibility')

fig,ax=sheet('08 / Fire and emergency access: gaps, not certified routes','Dashed paths are candidate review links; no fire-appliance template, turnaround or rescue certification',[
 ('I05 • CRITICAL / LOW','West public-road context is not surveyed fire access. Width, gradients, load, overhead clearance, turning, stopping and water supply unknown.'),
 ('I06 / I08 • CRITICAL','Guest east door reaches garden, not a proven public-way discharge. Children need tested rescue openings/courts and safe onward escape, including assisted use.'),
 ('I07 / I24 • CRITICAL','Garage separation/CO, open stair connections, smoke/CO alarms, egress hardware, guards and fall safety need actual products and applicable code.'),
 ('WILDFIRE CONDITIONAL','Hazard status unresolved. If relevant assess roof/eaves/gutters/vents, glazing, decks/underfloor and planting. Never create locked/power-only escape traps.')])
site_plan(ax)
for k in ['south-lower-escape-link','garden-stair','retained-site-external_stair','retained-site-pedestrian_crossing']:geom(ax,S.to_project(shape(P['works'][k])),'#f4c5bc',RED,.8,alpha=.8,z=5)
route(ax,[(19.1,-9.4),(19.7,-9.4),(19.7,-12.5),(4.,-12.5)],RED,'--');tag(ax,(13.,-12.6),'I06')
tag(ax,(4.,.2),'I08');tag(ax,(-2.,-1.5),'ROAD / FIRE ?');tag(ax,(22.,-5.),'NO CERTIFIED EXIT')
save(fig,'08-fire-emergency')

fig,ax=sheet('09 / Daylight, overheating and privacy risk map','Working east is ENE; south is SSE under the inherited north frame. Solar times/weather unknown',[
 ('I16 • MAJOR / MEDIUM','Lower wet court is partly beneath the upper floor: its polygon overlap is recorded in evidence.json. South children face a narrow excavated/retained strip.'),
 ('I17 • MAJOR / MEDIUM','ENE view glazing: low-angle morning heat/glare; WSW parents glass: afternoon exposure. External shading and internal night blinds are unselected.'),
 ('I25 / I30 • MODERATE','Dashed sightlines are hypothetical observers, not surveyed neighbours. Northern future development and shared south terrace need day/night checks.'),
 ('SIMULATION NEEDED','Verify principal-room daylight, glare, overheating, secure purge and smoke-mode ventilation after location, weather, glazing and neighbour mass are established.')])
site_plan(ax)
for k in ['north-wet-court','south-daylight-grade']:geom(ax,S.to_project(shape(P['works'][k])),'#f4c5bc',RED,z=6)
route(ax,[(25.,-2.),(17.8,-3.)],GOLD,'--');route(ax,[(-1.,-6.),(1.5,-6.)],GOLD,'--')
route(ax,[(16.,4.),(15.,0.)],BLUE,'--');route(ax,[(10.,-10.3),(2.8,-8.7)],BLUE,'--')
tag(ax,(11.,3.7),'I16 / I25');tag(ax,(19.5,-2.),'I17');tag(ax,(2.,-9.4),'I30');tag(ax,(12.,-12.6),'I16')
save(fig,'09-daylight-privacy')

fig,ax=sheet('10 / Acoustic risk: actual floor overlaps','Red polygons are plan overlap with noisy/wet functions above; no sound rating or measured noise level',[
 ('I15 • MAJOR / MEDIUM','Boys: 3.64 m² beneath parents ensuite and 1.69 m² beneath kitchen. Girls: 2.66 m² beneath kitchen and 2.41 m² beneath dining.'),
 ('I15 • UPPER FLOOR','Parents also partly beneath road unloading (3.74 m²) and parking (2.86 m²). Vehicle vibration, garage door impulse and CO/fire separation need coordination.'),
 ('OPEN CORE','Named acoustic-lobby door objects are recorded as operation=open. No installed acoustic closure is evidenced.'),
 ('CORRECTION','Coordinate resilient floors/ceilings, isolated pipes/plant and real sealing doors. Test four desks + TV + kitchen + office video call together.')])
plan(ax,'lower')
for a in P['floors']['lower']['rooms']:
    if a['kind']=='sleep':
        for b in P['floors']['upper']['rooms']+P['floors']['upper']['zones']:
            if any(k in b['id'] for k in ['KITCHEN','ENSUITE','DINING']):geom(ax,S.to_project(shape(a['g']).intersection(shape(b['g']))),'#df8c77',RED,z=8,alpha=.8)
tag(ax,(7.5,-8.6),'I15');tag(ax,(12.,-8.6),'I15');tag(ax,(6.8,-2.4),'OPEN CORE')
save(fig,'10-acoustic-overlays')

fig,ax=sheet('11 / Cost-risk map: priorities before rates','No money totals or savings percentages; red = ground/retaining risk, gold = terrace/envelope, purple = essential equipment',[
 ('K1 • GROUND / RETAINING','219.29 m³ garden fill prism and 190.11 m³ lower-enclosure cut prism are separate overlapping measures, never additive construction quantities.'),
 ('K2 • TERRACES / ENVELOPE','93.18 m² terraces, buried walls, many thresholds, roof-edge/guard junctions and bespoke glazing carry waterproofing and access costs.'),
 ('K3 • EQUIPMENT / SERVICES','Essential three-stop lift; actual plant, backup, utilities and foul/storm disposal unknown. Cheap initial reservations do not price real systems.'),
 ('K4 • AREA / LOGISTICS','495.83 m² gross incl. garage/core; 82.64 m² per permanent occupant. No owner cap is imposed. Price/use-test every duplicated or residual zone.')])
site_plan(ax)
geom(ax,S.to_project(shape(P['floors']['upper']['lift']['envelope'])),'#9b79ad','#714285',z=8)
tag(ax,(24.,0.),'K1');tag(ax,(0.,-7.),'K1');tag(ax,(18.5,-9.8),'K2');tag(ax,(4.,0.),'K3');tag(ax,(12.,-3.),'K4')
save(fig,'11-cost-risk-map')
(OUT/'figures.json').write_text(json.dumps(FIGURES,indent=2)+'\n')
print(json.dumps({'figures':len(FIGURES),'door_overlap_m2':conflicts,'wet_court_area_m2':court.area,'wet_court_under_upper_m2':cover,'geometry_sha256':E['geometry_sha256']},indent=2))

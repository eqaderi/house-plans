"""Codex C01: exploratory massing and topology, NOT a resolved room plan.

Geometry is selected by CP-SAT from envelope-contained candidates. No default
road-aligned generator is invoked. Outputs are exports, not approved plans.
"""
import json
import math
from dataclasses import asdict
from pathlib import Path

from ortools.sat.python import cp_model
from shapely.geometry import Polygon
from shapely.ops import unary_union

from house_ai.domain.geometry import Polygon2D
from house_ai.domain.integrity import check_model
from house_ai.domain.model import HouseModel, Level, Slab, SlabKind
from house_ai.domain.proposal import ConceptProposal, ProposalLevelAssignment, StairCoreProposal
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind, Provenance
from house_ai.domain.records import Assumption
from house_ai.domain.site import Site
from house_ai.domain.terrain import elevation_at
from house_ai.geospatial.earthworks import integrate
from house_ai.storage import ProjectStore

OUT = Path(__file__).resolve().parent
store = ProjectStore(OUT.parents[1])
actor = Actor(kind=ActorKind.AGENT, id="codex")
# Pin the source survey and rebuilt program. Never change site truth for a layout.
site_ref = next(r for r in store.latest_of_kind(ArtifactKind.SITE) if r.id == "site")
program_ref = next(r for r in store.latest_of_kind(ArtifactKind.SPACE_PROGRAM) if r.id == "program")
site = store.get(site_ref, Site)
boundary = site.boundary.to_shapely()
envelope = site.buildable_envelope.polygon.to_shapely()
nw, sw, se, ne = site.boundary.outer
length = math.dist(nw, ne)
east = ((ne[0]-nw[0])/length, (ne[1]-nw[1])/length)
south = (east[1], -east[0])

def xy(u, v):
    return (nw[0]+u*east[0]+v*south[0], nw[1]+u*east[1]+v*south[1])

def rect(u, v, d, w):
    return Polygon([xy(u,v),xy(u+d,v),xy(u+d,v+w),xy(u,v+w)])

def solve_mass(min_floor_m2):
    # 5.5m is an UNVERIFIED approach allowance, not a vehicle swept-path proof.
    # 1m northern clearance is a design assumption, not a legal setback claim.
    # 0.8m lower-floor offset expresses stepping without a sprawling footprint.
    candidates = []
    for d in range(110, 151):
        for w in range(90, 111):
            if d*w < min_floor_m2*100:
                continue
            top_d = math.ceil(9000/w)
            for u in [55,60,65]:
                for v in [10,15,20]:
                    polys = [rect(u/10,v/10,top_d/10,w/10),
                             rect(u/10,v/10,d/10,w/10),
                             rect((u+8)/10,v/10,d/10,w/10)]
                    if all(envelope.buffer(1e-7).covers(p) for p in polys):
                        union_dm2 = (d+8)*w
                        candidates.append((u,v,d,w,top_d,union_dm2))
    assert candidates, "No feasible massing candidate in the tested range"
    m = cp_model.CpModel()
    vs = [m.NewIntVar(min(t[i] for t in candidates),max(t[i] for t in candidates),n)
          for i,n in enumerate(['u','v','d','w','top_d','footprint'])]
    m.AddAllowedAssignments(vs,candidates)
    # Lexicographic in practice: area first; northwest position second;
    # a reasonably broad east-facing frontage breaks ties.
    m.Minimize(vs[5]*100000 + vs[0]*100 + vs[1]*10 - vs[3])
    solver=cp_model.CpSolver()
    solver.parameters.num_search_workers=1
    solver.parameters.random_seed=0
    solver.parameters.max_time_in_seconds=20
    status=solver.Solve(m)
    assert status in [cp_model.OPTIMAL,cp_model.FEASIBLE]
    u,v,d,w,td,area=[solver.Value(x) for x in vs]
    polys=[rect(u/10,v/10,td/10,w/10),rect(u/10,v/10,d/10,w/10),rect((u+8)/10,v/10,d/10,w/10)]
    return {'solver_status':solver.StatusName(status),'candidate_count':len(candidates),
            'min_residential_floor_assumption_m2':min_floor_m2,
            'u_m':u/10,'v_m':v/10,'depth_m':d/10,'width_m':w/10,
            'top_depth_m':td/10,'projected_footprint_m2':area/100,
            'floor_areas_m2':[round(p.area,3) for p in polys]},polys

rows=[]
for target in [115,125,135]:
    r,polys=solve_mass(target)
    rows.append(r)
    if target==125:
        chosen, footprints=r,polys

building=unary_union(footprints)
end=chosen['u_m']+chosen['depth_m']+.8
downhill=envelope.intersection(rect(end,0,60,60))
arrival=boundary.intersection(rect(-30,chosen['v_m'],30+chosen['u_m'],chosen['width_m']))
# Keep the broad southern/eastern open region together; exclude the narrow
# northern strip and western apron rather than calling all unbuilt land garden.
garden=envelope.intersection(unary_union([rect(end,0,60,60),
    rect(-30,chosen['v_m']+chosen['width_m'],100,60)]))
assert garden.geom_type=='Polygon'
assert garden.intersection(building).area < 1e-6
assert building.intersection(arrival).area < 1e-6
assert building.intersection(downhill).area < 1e-6
assert downhill.geom_type=='Polygon'
# TIN sampling only: the western reference is not a surveyed road/garage threshold.
road_xy=((nw[0]+sw[0])/2,(nw[1]+sw[1])/2)
z=elevation_at(site.terrain.surface,road_xy)
assert z is not None
level_z=[z,z-3.2,z-6.4]
screen=integrate(site.terrain.surface,downhill,level_z[-1])
assumptions=[
    'Exploratory massing only: no room packing, doors, stairs, lift shaft, structure or garage manoeuvring has been resolved.',
    'Three tiers are owner-confirmed. 3.2m floor intervals and the TIN western midpoint reference are assumptions, not chosen finished-floor levels.',
    'Tested residential gross floor-area lower bounds 115/125/135m² are Codex area budgets, not demonstrated minimum footprints.',
    'Northern 1m clearance, western 5.5m approach allowance, 0.8m lower-floor step and approximately 90m² top tier are exploratory assumptions.',
    'Downhill garden reserve is land in plan, not a graded garden. Flatness, retaining, drainage, soil and planting suitability are unresolved.',
    'Top office and plant room are tentative. Main-house axes strictly follow the north/south long boundaries; no road-aligned variant is permitted.',
]
model=HouseModel(id='codex-c01-massing',name='Codex C01 — boundary-aligned exploratory massing',
    coordinate_system_id=site.coordinates.local.id,site_ref=site_ref,program_ref=program_ref,
    levels=[Level(id=lid,name=name,elevation_m=height,floor_to_floor_m=3.2)
            for lid,name,height in zip(['road','res-upper','res-lower'],['Road / garage tier','Upper residential tier','Lower residential tier'],level_z)],
    slabs=[Slab(id=f'c01-mass-{lid}',level_id=lid,kind=SlabKind.FLOOR,
                boundary=Polygon2D(outer=list(p.exterior.coords)[:-1]),thickness_m=.25)
           for lid,p in zip(['road','res-upper','res-lower'],footprints)],
    assumptions=[Assumption(id=f'c01-assumption-{i}',statement=s,made_by=actor) for i,s in enumerate(assumptions,1)])
findings=check_model(model,site)
(OUT/'massing-model.json').write_text(model.model_dump_json(indent=2)+'\n')
(OUT/'integrity-findings.json').write_text(json.dumps([f.model_dump(mode='json') for f in findings],indent=2)+'\n')

for key,day,night in [('a','entry','lower'),('b','lower','entry')]:
    mapping={'pi-entry':'entry','pi-garage':'upper','pi-study-1':'upper','pi-mechanical':'upper',
             'pi-living':day,'pi-kitchen':day,'pi-dining':day,'pi-pantry':day,'pi-bath-2':day,
             'pi-storage':day,'pi-terrace':day,'pi-bed-main':night,'pi-bed-elder-1':night,
             'pi-bed-child-1':night,'pi-bed-child-2':night,'pi-bath-ensuite':night,
             'pi-bath-1':night,'pi-laundry':night,'pi-lift':'entry','pi-stair':'entry'}
    proposal=ConceptProposal(id=f'codex-c01-{key}',project_id='my-house',
        name=f'Codex C01-{key.upper()} — living {"upstairs" if key=="a" else "downstairs"}',
        intent='Exploratory topology only. Strict side-boundary alignment, northwest siting, western arrival court, garage above two residential floors. Compact shared stair/lift core; short vestibules, no double-loaded corridor. Lift must serve all tiers; lift/stair program assignments indicate core anchor only. Do not run the current road-default generator on this proposal. Office/plant at top tentative. Four bedrooms, two shared children rooms. Main entry stays at upper residential floor in both options.',
        level_assignments=[ProposalLevelAssignment(program_item_id=p,level_id=l) for p,l in mapping.items()],
        stair_cores=[StairCoreProposal(id=f'c01-{key}-core',position='entry',connects_levels=['upper','entry','lower'],near_program_item_ids=['pi-entry','pi-lift'])],
        target_strategy='corridor_free',
        provenance=Provenance(created_at=store.clock(),created_by=actor,method='agent_topology_proposal',inputs=[site_ref,program_ref]))
    (OUT/f'codex-c01-{key}-proposal.json').write_text(proposal.model_dump_json(indent=2)+'\n')

report={'author':'agent:codex','study':'Codex C01','status':'exploratory massing / topology, not a resolved floor plan',
        'site_ref':site_ref.model_dump(mode='json'),'program_ref':program_ref.model_dump(mode='json'),
        'geometry_source':'CP-SAT selection from surveyed-envelope-contained candidates; orthogonal axes from long north/south boundary',
        'solver_scope':'Minimum projected union within enumerated assumptions only; not a global architectural optimum',
        'sensitivity':rows,'selected':chosen,'parcel_area_m2':boundary.area,
        'unbuilt_plan_area_m2':boundary.area-building.area,'downhill_reserve_plan_area_m2':downhill.area,
        'connected_south_east_garden_reserve_plan_area_m2':garden.area,
        'arrival_reserve_plan_area_m2':arrival.area,'assumptions':assumptions,
        'downhill_plane_screen':{'plane_elevation_m':level_z[-1],**asdict(screen)},
        'geometry':{'building_union':list(building.exterior.coords),'downhill':list(downhill.exterior.coords),'garden':list(garden.exterior.coords),'arrival':list(arrival.exterior.coords)},
        'not_checked':['room/furniture fit','vehicle swept paths and door approach','lift and stair geometry','retaining design','actual road thresholds','structure','legal site approval','garden grading','construction cost']}
(OUT/'study.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['geometry','assumptions','not_checked']},indent=2))

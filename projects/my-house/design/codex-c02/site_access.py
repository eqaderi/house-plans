"""Solver-checked exterior stair reservation and site/section review drawing.

This is an access reservation, separate from the interior HouseModel: terrain,
road thresholds and detailed outside stair construction remain unresolved.
"""
import html
import json
import math
import subprocess
from pathlib import Path

from ortools.sat.python import cp_model
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from house_ai.domain.plan import PlanVersion
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.site import Site
from house_ai.storage import ProjectStore

ROOT=Path(__file__).resolve().parent;store=ProjectStore(ROOT.parents[1])
site=store.get(store.latest(ArtifactKind.SITE,'site'),Site)
summary=[]
for folder in sorted(ROOT.glob('codex-c02-*')):
    if not (folder/'plan.json').exists():continue
    plan=PlanVersion.model_validate_json((folder/'plan.json').read_text());m=plan.model
    site=store.get(plan.model.site_ref,Site)
    placement=json.loads((folder/'placement.json').read_text());fr=placement['frame']
    origin=fr['origin'];u=fr['u'];v=fr['v']
    def local(p):return origin[0]+p[0]*u[0]+p[1]*v[0],origin[1]+p[0]*u[1]+p[1]*v[1]
    def des(p):
        x,y=p[0]-origin[0],p[1]-origin[1]
        return x*u[0]+y*u[1],x*v[0]+y*v[1]
    def poly_local(g):return Polygon([local(p) for p in g.exterior.coords])
    env=site.buildable_envelope.polygon.to_shapely()
    building=unary_union([s.boundary.to_shapely() for s in m.spaces if s.function.value not in ['balcony','terrace']])
    balcony=m.space('sp-balcony').boundary.to_shapely()
    entry=next(r for r in placement['rooms'] if r['space_id']=='sp-main-entry')
    land_y=entry['v1']+(20 if plan.option_id.endswith('-b') else 0)
    target=(entry['u0']+entry['u1'])//2
    candidates=[];geoms={}
    for end in range(target-8,target+9,2):
        for north in range(land_y+12,land_y+27,2):
            # Full stair reserve includes 1.2m landing at either end of a 4.8m run.
            reserve=box((end-72)/10,north/10,end/10,(north+13)/10)
            connector=box((end-12)/10,land_y/10,end/10,north/10)
            shape=poly_local(unary_union([reserve,connector]).convex_hull)
            if env.buffer(1e-7).covers(shape) and building.intersection(shape).area<1e-7 and balcony.intersection(shape).area<1e-7:
                key=(end,north);geoms[key]=(reserve,connector)
                candidates.append((end,north,abs(end-target)*10+north-land_y))
    assert candidates,'No outside stair reserve fits the tested range'
    cp=cp_model.CpModel();a=cp.NewIntVar(min(x[0] for x in candidates),max(x[0] for x in candidates),'end')
    b=cp.NewIntVar(min(x[1] for x in candidates),max(x[1] for x in candidates),'north')
    c=cp.NewIntVar(0,10000,'distance');cp.AddAllowedAssignments([a,b,c],candidates);cp.Minimize(c)
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1
    status=solver.Solve(cp)
    assert status in [cp_model.OPTIMAL,cp_model.FEASIBLE]
    end,north=solver.Value(a),solver.Value(b);reserve,connector=geoms[(end,north)]
    stair=poly_local(reserve);walk=poly_local(connector)
    projected=unary_union([building,balcony])
    remaining=env.difference(unary_union([projected,stair,walk]).buffer(1e-6))
    # South/east garden region; small northern strips and western court excluded.
    end_u=max(des(q)[0] for sp in m.spaces for q in sp.boundary.outer)
    south_v=max(r['v1'] for r in placement['rooms'] if r['space_id']!='sp-balcony')/10
    garden_cut=unary_union([poly_local(box(end_u,0,50,40)),poly_local(box(-20,south_v,50,40))])
    garden=remaining.intersection(garden_cut)
    garden_parts=[p for p in getattr(garden,'geoms',[garden]) if p.geom_type=='Polygon']
    garden_main=max(garden_parts,key=lambda x:x.area)
    row={'option':plan.option_id,'building_projection_m2':building.area,
         'balcony_projection_m2':balcony.area,'building_and_balcony_union_m2':projected.area,
         'outside_stair_and_connector_m2':unary_union([stair,walk]).area,
         'gross_open_plan_area_m2':site.boundary.area_m2-projected.area,
         'main_connected_garden_reserve_m2':garden_main.area,
         'maximum_house_extent_from_frame_origin_m':max(des(p)[0] for p in projected.exterior.coords) if projected.geom_type=='Polygon' else max(des(p)[0] for g in projected.geoms for p in g.exterior.coords),
         'stair_reservation':{'solver_status':solver.StatusName(status),'top_level':'lv-upper','bottom_level':'lv-entry','run_m':4.8,'width_m':1.3,'landings_m':1.2,'assumed_rise_m':3,'assumed_risers':18,'tread_assumption_m':.28,'footprint_local_m':list(stair.exterior.coords),'connector_local_m':list(walk.exterior.coords)},
         'status':'Measured plan areas / CP-SAT containment; garden grading, road approach, external stair construction and structural design not checked'}
    (folder/'site-access.json').write_text(json.dumps(row,indent=2)+'\n');summary.append(row)
    W,H=1500,1040;svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="#f6f3ec"/><style>text{{font-family:DejaVu Sans,Arial,sans-serif;fill:#203d3e}}</style>']
    def text(x,y,t,size=17,anchor='start'):svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{html.escape(t)}</text>')
    def line(a,b,col='#334d4d',w=2):svg.append(f'<path d="M{a[0]},{a[1]}L{b[0]},{b[1]}" stroke="{col}" stroke-width="{w}" fill="none"/>')
    def xy(p):return 120+p[0]*18,820-p[1]*18
    def polygon(g,fill,stroke='#49615a',dash=False):
        for poly in getattr(g,'geoms',[g]):
            if poly.geom_type!='Polygon':continue
            ps=' '.join(f'{x:.1f},{y:.1f}' for x,y in map(xy,poly.exterior.coords))
            svg.append(f'<polygon points="{ps}" fill="{fill}" fill-opacity=".82" stroke="{stroke}" stroke-width="2"'+(' stroke-dasharray="5 4"' if dash else '')+'/>')
    text(36,44,plan.label+' — site and stepped elevation',28)
    text(36,76,'House follows long side boundaries. Outside stairs arrive at the upper residential entrance.',16)
    polygon(site.boundary.to_shapely(),'#e9eadb')
    polygon(garden_main,'#bcd7a2')
    polygon(building,'#729d9f')
    polygon(balcony,'#d7b779')
    polygon(stair,'#b9b7b4');polygon(walk,'#ddcec0')
    # Treads are derived from the solved stair-reservation rectangle.
    for t in range(18):
        uu=(end-60+t*48/17)/10
        line(xy(local((uu,north/10))),xy(local((uu,(north+13)/10))),'#747b77',1)
    text(96,855,'غرب / خیابان',18)
    text(440,865,'باغ جنوب و پایین زمین',18)
    text(80,916,f'Building projection: {building.area:.1f} m² · balcony: {balcony.area:.1f} m²',17)
    text(80,945,f'Connected garden reserve after stairs: ~{garden_main.area:.0f} m² (ungraded)',17)
    # Section is model geometry projected onto the downhill axis, not guessed massing.
    sx,sy,sc=835,590,31
    text(818,162,'Schematic side elevation / ENE axis',22)
    levels=sorted(m.levels,key=lambda x:-x.elevation_m)
    for lv in levels:
        shapes=[Polygon([des(q) for q in s.boundary.outer]) for s in m.spaces if s.level_id==lv.id and s.function.value not in ['balcony','terrace']]
        lo=min(g.bounds[0] for g in shapes);hi=max(g.bounds[2] for g in shapes)
        yy=sy-(lv.elevation_m-levels[-1].elevation_m)*sc
        svg.append(f'<rect x="{sx+lo*sc}" y="{yy-2.7*sc}" width="{(hi-lo)*sc}" height="{2.7*sc}" fill="#d9e4dc" stroke="#40575a" stroke-width="2"/>')
        line((sx+lo*sc,yy),(sx+hi*sc,yy),'#304c4e',5)
        text(sx+lo*sc+8,yy-35,{'lv-upper':'Road / garage','lv-entry':'Upper residential','lv-lower':'Lower residential'}[lv.id],15)
    bshape=Polygon([des(q) for q in m.space('sp-balcony').boundary.outer]);lo,_,hi,_=bshape.bounds
    yy=sy-(m.level('lv-entry').elevation_m-levels[-1].elevation_m)*sc
    line((sx+lo*sc,yy),(sx+hi*sc,yy),'#bd9554',7)
    text(818,650,'3 tiers · one aligned internal stair/lift core',17)
    text(818,686,'3m intervals are assumptions; road thresholds',15)
    text(818,710,'and garden finished levels are unresolved.',15)
    text(818,760,'Blue = building · gold = balcony',15)
    text(818,786,'Grey = outside stair reservation',15)
    text(818,812,'Green = reserved garden land',15)
    text(36,1002,'EXPLORATORY · Exterior stair shown as a solver-contained reservation, not a finished stair/retaining or grading design.',15)
    svg.append('</svg>');(folder/'site-section.svg').write_text('\n'.join(svg))
    subprocess.run(['rsvg-convert','-w','1800','-o',str(folder/'site-section.png'),str(folder/'site-section.svg')],check=True)
(ROOT/'comparison-metrics.json').write_text(json.dumps(summary,indent=2)+'\n')
for r in summary:print(r['option'],'building',round(r['building_projection_m2'],1),'garden',round(r['main_connected_garden_reserve_m2'],1))

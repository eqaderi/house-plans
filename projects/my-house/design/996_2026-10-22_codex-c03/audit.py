"""Read-only verification and measured comparison of the C03 exports."""
from pathlib import Path
import json, math
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
from house_ai.domain.plan import PlanVersion
from house_ai.domain.site import Site
from house_ai.domain.program import SpaceProgram
from house_ai.domain.integrity import check_model
from house_ai.storage import ProjectStore
from house_ai.evaluation.routes import RouteNetwork
from earthwork import calculate,self_test
ROOT=Path(__file__).resolve().parent;store=ProjectStore(ROOT.parents[1])
self_test();rows=[]
for folder in sorted(ROOT.glob('codex-c03-*')):
    if not (folder/'plan.json').exists():continue
    plan=PlanVersion.model_validate_json((folder/'plan.json').read_text());m=plan.model
    site=store.get(m.site_ref,Site);prog=SpaceProgram.model_validate_json((folder/'scenario-program.json').read_text())
    findings=check_model(m,site,prog);assert not findings,findings
    pl=json.loads((folder/'placement.json').read_text());fr=pl['frame'];o,u,v=fr['origin'],fr['u'],fr['v']
    def de(q):return(round((q[0]-o[0])*u[0]+(q[1]-o[1])*u[1],5),round((q[0]-o[0])*v[0]+(q[1]-o[1])*v[1],5))
    shapes={s.id:Polygon([de(q) for q in s.boundary.outer],[[de(q) for q in r] for r in s.boundary.holes]) for s in m.spaces}
    closed={lv.id:unary_union([shapes[s.id] for s in m.spaces if s.level_id==lv.id and s.function.value not in ['terrace','balcony']]) for lv in m.levels}
    plate_gaps={lv:box(*g.bounds).difference(g).area for lv,g in closed.items() if lv!='lv-upper'}
    assert all(x<1e-6 for x in plate_gaps.values()),plate_gaps
    terraces=[s for s in m.spaces if s.function.value=='terrace']
    roof=unary_union([shapes[s.id] for s in terraces]);unsupported=roof.difference(closed['lv-lower']).area
    assert unsupported<1e-6,unsupported
    kitchen_doors=[op for op in m.openings if set(op.connects)=={'sp-kitchen','sp-terrace-south'} and op.is_passable]
    assert kitchen_doors
    for op in kitchen_doors:
        wall=m.wall(op.host_wall_id);a,b=de(wall.start),de(wall.end)
        assert abs(a[1]-b[1])<1e-4
        assert abs(a[1]-shapes['sp-kitchen'].bounds[3])<1e-4
        assert op.material_id=='m-window'
    furniture=json.loads((folder/'furniture-check.json').read_text());assert all(r['status']!='not_fitted' for r in furniture)
    for item in m.furniture:
        assert m.space(item.space_id).boundary.to_shapely().buffer(1e-5).covers(item.footprint_polygon().to_shapely())
    graph={s.id:set() for s in m.spaces}
    for op in m.openings:
        if not op.is_passable:continue
        a,b=op.connects
        if a in graph and b in graph:graph[a].add(b);graph[b].add(a)
    def reachable(start,exclude_beds=False):
        seen={start};todo=[start]
        while todo:
            for nxt in graph[todo.pop()]-seen:
                if exclude_beds and m.space(nxt).function.value=='bedroom':continue
                seen.add(nxt);todo.append(nxt)
        return seen
    common=reachable('sp-main-entry',True)
    assert all(s.id in common for s in terraces),'Terrace access requires a bedroom or is disconnected'
    network=RouteNetwork(m)
    targets=['sp-living','sp-kitchen','sp-main-bed','sp-elder-bed','sp-boys','sp-girls',*[s.id for s in terraces]]
    routes={sid:network.between('sp-main-entry',sid) for sid in targets}
    # This is the native point-path check; never advertise it as a body-width certificate.
    route_report={sid:None if r is None else dict(length_m=r.length_m,spaces=r.space_ids,estimated=r.estimated) for sid,r in routes.items()}
    projection=unary_union(list(closed.values()));earth=calculate(folder)
    sensitivities=[dict(floor_shift_m=shift,cut_m3=calculate(folder,level_shift=shift)['cut_m3']) for shift in [-.5,0,.5]]
    row=dict(option=plan.option_id,epistemic_status='measured plan geometry; inferred terrain/earthworks; point-route check only',
             enclosed_area_m2={lv:closed[lv].area for lv in closed},building_projection_m2=projection.area,
             gross_unbuilt_site_area_m2=site.boundary.area_m2-projection.area,
             terrace_areas_m2={s.id:s.area_m2 for s in terraces},roof_terrace_area_m2=roof.area,
             uncovered_roof_terrace_area_m2=unsupported,unassigned_plate_area_m2=plate_gaps,
             living_to_lower_east_step_m=pl['bounds']['lv-lower'][0]/10-pl['bounds']['lv-entry'][0]/10,
             cut_m3=earth['cut_m3'],maximum_cut_depth_m=earth['max_cut_depth_m'],floor_height_sensitivity=sensitivities,
             kitchen_south_terrace_doors=[op.id for op in kitchen_doors],basic_furniture_fit=True,
             point_routes=route_report,unreachable_point_route_targets=[sid for sid,r in routes.items() if r is None],
             check_model_findings=0,baseline_program_findings=json.loads((folder/'baseline-program-findings.json').read_text()))
    (folder/'audit.json').write_text(json.dumps(row,indent=2)+'\n');rows.append(row)
(ROOT/'comparison-metrics.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(r['option'],'cut',round(r['cut_m3'],1),'terraces',round(r['roof_terrace_area_m2'],1),'projection',round(r['building_projection_m2'],1),'unreachable point routes',r['unreachable_point_route_targets'])

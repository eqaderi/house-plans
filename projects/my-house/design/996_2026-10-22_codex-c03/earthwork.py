"""Exact integration of positive TIN-to-formation depth; no double-counted tiers.

Scenario proxy only: no batter, working room, footings, access, drainage, garden
levelling or bulking. Outside the surveyed TIN is unknown, never extrapolated.
"""
from pathlib import Path
import json
from shapely.geometry import Polygon
from shapely.ops import unary_union
from house_ai.domain.plan import PlanVersion
from house_ai.domain.site import Site
from house_ai.storage import ProjectStore

ROOT=Path(__file__).resolve().parent
STORE=ProjectStore(ROOT.parents[1])


def clip_positive(vertices, datum):
    result=[]
    for a,b in zip(vertices,vertices[1:]+vertices[:1]):
        ha,hb=a[2]-datum,b[2]-datum
        if ha>=0:result.append(a)
        if (ha<0)!=(hb<0):
            t=ha/(ha-hb)
            result.append(tuple(a[i]+t*(b[i]-a[i]) for i in range(3)))
    return result


def integrate(surface, footprint, datum):
    volume=0.0;known=0.0;cut_area=0.0;max_depth=0.0
    for ia,ib,ic in surface.triangles:
        a,b,c=[surface.vertices[i] for i in [ia,ib,ic]]
        tri=Polygon([q[:2] for q in [a,b,c]])
        hit=footprint.intersection(tri)
        if hit.area<1e-9:continue
        known+=hit.area
        det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        def depth(p):
            wb=((p[0]-a[0])*(c[1]-a[1])-(p[1]-a[1])*(c[0]-a[0]))/det
            wc=((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))/det
            return a[2]+wb*(b[2]-a[2])+wc*(c[2]-a[2])-datum
        clipped=clip_positive([a,b,c],datum)
        if len(clipped)<3:continue
        cut=footprint.intersection(Polygon([q[:2] for q in clipped]))
        if cut.area<1e-9:continue
        volume+=cut.area*max(0,depth((cut.centroid.x,cut.centroid.y)))
        cut_area+=cut.area
        for g in getattr(cut,'geoms',[cut]):
            if g.geom_type=='Polygon':
                max_depth=max(max_depth,*[depth(q) for q in g.exterior.coords])
    return dict(cut_m3=volume,cut_area_m2=cut_area,max_cut_depth_m=max_depth,
                known_area_m2=known,unknown_area_m2=max(0,footprint.area-known))


def calculate(folder, formation_allowance=.35, level_shift=0.0):
    plan=PlanVersion.model_validate_json((folder/'plan.json').read_text());m=plan.model
    site=STORE.get(m.site_ref,Site)
    covered=Polygon();rows=[];footprints={}
    for lv in sorted(m.levels,key=lambda x:x.elevation_m):
        fp=unary_union([s.boundary.to_shapely() for s in m.spaces if s.level_id==lv.id and s.function.value not in ['terrace','balcony']])
        # Lowest floor at each XY determines the excavation; upper tiers are not added twice.
        zone=fp.difference(covered);covered=unary_union([covered,fp]);footprints[lv.id]=fp
        result=integrate(site.terrain.surface,zone,lv.elevation_m+level_shift-formation_allowance)
        rows.append(dict(level=lv.id,floor_m=lv.elevation_m,formation_allowance_m=formation_allowance,**result))
    return dict(option=plan.option_id,method='inferred: exact linear integration on stored survey TIN, lowest formation at each XY',
                cut_m3=sum(r['cut_m3'] for r in rows),max_cut_depth_m=max(r['max_cut_depth_m'] for r in rows),
                unknown_area_m2=sum(r['unknown_area_m2'] for r in rows),building_projection_m2=covered.area,levels=rows,
                exclusions=['garden grading','exterior stairs and access','working clearance and batter','individual foundations and retaining walls','drainage','bulking and disposal'],
                road_and_floor_elevations='assumed C02 western reference retained for comparison; not surveyed thresholds')


def self_test():
    from types import SimpleNamespace
    t=SimpleNamespace(vertices=[(0,0,0),(2,0,2),(0,2,0)],triangles=[(0,1,2)])
    shape=Polygon([(0,0),(2,0),(0,2)])
    assert abs(integrate(t,shape,0)['cut_m3']-4/3)<1e-9
    assert abs(integrate(t,shape,1)['cut_m3']-1/6)<1e-9
    assert abs(integrate(t,shape,3)['cut_m3'])<1e-9
    assert integrate(t,Polygon([(3,3),(4,3),(3,4)]),0)['unknown_area_m2']==.5

if __name__=='__main__':
    self_test();rows=[]
    for folder in [*sorted((ROOT.parent/'codex-c02').glob('codex-c02-*')),*sorted(ROOT.glob('codex-c03-*'))]:
        if (folder/'plan.json').exists():rows.append(calculate(folder))
    (ROOT/'earthwork-comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
    for row in rows:print(row['option'],round(row['cut_m3'],1),'m3',round(row['max_cut_depth_m'],2),'m max cut; unknown m2',round(row['unknown_area_m2'],2))

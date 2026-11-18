"""Analytical terrain screening, not a floor plan or an approved grading design."""
from pathlib import Path
from dataclasses import asdict
import json
import math
import numpy as np
from shapely.geometry import Polygon
from house_ai.storage import ProjectStore
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.site import Site
from house_ai.domain.terrain import elevation_at
from house_ai.geospatial.earthworks import integrate

out = Path(__file__).resolve().parent
store = ProjectStore(out.parents[1])
ref = store.latest(ArtifactKind.SITE, 'site')
site = store.get(ref, Site)
p = np.array(site.boundary.outer)
v, w = p[0]-p[1], p[2]-p[1]
at = lambda u,t: p[1]+u*v+t*w
west_ref = tuple(at(.5,0))
west_z = elevation_at(site.terrain.surface, west_ref)
rows = []
for name,t0,t1 in [('upper_southern_strip',.18,.48),('middle_southern_strip',.30,.60),('lower_southern_strip',.42,.72)]:
    # Equal-area sampling windows shifted downhill; NOT proposed construction pads.
    u0,u1=.08,.72
    q=Polygon([at(u0,t0),at(u0,t1),at(u1,t1),at(u1,t0)])
    assert site.buildable_envelope.polygon.to_shapely().buffer(1e-8).covers(q)
    r=integrate(site.terrain.surface,q,west_z)
    assert math.isclose(r.known_area_m2,q.area,abs_tol=1e-7)
    mean_z=west_z-(r.below_plane_m3-r.cut_m3)/r.known_area_m2
    balanced=integrate(site.terrain.surface,q,mean_z)
    assert math.isclose(balanced.cut_m3,balanced.below_plane_m3,abs_tol=1e-7)
    examples=[]
    for fall in [3.2,6.4]:
        z=west_z-fall
        examples.append({'assumed_fall_below_west_reference_m':fall,'hypothetical_plane_m':z,**asdict(integrate(site.terrain.surface,q,z))})
    rows.append({'id':name,'status':'inferred; comparative terrain sampling window, not proposed garden geometry','polygon_local_m':list(q.exterior.coords)[:-1],'area_m2':q.area,'average_existing_ground_m':mean_z,'below_west_reference_m':west_z-mean_z,'balanced_geometric_plane':asdict(balanced),'hypothetical_planes':examples})
manifest={'project_id':store.project_id,'site_ref':ref.model_dump(mode='json'),'method':'exact clipping of stored TIN to equal-area analytical sampling windows; affine integration','status':'inferred terrain screening; no architectural layout, grading, soil suitability, retaining structures or cost validated','west_reference':{'xy_local_m':west_ref,'z_m':west_z,'status':'TIN-interpolated parcel-west-boundary midpoint, NOT measured road/garage finished-floor level'},'sampling_windows':rows,'ramp_illustration':{'hypothetical_drop_m':12,'hypothetical_grade':.15,'required_horizontal_run_m':80,'status':'arithmetic illustration only; no local legal ramp limit assumed, no turning or transition allowance included'},'unchanged_canonical_site':True}
(out/'terrain-screening.json').write_text(json.dumps(manifest,indent=2)+'\n')
for row in rows:
    r=row['balanced_geometric_plane']
    print(row['id'],f"{row['area_m2']:.1f} m²",f"{row['below_west_reference_m']:.2f} m below west reference",f"balanced geometric cut/space below plane: {r['cut_m3']:.1f}/{r['below_plane_m3']:.1f} m³",f"max cut / below plane: {r['max_cut_m']:.2f}/{r['max_below_m']:.2f} m")

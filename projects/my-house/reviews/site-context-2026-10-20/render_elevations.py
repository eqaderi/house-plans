"""Derive an elevation overlay from the current canonical site; preserve the context original."""
from pathlib import Path
from html import escape
import json
import math
import re
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
from house_ai.storage import ProjectStore
from house_ai.domain.provenance import ArtifactKind
from house_ai.domain.site import Site
from house_ai.domain.terrain import elevation_at
from house_ai.render2d.terrain_svg import _segment_at

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
store = ProjectStore(ROOT)
ref = store.latest(ArtifactKind.SITE, 'site')
site = store.get(ref, Site)
surface = site.terrain.surface
assert surface is not None
parcel = Polygon(site.boundary.outer)
p = np.array(site.boundary.outer)
S = 12.4
X = lambda x: 255 + S * float(x)
Y = lambda y: 654 - S * float(y)
points = lambda seq: ' '.join(f'{X(a[0]):.3f},{Y(a[1]):.3f}' for a in seq)

def poly_parts(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    return [g for g in geom.geoms if g.geom_type == 'Polygon']

def line_parts(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'LineString':
        return [geom]
    return [g for g in geom.geoms if g.geom_type == 'LineString']

def txt(x, y, value, size=15, color='#253640', anchor='start', halo=False, weight='normal'):
    h = ' paint-order="stroke" stroke="#fbfaf6" stroke-width="4" stroke-linejoin="round"' if halo else ''
    return f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" style="fill:{color}" text-anchor="{anchor}" font-weight="{weight}"{h}>{escape(value)}</text>'

def clip_z(vertices, z, above):
    result = []
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        ina = a[2] >= z if above else a[2] <= z
        inb = b[2] >= z if above else b[2] <= z
        if ina:
            result.append(a)
        if ina != inb:
            t = (z-a[2]) / (b[2]-a[2])
            result.append(tuple(a[i]+t*(b[i]-a[i]) for i in range(3)))
    return result

low = np.array([192, 220, 221])
high = np.array([231, 192, 147])
def color(z):
    t = min(1, max(0, (z-1664)/14))
    c = np.rint(low*(1-t)+high*t).astype(int)
    return '#' + ''.join(f'{a:02x}' for a in c)

svg = (OUT/'site-context.svg').read_text()
svg = svg.replace('height="850" viewBox="0 0 1100 850"', 'height="1240" viewBox="0 0 1100 1240"')
svg = svg.replace('<rect width="1100" height="850"', '<rect width="1100" height="1240"')
svg = svg.replace('Site geometry, access and principal outlook', 'Site geometry, elevations and principal outlook')
svg = svg.replace('Survey boundary to scale • Owner-reported site context • 20 October 2026', 'Survey boundary to scale • Terrain from surveyed heights • 20 October 2026')
defs = f'''<pattern id="unknown" patternUnits="userSpaceOnUse" width="5" height="5"><path d="M0,5 L5,0" stroke="#b8b5ab" stroke-width="1"/></pattern><linearGradient id="elev" x1="0" x2="1"><stop offset="0" stop-color="{color(1678)}"/><stop offset="1" stop-color="{color(1664)}"/></linearGradient><clipPath id="parcel"><polygon points="{points(p)}"/></clipPath>'''
svg = svg.replace('</defs>', defs+'</defs>')
# Keep the established survey footprint and add terrain behind its outline.
base_match = re.search(r'<polygon[^>]+fill="#eef2e9"[^>]*/>', svg)
assert base_match
base = base_match.group(0)
triangles = []
coverage = []
band_count = 0
for ids in surface.triangles:
    verts = [surface.vertices[i] for i in ids]
    triangle = Polygon([v[:2] for v in verts])
    covered = triangle.intersection(parcel)
    if covered.is_empty:
        continue
    coverage.append(covered)
    for lower in np.arange(1664, 1678, .25):
        band = clip_z(verts, float(lower), True)
        if len(band) < 3:
            continue
        band = clip_z(band, float(lower+.25), False)
        if len(band) < 3:
            continue
        geom = Polygon([a[:2] for a in band]).intersection(parcel)
        for part in poly_parts(geom):
            if part.area < 1e-12:
                continue
            triangles.append(f'<polygon points="{points(part.exterior.coords)}" fill="{color(lower+.125)}" stroke="{color(lower+.125)}" stroke-width="0.25"><title>Interpolated terrain: {lower:.2f}–{lower+.25:.2f} m</title></polygon>')
            band_count += 1
covered_area = unary_union(coverage).area
terrain = '<g id="elevation-terrain" clip-path="url(#parcel)"><polygon points="'+points(p)+'" fill="url(#unknown)"/>'+''.join(triangles)+'</g>'
svg = svg[:base_match.start()] + terrain + base.replace('fill="#eef2e9"', 'fill="none"') + svg[base_match.end():]
# Use canonical clipped polygons for both setback overlays.
svg = re.sub(r'<polygon[^>]*fill="#f4d9b5"[^>]*/>', '', svg)
setbacks = ''.join(f'<polygon points="{points(next(f for f in site.features if f.id==fid).geometry.polygon.outer)}" fill="#f4d9b5" fill-opacity="0.88"/>' for fid in ['owner-south-setback','owner-east-setback'])
# Insert contours after terrain but before the original no-fill boundary/envelope.
contours = []
contour_ledger = []
label_transect = LineString([.8*p[0]+.2*p[1], .8*p[3]+.2*p[2]])
for z in range(1666, 1678, 2):
    parts = []
    for ids in surface.triangles:
        v = [surface.vertices[i] for i in ids]
        seg = _segment_at(z, *v)
        if seg is None:
            continue
        for ln in line_parts(LineString(seg).intersection(parcel)):
            parts.append(ln)
            xy = list(ln.coords)
            for point in xy:
                value = elevation_at(surface, point)
                assert value is not None and math.isclose(value, z, abs_tol=2e-7)
            contours.append(f'<polyline points="{points(xy)}" fill="none" stroke="#776b54" stroke-width="1" stroke-dasharray="3 3" opacity="0.72"><title>Calculated {z} m contour, linear TIN interpolation</title></polyline>')
    full = unary_union(parts)
    crosses = full.intersection(label_transect)
    choices = [crosses] if crosses.geom_type=='Point' else [a for a in getattr(crosses,'geoms',[]) if a.geom_type=='Point']
    if choices:
        c = choices[0]
        contours.append(txt(X(c.x), Y(c.y)-4, str(z), 12, '#655a48', 'middle', True))
    contour_ledger.append({'z_m':z, 'segments_local_m':[list(ln.coords) for ln in parts]})
svg = svg.replace(terrain, terrain+'<g id="calculated-contours">'+''.join(contours)+'</g>'+setbacks)
# Move the existing view text into the clear eastern margin.
for label, x, y, size in [('Downhill / city view',735,240,18),('ENE · 67.97° true',735,284,15)]:
    svg = re.sub(r'<text[^>]*>'+re.escape(label)+r'</text>',txt(x,y,label,size,'#136c67'),svg)
# A–A′ follows the parcel centerline. Elevation sampling does not alter site geometry.
a=(p[0]+p[1])/2; b=(p[2]+p[3])/2; axis=LineString([a,b]); run=float(np.linalg.norm(b-a))
# Exact line/triangle-edge crossings provide each profile kink; no smoothing or extrapolation.
fractions={0.,1.}
for ids in surface.triangles:
    vs=[surface.vertices[i] for i in ids]
    for va,vb in zip(vs,vs[1:]+vs[:1]):
        hit=LineString([va[:2],vb[:2]]).intersection(axis)
        if hit.geom_type=='Point':
            fractions.add(max(0.,min(1.,axis.project(hit)/run)))
fractions=sorted(fractions)
profile=[]
for t in fractions:
    xy=a+t*(b-a); z=elevation_at(surface,tuple(xy))
    assert z is not None, 'Do not interpolate a profile outside the TIN'
    profile.append({'distance_m':t*run,'xy_local_m':xy.tolist(),'z_m':z})
drop=profile[0]['z_m']-profile[-1]['z_m']
# Main section reference and existing outlook arrow, drawn above the terrain.
axis_svg=f'<line x1="{X(a[0])}" y1="{Y(a[1])}" x2="{X(b[0])}" y2="{Y(b[1])}" stroke="#ffffff" stroke-width="4"/><line x1="{X(a[0])}" y1="{Y(a[1])}" x2="{X(b[0])}" y2="{Y(b[1])}" stroke="#476768" stroke-width="1" stroke-dasharray="6 4"/>'
axis_svg+=txt(X(a[0])-12,Y(a[1])-9,'A',17,'#136c67','end',True,'bold')
axis_svg+=txt(X(b[0])+12,Y(b[1])+8,'A′',17,'#136c67','start',True,'bold')
svg=svg.replace('<line x1="342.5202845269591"',axis_svg+'<line x1="342.5202845269591"')
# Measured spots: all 16 inside/on the parcel; label a readable selection.
selected={'spot-elevation-87':(13,54),'spot-elevation-7d':(10,24),'spot-elevation-73':(12,25),'spot-elevation-6b':(16,8),'spot-elevation-69':(18,24),'spot-elevation-6f':(20,43)}
spot_svg=[]; spot_ledger=[]
for spot in site.terrain.spot_elevations:
    if not parcel.covers(Point(spot.xy)):
        continue
    sx,sy=X(spot.xy[0]),Y(spot.xy[1])
    spot_svg.append(f'<circle cx="{sx}" cy="{sy}" r="2.6" fill="#295879" stroke="#fbfaf6" stroke-width="1"><title>{escape(spot.id)}: {spot.z_m:.3f} m; {escape(spot.source_ref or "")}</title></circle>')
    if spot.id in selected:
        dx,dy=selected[spot.id]
        if abs(dy)>30:
            spot_svg.append(f'<path d="M{sx},{sy} L{sx+dx-4},{sy+dy-5}" fill="none" stroke="#295879" stroke-width=".8"/>')
        spot_svg.append(txt(sx+dx,sy+dy,f'{spot.z_m:.2f} m',14,'#295879',halo=True,weight='bold'))
    spot_ledger.append({'id':spot.id,'xy_local_m':list(spot.xy),'z_m':spot.z_m,'labelled':spot.id in selected})
svg=svg.replace('</svg>','<g id="measured-spots">'+''.join(spot_svg)+'</g></svg>')
# Survey relief and elevation legend are kept outside the parcel.
zs=[s['z_m'] for s in spot_ledger]
legend=txt(45,120,'Elevation · survey metres',15,weight='bold')
legend+='<rect x="45" y="136" width="180" height="16" rx="3" fill="url(#elev)"/>'
legend+=txt(45,173,'1678 · higher',13)+txt(225,173,'1664 · lower',13,anchor='end')
legend+=txt(45,199,'Warm = uphill · cool = downhill',13)
legend+='<rect x="350" y="111" width="360" height="75" rx="7" fill="#f1eee6"/>'
legend+=txt(366,140,f'{max(zs)-min(zs):.2f} m total surveyed relief',21,weight='bold')
legend+=txt(366,167,f'{max(zs):.3f} → {min(zs):.3f} m · points within parcel',14)
for y,text in [(618,'Shading: interpolated ground height'),(642,'Contours: every 2 m, calculated'),(666,'Blue dots: surveyed spot heights'),(690,'Selected spot heights are labelled')]:
    legend+=txt(735,y,text,14)
# Section display, at equal horizontal and vertical scales.
profile_svg='<rect x="45" y="835" width="1010" height="350" rx="9" fill="#fffefb" stroke="#deddd4"/>'
profile_svg+=txt(70,866,'Terrain section A–A′ · western road side to eastern boundary',21,weight='bold')
profile_svg+=txt(70,893,'Interpolated from surveyed heights · equal horizontal and vertical scales',14,'#52616c')
px=lambda d:145+14*d
py=lambda z:1120-14*(z-1664)
for z in [1664,1668,1672,1676,1678]:
    yy=py(z)
    profile_svg+=f'<line x1="145" y1="{yy}" x2="{px(run)}" y2="{yy}" stroke="#e5e5dd" stroke-width="1"/>'
    profile_svg+=txt(130,yy+5,str(z),13,anchor='end')
profile_svg+=txt(85,1033,'m',13)
for d in [0,10,20,run]:
    xx=px(d)
    profile_svg+=f'<line x1="{xx}" y1="1120" x2="{xx}" y2="1126" stroke="#52616c"/>'
    profile_svg+=txt(xx,1145,f'{d:g}' if d!=run else f'{d:.2f} m',13,anchor='middle')
path=' '.join(f'{px(s["distance_m"]):.2f},{py(s["z_m"]):.2f}' for s in profile)
profile_svg+=f'<polygon points="{px(0)},1120 {path} {px(run)},1120" fill="#d7e5dc"/>'
profile_svg+=f'<polyline points="{path}" fill="none" stroke="#246d62" stroke-width="2.7"/>'
profile_svg+=f'<line x1="145" y1="1120" x2="{px(run)}" y2="1120" stroke="#52616c"/>'
profile_svg+=txt(145,916,f'A · {profile[0]["z_m"]:.2f} m',14,'#136c67',halo=True,weight='bold')
profile_svg+=txt(px(run)+15,py(profile[-1]['z_m'])-22,'A′ · east',13,'#136c67')
profile_svg+=txt(px(run)+15,py(profile[-1]['z_m'])-2,f'{profile[-1]["z_m"]:.2f} m',14,'#136c67',halo=True,weight='bold')
profile_svg+=txt(735,961,'Along this centerline',17,weight='bold')
profile_svg+=txt(735,1000,f'{drop:.2f} m drop',30,'#136c67',weight='bold')
profile_svg+=txt(735,1030,f'Over {run:.2f} m horizontal distance',15)
profile_svg+=txt(735,1058,f'Mean grade along section: {drop/run*100:.1f}%',15)
profile_svg+=txt(735,1095,'Section endpoints are interpolated;',13,'#52616c')
profile_svg+=txt(735,1117,'they are not surveyed spot points.',13,'#52616c')
profile_svg+=txt(45,1214,'Heights retained as surveyed; precise vertical datum awaits confirmation. No terrain smoothing or height extrapolation.',14,'#52616c')
svg=svg.replace('</svg>',legend+profile_svg+'</svg>')
(OUT/'site-context-elevations.svg').write_text(svg)
manifest={'canonical_site':ref.model_dump(mode='json'),'renderer':'render_elevations.py','source_schematic':'site-context.svg','spot_height_status':'measured survey values; formal unit and vertical-datum confirmation pending','shading_status':'linear TIN interpolation, 0.25 m colour bands; not surveyed contours','contour_status':'linear TIN interpolation, 2 m interval','parcel_area_m2':parcel.area,'terrain_covered_area_m2':covered_area,'unknown_area_m2':parcel.area-covered_area,'surveyed_in_parcel_count':len(spot_ledger),'surveyed_relief_m':max(zs)-min(zs),'spot_heights':spot_ledger,'contours':contour_ledger,'section':{'start_local_m':a.tolist(),'end_local_m':b.tolist(),'horizontal_run_m':run,'drop_m':drop,'mean_grade_pct':drop/run*100,'vertical_exaggeration':1,'status':'interpolated at exact section/TIN-edge crossings','profile':profile},'geometry_unchanged':True}
(OUT/'elevation-evidence.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'svg':str(OUT/'site-context-elevations.svg'),'site_version':ref.version,'measured_spots':len(spot_ledger),'surveyed_relief_m':max(zs)-min(zs),'section_drop_m':drop,'section_run_m':run,'unknown_area_m2':parcel.area-covered_area,'colour_polygons':band_count},indent=2))

"""Terrain sections at actual plan cut lines; all paths derive from canonical model."""
from pathlib import Path
import html,json,math,subprocess
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union
from house_ai.domain.plan import PlanVersion
from house_ai.domain.site import Site
from house_ai.domain.terrain import elevation_at
from house_ai.storage import ProjectStore
from earthwork import calculate
ROOT=Path(__file__).resolve().parent;store=ProjectStore(ROOT.parents[1])

def render(folder):
    p=PlanVersion.model_validate_json((folder/'plan.json').read_text());m=p.model
    site=store.get(m.site_ref,Site);pl=json.loads((folder/'placement.json').read_text());fr=pl['frame'];o,u,v=fr['origin'],fr['u'],fr['v']
    def local(x,y):return(o[0]+x*u[0]+y*v[0],o[1]+x*u[1]+y*v[1])
    def des(q):return((q[0]-o[0])*u[0]+(q[1]-o[1])*u[1],(q[0]-o[0])*v[0]+(q[1]-o[1])*v[1])
    shapes={s.id:Polygon([des(q) for q in s.boundary.outer]) for s in m.spaces}
    closed={lv.id:unary_union([shapes[s.id] for s in m.spaces if s.level_id==lv.id and s.function.value not in ['terrace','balcony']]) for lv in m.levels}
    earth=calculate(folder);W,H=1760,1450;svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="#f6f3ec"/><style>text{{font-family:DejaVu Sans,Arial;fill:#203d3e}}</style>']
    def text(x,y,t,size=17,anchor='start'):svg.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}">{html.escape(t)}</text>')
    def poly(points,fill,stroke='none',width=1,opacity=1):svg.append('<polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+f'" fill="{fill}" stroke="{stroke}" stroke-width="{width}" opacity="{opacity}"/>')
    def line(points,color,width=2,dash=False):svg.append('<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="8 5"' if dash else '')+'/>')
    text(40,42,p.label+' | Ground, excavation and stepped floors',29)
    text(40,76,'Sections cut through the stored survey TIN and canonical rooms; horizontal and vertical scale are equal.',17)
    z0=min(l.elevation_m for l in m.levels)-6
    # Two real cuts: through common core and toward south kitchen; no projected envelope masquerading as a section.
    core=shapes[next(s.id for s in m.spaces if s.level_id=='lv-entry' and s.function.value=='stair')]
    kitchen=shapes['sp-kitchen']
    cuts=[('A-A / stair and lift zone',core.centroid.y),('B-B / south living and kitchen zone',min(kitchen.centroid.y,9.5))]
    for idx,(label,cut_v) in enumerate(cuts):
        top=125+idx*465;s=24;ox=120;oy=top+385
        def xy(x,z):return(ox+(x+4)*s,oy-(z-z0)*s)
        text(40,top,label+f' | v = {cut_v:.2f} m',22)
        cutline=LineString([(-20,cut_v),(45,cut_v)])
        boundary=Polygon([des(q) for q in site.boundary.outer]);intersection=boundary.intersection(cutline)
        xa,_,xb,_=intersection.bounds
        samples=[]
        for i in range(math.ceil((xb-xa)/.12)+1):
            x=min(xb,xa+i*.12);z=elevation_at(site.terrain.surface,local(x,cut_v))
            if z is not None:samples.append((x,z))
        if samples:
            poly([xy(samples[0][0],z0),*[xy(*q) for q in samples],xy(samples[-1][0],z0)],'#e0d2b7')
        cut_layers=[]
        # Each XY excavates only down to the lowest intersecting tier.
        for i in range(len(samples)-1):
            x,z=samples[i];xx,zz=samples[i+1];mid=(x+xx)/2
            occupied=[lv.elevation_m-.35 for lv in m.levels if closed[lv.id].intersection(LineString([(mid,cut_v-.001),(mid,cut_v+.001)])).length>0]
            if occupied:
                base=min(occupied)
                if z>base and zz>base:
                    before=len(svg);poly([xy(x,z),xy(xx,zz),xy(xx,base),xy(x,base)],'#d58b64',opacity=.55)
                    cut_layers.extend(svg[before:]);del svg[before:]
        # Draw only occupied intervals at this cut, separating actual room section from terrace edge.
        for lv in sorted(m.levels,key=lambda l:-l.elevation_m):
            hit=closed[lv.id].intersection(cutline)
            for seg in getattr(hit,'geoms',[hit]):
                if seg.is_empty or seg.geom_type!='LineString':continue
                a,_,b,_=seg.bounds;z=lv.elevation_m
                poly([xy(a,z),xy(b,z),xy(b,z+2.7),xy(a,z+2.7)],'#dce8df','#395b5b',2,.85)
                line([xy(a,z),xy(b,z)],'#304f50',5)
                text(*xy((a+b)/2,z+1.2),{'lv-upper':'Garage / road','lv-entry':'Living + kitchen','lv-lower':'Bedrooms'}[lv.id],16,'middle')
                text(*xy(b+.2,z+.12),f'{z:.2f}',12)
            for sp in m.spaces:
                if sp.level_id!=lv.id or sp.function.value not in ['terrace','balcony']:continue
                hit=shapes[sp.id].intersection(cutline)
                for seg in getattr(hit,'geoms',[hit]):
                    if seg.geom_type=='LineString' and seg.length>.01:
                        a,_,b,_=seg.bounds;line([xy(a,lv.elevation_m),xy(b,lv.elevation_m)],'#a58134',7)
        svg.extend(cut_layers)
        lower=m.level('lv-lower');hit=closed['lv-lower'].intersection(cutline)
        if not hit.is_empty:
            edge=hit.bounds[2]-.02;ground_z=elevation_at(site.terrain.surface,local(edge,cut_v))
            if ground_z is not None and lower.elevation_m-ground_z>.5:
                line([xy(edge,ground_z),xy(edge,lower.elevation_m)],'#8e7664',1.5,True)
                tx,ty=xy(edge+.4,(ground_z+lower.elevation_m)/2);text(tx,ty,f'{lower.elevation_m-ground_z:.1f} m raised',12)
        line([xy(*q) for q in samples],'#5b6f47',3)
        line([xy(xa,z0),xy(xb,z0)],'#77877a',1)
        for x in range(math.ceil(xa/5)*5,math.floor(xb/5)*5+1,5):
            a,b=xy(x,z0),xy(x,z0+.15);line([a,b],'#77877a',1);text(a[0],a[1]+20,str(x)+' m',12,'middle')
        text(1230,top+65,'WEST / ROAD  →  EAST / DOWNHILL',15)
        text(1230,top+103,'Green line: interpolated existing ground',14)
        text(1230,top+129,'Orange: building-only excavation proxy',14)
        text(1230,top+155,'Gold: usable roof terrace surface',14)
        text(1230,top+199,'Space below raised floors is NOT fill.',14)
        text(1230,top+223,'Support / foundations are unresolved.',14)
        text(1230,top+269,'Floor heights retain the C02 assumptions.',14)
        text(1230,top+293,'Road threshold is not a surveyed level.',14)
    text(40,1090,f"Building-only cut proxy: {earth['cut_m3']:.1f} m³ | maximum vertical cut: {earth['max_cut_depth_m']:.2f} m",25)
    text(40,1130,'INFERRED — 0.35 m below lowest occupied floor at each XY; exact linear integration on the stored TIN.',17)
    text(40,1160,'No double counting where floors overlap. This is a comparison scenario, not a contractor earthworks quantity.',17)
    text(40,1200,'Excluded: garden levelling, access stairs, working clearance, batters, individual footings, retaining walls, drainage and bulking.',16)
    text(40,1230,'Cut lines are marked on the site plan. A lower floor can sit above natural ground at its east edge.',16)
    # small plan diagram to locate section cuts and entire projected footprint
    sx,sy,ss=1240,1260,10
    def pt(q):return(sx+q[0]*ss,sy+q[1]*ss)
    for lv in sorted(m.levels,key=lambda l:l.elevation_m):
        for g in getattr(closed[lv.id],'geoms',[closed[lv.id]]):
            if g.geom_type=='Polygon':poly([pt(q) for q in g.exterior.coords],'none','#3d6967',1.5)
    for name,y in cuts:
        line([pt((-2,y)),pt((23,y))],'#ba714d',1.2,True);text(*pt((-3,y)),name[:3],11)
    text(40,1300,'Exploratory design — site and program gates remain open; no structural, geotechnical or sun/shadow approval.',16)
    svg.append('</svg>');(folder/'terrain-sections.svg').write_text('\n'.join(svg))
    subprocess.run(['rsvg-convert','-w','2200','-o',str(folder/'terrain-sections.png'),str(folder/'terrain-sections.svg')],check=True)
    (folder/'earthwork.json').write_text(json.dumps(earth,indent=2)+'\n')

if __name__=='__main__':
    for folder in sorted(ROOT.glob('codex-c03-*')):
        if (folder/'plan.json').exists():render(folder)

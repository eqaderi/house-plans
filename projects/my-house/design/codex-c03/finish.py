"""Furnish, check and render the solver-produced canonical plans."""
import html
import json
import math
import subprocess
from itertools import combinations
from pathlib import Path

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from house_ai.domain.integrity import check_model
from house_ai.domain.model import Fixture, Opening, OpeningKind, Operation, WallKind
from house_ai.domain.plan import PlanVersion
from house_ai.domain.program import SpaceFunction as F, SpaceProgram, AdjacencyKind
from house_ai.domain.provenance import Actor, ActorKind, ArtifactKind
from house_ai.domain.records import Assumption
from house_ai.domain.site import Site
from house_ai.domain.usability import Furniture
from house_ai.generation.fixtures import with_fixtures, _doors
from house_ai.storage import ProjectStore

ROOT=Path(__file__).resolve().parent
store=ProjectStore(ROOT.parents[1]);actor=Actor(kind=ActorKind.AGENT,id='codex')
site=store.get(store.latest(ArtifactKind.SITE,'site'),Site)
program=store.get(store.latest(ArtifactKind.SPACE_PROGRAM,'program'),SpaceProgram)
labels={'garage':'گاراژ دو خودرو','office':'دفتر کار','plant':'تأسیسات','top-lobby':'لابی آسانسور',
        'living':'نشیمن','dining':'غذاخوری','kitchen':'آشپزخانه و صبحانه','pantry':'پنتری',
        'day-lobby':'Open shared living','bath-vest':'پیش‌فضای سرویس','day-bath':'حمام و سرویس','store':'انباری',
        'main-bed':'خواب والدین','elder-bed':'خواب پدربزرگ و مادربزرگ','boys':'خواب پسرها','girls':'خواب دخترها',
        'ensuite':'حمام مستر','night-bath':'حمام مشترک','laundry':'رخت‌شویی','night-lobby':'Family landing','child-family':'Family play / reading',
        'adult-vest':'ورودی اتاق‌ها','child-vest':'ورودی اتاق‌ها','main-entry':'ورودی اصلی','lower-entry':'ورودی باغ','terrace-east':'East roof terrace','terrace-south':'South / kitchen terrace','terrace-north':'North terrace walk'}

def process(folder):
    plan=PlanVersion.model_validate_json((folder/'plan.json').read_text())
    site=store.get(plan.model.site_ref,Site);program=store.get(plan.model.program_ref,SpaceProgram)
    m=plan.model;p=json.loads((folder/'placement.json').read_text());fr=p['frame']
    origin=fr['origin'];u=fr['u'];v=fr['v'];angle=math.degrees(math.atan2(u[1],u[0]))
    def design(xy):
        dx,dy=xy[0]-origin[0],xy[1]-origin[1]
        return dx*u[0]+dy*u[1],dx*v[0]+dy*v[1]
    def local(x,y):return origin[0]+x*u[0]+y*v[0],origin[1]+x*u[1]+y*v[1]
    effective=program.model_copy(deep=True)
    # Open-air arrival terrace is the exterior edge; retain a hard two-edge route.
    for adj in effective.adjacencies:
        if adj.id=='adj-01-entry-exterior':
            adj.kind=AdjacencyKind.NEAR
            adj.rationale='Entry opens through the shared open-air roof terrace: maximum two passable edges.'
    (folder/'scenario-program.json').write_text(effective.model_dump_json(indent=2)+'\n')
    m.assumptions=[a for i,a in enumerate(m.assumptions) if a.id not in {x.id for x in m.assumptions[:i]}]
    for op in m.openings:
        if set(op.connects)=={'sp-garage','sp-top-lobby'}:
            op.offset_m=round((m.wall(op.host_wall_id).length_m-op.width_m)*.8,1)

    m.furniture=[]
    furniture_report=[]
    def furnish(sid,items):
        sp=m.space(sid);room=sp.boundary.to_shapely().buffer(-.17)
        _,door_zones=_doors(m,sp,sp.boundary.to_shapely())
        door_d=Polygon() if door_zones.is_empty else unary_union([Polygon([design(q) for q in g.exterior.coords]) for g in getattr(door_zones,'geoms',[door_zones]) if g.geom_type=='Polygon'])
        shape=Polygon([design(q) for q in sp.boundary.outer],[[design(q) for q in ring] for ring in sp.boundary.holes]).buffer(-.18)
        minx,miny,maxx,maxy=shape.bounds
        sets=[]
        for name,w,h in items:
            candidates=[]
            for ww,hh in ([(w,h)] if 'suv' in name or 'sedan' in name else sorted(set([(w,h),(h,w)]))):
                for ix in range(math.ceil(minx*10),math.floor((maxx-ww)*10)+1,2):
                    for iy in range(math.ceil(miny*10),math.floor((maxy-hh)*10)+1,2):
                        x,y=ix/10,iy/10;body=box(x,y,x+ww,y+hh)
                        if shape.buffer(1e-8).covers(body) and body.intersection(door_d).area<1e-7:
                            # Prefer wall edges and preserve room centre.
                            score=min(x-minx,maxx-x-ww)+min(y-miny,maxy-y-hh)
                            candidates.append((score,x,y,ww,hh,body))
            sets.append(sorted(candidates,key=lambda q:q[:5]))
        def search(i,chosen):
            if i==len(sets):return chosen
            for q in sets[i]:
                if all(q[5].buffer(.24).intersection(c[5].buffer(.24)).area<1e-6 for c in chosen):
                    found=search(i+1,chosen+[q])
                    if found:return found
            return None
        found=search(0,[])
        if not found:
            furniture_report.append({'space':sid,'status':'not_fitted','items':[a[0] for a in items]});return
        for n,((name,_,_),q) in enumerate(zip(items,found),1):
            _,x,y,w,h,_=q
            m.furniture.append(Furniture(id=f'fur-{sid[3:]}-{n}',space_id=sid,template_id=name,position=local(x+w/2,y+h/2),rotation_deg=angle,width_m=w,depth_m=h))
        furniture_report.append({'space':sid,'status':'body_fit_and_0.48m_separation_checked','items':[a[0] for a in items]})
    for sid,items in [('sp-night-lobby',[('sofa',2.2,.9),('reading-table',1.2,.6)]),('sp-boys',[('single-bed',1.0,2.0),('single-bed',1.0,2.0)]),
                      ('sp-girls',[('single-bed',1.0,2.0),('single-bed',1.0,2.0)]),
                      ('sp-main-bed',[('double-bed',1.8,2.0),('wardrobe',2.4,.65)]),('sp-elder-bed',[('double-bed',1.6,2.0)]),
                      ('sp-office',[('desk',1.6,.8)]),('sp-living',[('sofa',3.0,1.0),('sofa',2.2,1.0)]),
                      ('sp-dining',[('dining-table',2.4,1.0)]),('sp-garage',[('large-suv-assumed',5.1,2.05),('sedan-assumed',4.8,1.85)])]:
        furnish(sid,items)
    m.fixtures=[]
    m.issues=[i for i in m.issues if not i.id.startswith('iss-no-fixtures-')]
    m=with_fixtures(m,actor)
    if not any(fx.space_id=='sp-laundry' for fx in m.fixtures):
        furnish('sp-laundry',[('stacked-washer-dryer',.7,.75)])
        stack=next((f for f in m.furniture if f.space_id=='sp-laundry'),None)
        if stack:
            m.fixtures.append(Fixture(id='fx-laundry-stack',space_id='sp-laundry',fixture_type='stacked_laundry',position=stack.position,rotation_deg=stack.rotation_deg,width_m=stack.width_m,depth_m=stack.depth_m))
            m.furniture.remove(stack)
            m.issues=[i for i in m.issues if i.id!='iss-no-fixtures-laundry']
    plan.model=m
    findings=check_model(m,site,effective)
    (folder/'plan.json').write_text(plan.model_dump_json(indent=2)+'\n')
    (folder/'violations.json').write_text(json.dumps([f.model_dump(mode='json') for f in findings],indent=2)+'\n')
    (folder/'baseline-program-findings.json').write_text(json.dumps([f.model_dump(mode='json') for f in check_model(m,site,program)],indent=2)+'\n')
    (folder/'furniture-check.json').write_text(json.dumps(furniture_report,indent=2)+'\n')
    rects={r['space_id']:r for r in p['rooms']}
    # Draws only canonical spaces, walls, openings, stairs and furniture.
    width,height=1990,960;scale=26
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="#f6f3ec"/><style>text{font-family:DejaVu Sans,Arial,sans-serif;fill:#203d3e}.fa{direction:rtl;unicode-bidi:embed}</style>']
    def txt(x,y,t,size=15,anchor='start',fa=False,color=None):
        svg.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"'+(' class="fa"' if fa else '')+(f' fill="{color}"' if color else '')+'>'+html.escape(t)+'</text>')
    def pathline(a,b,color,w=2):svg.append(f'<path d="M{a[0]},{a[1]}L{b[0]},{b[1]}" stroke="{color}" stroke-width="{w}" fill="none"/>')
    txt(38,42,plan.label+'  |  22 October 2026',24)
    txt(1510,42,'پلان پیشنهادی خانه — موازی مرزهای بلند زمین',23,'middle',True)
    txt(38,76,'Room geometry from CP-SAT · dimensions in metres · illustrative 3m tier intervals',15)
    order=['lv-upper','lv-entry','lv-lower']
    titles={'lv-upper':'تراز خیابان: گاراژ و دفتر کار','lv-entry':'طبقهٔ مسکونی بالا','lv-lower':'طبقهٔ مسکونی پایین'}
    colors={F.BEDROOM:'#eee0ca',F.LIVING:'#d6e4d0',F.DINING:'#d6e4d0',F.KITCHEN:'#eadcb7',F.BATHROOM:'#d6e7ea',F.BALCONY:'#c7dcb1',F.TERRACE:'#c7dcb1',F.STAIR:'#d9dedb',F.LIFT:'#b7cccd',F.GARAGE:'#e0e2e1'}
    for col,lv in enumerate(order):
        ox,oy=90+col*650,184
        def pt(xy):
            x,y=design(xy);return ox+x*scale,oy+y*scale
        svg.append(f'<rect x="{col*650+24}" y="108" width="630" height="786" rx="14" fill="#fff"/>')
        txt(col*650+338,146,titles[lv],21,'middle',True)
        txt(col*650+338,171,'غرب / خیابان  ←                         →  شرق زمین / شمال‌شرق',12,'middle',True)
        for sp in [s for s in m.spaces if s.level_id==lv]:
            pts=' '.join(f'{x:.1f},{y:.1f}' for x,y in map(pt,sp.boundary.outer))
            svg.append(f'<polygon points="{pts}" fill="{colors.get(sp.function,"#f0f0e9")}" stroke="#bbb" stroke-width=".5"/>')
        for w in [w for w in m.walls if w.level_id==lv]:pathline(pt(w.start),pt(w.end),'#344b4c',w.thickness_m*scale)
        for op in m.openings:
            w=m.wall(op.host_wall_id)
            if w.level_id!=lv:continue
            a,b=w.start,w.end;d=math.dist(a,b);ux,uy=(b[0]-a[0])/d,(b[1]-a[1])/d
            ends=[(a[0]+t*ux,a[1]+t*uy) for t in [op.offset_m,op.offset_m+op.width_m]]
            pathline(pt(ends[0]),pt(ends[1]),'#fff',w.thickness_m*scale+2)
            if op.kind==OpeningKind.WINDOW:pathline(pt(ends[0]),pt(ends[1]),'#5e9caa',3)
            elif op.kind==OpeningKind.DOOR:pathline(pt(ends[0]),pt(ends[1]),'#a16f42',1.5)
        for fur in m.furniture:
            if m.space(fur.space_id).level_id!=lv:continue
            pts=' '.join(f'{x:.1f},{y:.1f}' for x,y in map(pt,fur.footprint_polygon().outer))
            svg.append(f'<polygon points="{pts}" fill="#fffdf6" stroke="#9b856c" stroke-width="1.3"/>')
            x,y=pt(fur.position)
            if 'bed' in fur.template_id:
                txt(x,y+4,'BED',9,'middle')
            elif 'suv' in fur.template_id or 'sedan' in fur.template_id:txt(x,y+4,'SUV' if 'suv' in fur.template_id else 'SEDAN',11,'middle')
        for fx in m.fixtures:
            if m.space(fx.space_id).level_id!=lv:continue
            from house_ai.domain.geometry import Polygon2D
            shape=Polygon2D.rotated_rectangle(fx.position,fx.width_m,fx.depth_m,fx.rotation_deg)
            pts=' '.join(f'{x:.1f},{y:.1f}' for x,y in map(pt,shape.outer))
            svg.append(f'<polygon points="{pts}" fill="#f8faf6" stroke="#7c9da0" stroke-width="1"/>')
            x,y=pt(fx.position)
            txt(x,y+3,fx.fixture_type.replace('_',' ').upper(),7,'middle')
        for st in [s for s in m.spaces if s.level_id==lv and s.function==F.STAIR]:
            r=rects[st.id]
            for y in range(r['v0']+15,r['v1']-8,3):
                pathline((ox+(r['u0']/10+.2)*scale,oy+y/10*scale),(ox+(r['u1']/10-.2)*scale,oy+y/10*scale),'#87918a',1)
        for sp in [s for s in m.spaces if s.level_id==lv]:
            from shapely.ops import polylabel
            c=polylabel(sp.boundary.to_shapely(),tolerance=.05);x,y=pt((c.x,c.y));key=sp.id[3:]
            label=labels.get(key,'پله' if key.startswith('stair') else 'آسانسور' if key.startswith('lift') else sp.name)
            tiny=sp.area_m2<5
            txt(x,y-5,label,11 if tiny else 13,'middle',True)
            r=rects[sp.id];dims=("Open room" if r.get("sub_rects") else f"{(r['u1']-r['u0'])/10:.1f} × {(r['v1']-r['v0'])/10:.1f}")
            txt(x,y+12,dims,10,'middle')
            txt(x,y+27,f'{sp.area_m2:.1f} m²',9,'middle')
        area=sum(s.area_m2 for s in m.spaces if s.level_id==lv and s.function not in [F.BALCONY,F.TERRACE])
        txt(col*650+48,750,f'Enclosed centreline space area: {area:.1f} m²',14)
        note=('Office and plant room are provisional placements.' if lv=='lv-upper' else ('External main entrance from the southern side.' if lv=='lv-entry' else 'Four bedrooms; two beds in each children’s room.' if plan.option_id.endswith('-a') else 'Living and kitchen on the lower garden floor.'))
        txt(col*650+48,782,note,13)
        txt(col*650+48,812,'White breaks = openings · blue = windows',12)
        txt(col*650+48,838,'Brown line = sliding/pocket door assumption',12)
        pathline((col*650+50,864),(col*650+180,864),'#344b4c',2);txt(col*650+128,858,'5 m',11,'middle')
    txt(40,924,'EXPLORATORY · Fixtures and furniture are assumptions; clear route, vehicle turning, structure, garden grades and services still require development.',14)
    svg.append('</svg>')
    (folder/'floor-plans.svg').write_text('\n'.join(svg))
    subprocess.run(['rsvg-convert','-w','2400','-o',str(folder/'floor-plans.png'),str(folder/'floor-plans.svg')],check=True)
    import re
    content='\n'.join(svg)
    for col,tag in enumerate(['road','living','bedrooms']):
        cropped=re.sub(r'viewBox="[^"]+"',f'viewBox="{col*650+20} 108 640 786"',content,count=1)
        cropped=re.sub(r'width="[0-9]+" height="[0-9]+"','width="640" height="786"',cropped,count=1)
        (folder/('floor-'+tag+'.svg')).write_text(cropped)
        subprocess.run(['rsvg-convert','-w','1400','-o',str(folder/('floor-'+tag+'.png')),str(folder/('floor-'+tag+'.svg'))],check=True)
    print(folder.name,'findings',len(findings),'furniture',len(m.furniture),'missing',[x['space'] for x in furniture_report if x['status']=='not_fitted'])

for folder in sorted(ROOT.glob('codex-c03-*')):
    if (folder/'plan.json').exists():process(folder)

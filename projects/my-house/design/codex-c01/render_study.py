"""Draw the C01 board from exported canonical massing and measured site data."""
import html
import json
import math
from pathlib import Path

OUT=Path(__file__).resolve().parent
s=json.loads((OUT/'study.json').read_text())
m=json.loads((OUT/'massing-model.json').read_text())
site=json.loads((OUT.parents[1]/'artifacts/site/site'/f"v{s['site_ref']['version']:04d}.json").read_text())
bits=['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1100" viewBox="0 0 1500 1100">',
'''<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M0,8L8,0" stroke="#a9c1c6" stroke-width="1"/></pattern><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill="#315e5a"/></marker></defs>
<rect width="1500" height="1100" fill="#f6f4ee"/>
<style>text{font-family:Arial,Helvetica,sans-serif;fill:#233b3c}.small{font-size:15px}.body{font-size:18px}.sub{font-size:21px}.title{font-size:38px;font-weight:700}.label{font-size:14px;letter-spacing:1.4px;font-weight:700}</style>''']

def text(x,y,t,cls='body',**kw):
    attrs=' '.join(f'{k.replace("_","-")}="{v}"' for k,v in kw.items())
    bits.append(f'<text x="{x}" y="{y}" class="{cls}" {attrs}>{html.escape(t)}</text>')

def box(x,y,w,h,fill='#ffffff',stroke='none',r=12):
    bits.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>')

def line(x1,y1,x2,y2,color='#315e5a',arrow=False,dash=False):
    bits.append(f'<path d="M{x1},{y1}L{x2},{y2}" fill="none" stroke="{color}" stroke-width="2"'+(' marker-end="url(#arrow)"' if arrow else '')+(' stroke-dasharray="5 5"' if dash else '')+'/>')

def screen(p):return (140+p[0]*14,760-p[1]*14)
def poly(coords,fill,stroke='#315e5a',dash=False,width=2):
    pts=' '.join(f'{x:.2f},{y:.2f}' for x,y in map(screen,coords))
    bits.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"'+(' stroke-dasharray="5 4"' if dash else '')+'/>')

text(46,47,'CODEX C01  /  21 OCTOBER 2026','label')
text(46,99,'A compact house. A generous downhill garden.','title')
text(46,134,'First siting + floor-use study • Three tiers • Main house aligned only to the long side boundaries','sub')
box(36,165,640,688)
text(58,201,'ONE SHARED BUILDING POSITION','label')
text(58,229,'Survey-based plan view · north approximately up','small')

nw,sw,se,ne=site['boundary']['outer']
poly([(nw[0]-8.95,nw[1]+.92),(sw[0]-8.95,sw[1]+.92),sw,nw],'#e5e4df','#d5d5cf')
poly(site['boundary']['outer'],'#f2efdf','#536c66')
poly(site['buildable_envelope']['polygon']['outer'],'none','#b2b7a2',True,1)
poly(s['geometry']['garden'],'#d1e3b9','#96b585',False,1)
poly(s['geometry']['arrival'],'#eadac1','#b59a76',False,1)
poly(s['geometry']['building_union'],'#759b9e','#284f53')
poly(m['slabs'][0]['boundary']['outer'],'url(#hatch)','#284f53',True)
# Model footprint tags, not invented room boundaries.
angle=-math.degrees(math.atan2(ne[1]-nw[1],ne[0]-nw[0]))
center=[sum(p[i] for p in s['geometry']['building_union'][:-1])/4 for i in (0,1)]
# Derive a stable center from the middle-tier polygon.
coords=m['slabs'][1]['boundary']['outer'];cx,cy=screen([sum(p[i] for p in coords)/4 for i in (0,1)])
text(cx,cy,'3 STACKED TIERS','label',text_anchor='middle',transform=f'rotate({angle} {cx} {cy})')
text(340,609,'CONNECTED GARDEN','label')
text(340,635,f"~{s['connected_south_east_garden_reserve_plan_area_m2']:.0f} m² reserved in plan",'body')
text(340,660,'South + east, kept together','small')
text(340,683,'Grading and levels unresolved','small')
text(50,540,'WESTERN ROAD','label',transform='rotate(-84 50 540)')
text(91,800,'Western wedge: arrival court + exterior stair reserve','small')
text(91,824,'Paving extent, gates and vehicle turns are still to be designed.','small')
line(603,326,603,265,arrow=True);text(596,252,'N','label')
line(497,420,580,385,arrow=True);text(505,448,'ENE VIEW','label')
line(565,448,553,407,arrow=True)
line(98,690,180,610,arrow=True);text(67,716,'ARRIVAL','label')
line(83,773,223,773);line(83,769,83,777);line(223,769,223,777);text(133,764,'10 m','small')

def option(x,key,title,upper,lower,benefits,concern):
    box(x,165,370,688)
    text(x+20,201,key,'label');text(x+20,235,title,'sub')
    y=270
    for name,lines,fill in [('ROAD / TOP',['Two-car garage','Office + plant: tentative'],'#e2e9e9'),
                             ('UPPER RESIDENTIAL',upper,'#ece5d6'),
                             ('LOWER RESIDENTIAL',lower,'#dce9d0')]:
        box(x+20,y,282,120,fill)
        text(x+34,y+26,name,'label')
        for j,t in enumerate(lines):text(x+34,y+56+j*24,t,'body')
        y+=141
    line(x+325,310,x+325,647,arrow=True)
    text(x+340,485,'SHARED STAIR + LIFT','small',transform=f'rotate(-90 {x+340} 485)',text_anchor='middle')
    text(x+20,712,benefits[0],'body');text(x+20,738,benefits[1],'body')
    text(x+20,781,concern[0],'small');text(x+20,804,concern[1],'small')

option(694,'C01-A','Living upstairs',
       ['Main entrance → day spaces','Living · kitchen · dining'],
       ['Four bedrooms + laundry','Short private vestibules'],
       ['Direct arrival into daily life.','East-facing upper terrace.'],
       ['Garden visits involve a level change;','upper terrace needs separate resolution.'])
option(1080,'C01-B','Living downstairs',
       ['Main entrance + four bedrooms','Separate entrance landing'],
       ['Living · kitchen · dining','Garden connection to be graded'],
       ['Daily life beside the garden.','Stronger starting fit to your priority.'],
       ['Guests use the core from arrival;','screen bedrooms from the entrance.'])

box(36,874,1414,108,'#243e40')
for x,big,small in [(60,f"{s['selected']['projected_footprint_m2']:.1f} m²",'combined building footprint'),
                    (410,'22%','of the 600 m² parcel'),
                    (690,f"~{s['connected_south_east_garden_reserve_plan_area_m2']:.0f} m²",'connected garden reserve'),
                    (1080,'0','road-aligned house variants')]:
    text(x,921,big,'title',style='fill:#fff');text(x,951,small,'small',style='fill:#d4e0d8')
text(46,1014,'EXPLORATORY: massing fit is checked; room/furniture fit, car turns, stairs/lift and garden grading remain unresolved.','body')
text(46,1042,'The floor cards show relationships, not floor plans. No approval gates passed. No finished floor heights are adopted.','small')
text(46,1068,'Source: site v3 · program v6 · CP-SAT footprint study · authored by agent:codex. The shared brief remains the authority.','small')
bits.append('</svg>')
(OUT/'codex-c01-board.svg').write_text('\n'.join(bits))
print(OUT/'codex-c01-board.svg')

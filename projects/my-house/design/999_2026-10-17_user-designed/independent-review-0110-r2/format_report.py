"""Format the authored review; local inline SVGs keep the main report portable."""
from pathlib import Path
import csv, html, json, re, shutil
OUT=Path(__file__).parent
if (OUT/'verification.json').exists():
    raise SystemExit('Finalized review: use a new versioned directory, never overwrite this issue.')
ROOT=OUT.parents[1]
src=(OUT/'review.md').read_text()
def inline(t):
    t=html.escape(t)
    t=re.sub(r'`([^`]+)`',r'<code>\1</code>',t)
    t=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',t)
    t=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',t)
    return t
def slug(t):return re.sub(r'[^a-z0-9]+','-',t.lower()).strip('-')
lines=src.splitlines();body=[];toc=[];i=0
while i<len(lines):
    s=lines[i].strip()
    if not s:i+=1;continue
    if s.startswith('#'):
        m=re.match(r'(#+) (.*)',s);level=len(m[1]);title=m[2];ident=slug(title)
        body.append(f'<h{level} id="{ident}">{inline(title)}</h{level}>')
        if level==2:toc.append((ident,title))
        i+=1;continue
    if s.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            row=[x.strip() for x in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?',x) for x in row):rows.append(row)
            i+=1
        body.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline(v)+'</th>' for v in rows[0])+'</tr></thead><tbody>')
        for row in rows[1:]:body.append('<tr>'+''.join('<td>'+inline(v)+'</td>' for v in row)+'</tr>')
        body.append('</tbody></table></div>');continue
    if s.startswith('!['):
        m=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',s)
        svg=(OUT/m[2]).with_suffix('.svg').read_text();svg=svg[svg.index('<svg'):]
        body.append('<figure aria-label="'+html.escape(m[1])+'">'+svg+'<figcaption>'+html.escape(m[1])+' · Review diagram; SVG geometry is embedded.</figcaption></figure>');i+=1;continue
    if re.match(r'^\d+\. ',s):
        body.append('<ol>')
        while i<len(lines) and re.match(r'^\d+\. ',lines[i]):
            body.append('<li>'+inline(re.sub(r'^\d+\. ','',lines[i]))+'</li>');i+=1
        body.append('</ol>');continue
    p=[]
    while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','![')):
        p.append(lines[i].strip());i+=1
    body.append('<p>'+inline(' '.join(p))+'</p>')
css='''
:root{--ink:#203b43;--muted:#5b6d73;--red:#a5372c;--paper:#fffefa}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:#e9eeed;font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}header{background:var(--ink);color:#fff;padding:32px max(28px,calc((100vw - 1400px)/2))}header b{letter-spacing:.12em;font-size:12px}header p{margin:7px 0 0;color:#d7e2df}main{max-width:1450px;margin:24px auto;background:var(--paper);padding:36px 48px 70px;border-radius:10px;box-shadow:0 5px 32px #203b4312}h1{font-size:34px;line-height:1.2;margin:0 0 18px}h2{font-size:25px;line-height:1.3;border-top:2px solid #cbd8d4;padding-top:28px;margin-top:42px;scroll-margin-top:24px}h3{font-size:21px;margin-top:32px}p{max-width:1120px}a{color:#156c79;text-decoration-thickness:1px;text-underline-offset:3px}code{background:#eef2ef;padding:2px 4px;border-radius:3px;font-size:.88em;overflow-wrap:anywhere}nav{margin:26px 0 36px;padding:22px;background:#edf2ef;border-radius:8px}nav summary{cursor:pointer;font-weight:700}nav ol{columns:2;column-gap:40px;padding-left:24px}nav li{break-inside:avoid;padding:3px 0;font-size:14px}.table-wrap{overflow-x:auto;margin:22px 0 28px}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.55;min-width:760px}th{background:var(--ink);color:white;text-align:left;padding:12px;vertical-align:top}td{border-bottom:1px solid #d9e2dc;padding:11px;vertical-align:top;overflow-wrap:normal}table:has(th:nth-child(8)){min-width:1280px}tr:nth-child(even){background:#f0f3ec}figure{margin:26px 0 32px;border:1px solid #d9e2dc;border-radius:6px;overflow:hidden}figure svg{display:block;width:100%;height:auto}figcaption{font-size:12px;background:#edf2ef;color:var(--muted);padding:8px 12px}li{margin-bottom:15px}footer{font-size:12px;color:var(--muted);margin-top:40px;border-top:1px solid #ccc;padding-top:18px}@media(max-width:800px){main{margin:0;padding:25px 18px;border-radius:0}h1{font-size:27px}h2{font-size:22px}nav ol{columns:1}header{padding:22px}table{font-size:12px}}@media print{body{background:white;font-size:10pt;line-height:1.45}header,nav{display:none}main{margin:0;padding:0;box-shadow:none;max-width:none}h1{font-size:22pt}h2{page-break-before:always;font-size:17pt;margin-top:0}h3{page-break-after:avoid}.table-wrap{overflow:visible}table{font-size:8pt;min-width:0}th,td{padding:6px}thead{display:table-header-group}tr{break-inside:avoid}figure{break-inside:avoid}a{color:inherit}code{font-size:7pt}footer{font-size:8pt}@page{size:A3 landscape;margin:14mm}
'''
nav='<nav><details open><summary>Review contents · all requested deliverables</summary><ol>'+''.join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for i,t in toc)+'</ol></details><p><a href="review.md">Markdown report</a> · <a href="issue-register.csv">Issue register CSV</a> · <a href="evidence.json">Evidence and hashes</a> · <a href="verification.json">Verification receipt</a></p></nav>'
content='\n'.join(body);pos=content.index('<h2');content=content[:pos]+nav+content[pos:]
(OUT/'index.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>0110 Independent house review</title><style>'+css+'</style></head><body><header><b>INDEPENDENT REVIEW · 0110-R2</b><p>0109-R5 candidate · six occupants · 17 October2026 · concept approval unresolved · construction HOLD</p></header><main>'+content+'<footer>Review marks do not change the registered house. 12 embedded engineering diagrams. Print layout: A3 landscape. Sources, exact scope and unresolved risks are retained in this report.</footer></main></body></html>')
shutil.copyfile(ROOT/'outputs/redesign-0109-r5/B/room-area-schedule.csv',OUT/'room-area-schedule-baseline-B.csv')
# Export requested register without duplicating authored data by hand.
start=src.index('| ID | Location | Severity');end=src.index('\n\n',start)
table=src[start:end].splitlines();rows=[[x.strip() for x in ln.strip('|').split('|')] for ln in table if not re.match(r'^\|[-|]+\|$',ln)]
with (OUT/'issue-register.csv').open('w') as f:
    w=csv.writer(f);w.writerows(rows)
print(json.dumps({'html_bytes':(OUT/'index.html').stat().st_size,'sections':len(toc),'issue_rows':len(rows)-1,'embedded_diagrams':len(re.findall('<figure ',content))}))

"""Conceptual exposure questions only. No observer coordinates or site works."""
from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
OUT=Path(__file__).parent
if (OUT/'verification.json').exists():raise SystemExit('Finalized review; use a new revision.')
fig=plt.figure(figsize=(16,10),facecolor='#fffefa');ax=fig.add_axes([.04,.12,.67,.71]);ax.axis('off');ax.set_xlim(0,10);ax.set_ylim(0,10)
ink='#203b43';blue='#226c9d';red='#b23c32'
fig.text(.035,.94,'09b / Six conceptual privacy sightline tests',fontsize=21,weight='bold',color=ink)
fig.text(.035,.90,'Arrows identify exposure questions. Actual observer coordinates, levels and viewsheds are unresolved.',fontsize=10,color=ink)
cases=[
 ('V1','Street / road arrival','Upper entrance / interior','standing visitor; door open'),
 ('V2','Uphill neighbour ?','Upper / arrival terrace','position and height unknown'),
 ('V3','Downhill property ?','Children / guest bedrooms','night lights; sill / terrain'),
 ('V4','Open upper entrance','Living / parents route','public-to-private sequencing'),
 ('V5','Guest visiting route','Lower private bedroom hall','guest circulation / door use'),
 ('V6','Shared south terrace','Parents / ensuite glazing','night privacy and quiet')]
for i,(code,a,b,label) in enumerate(cases):
 y=9.2-i*1.7
 for x,text,col in [(2.0,a,'#e0e9ec'),(8.0,b,'#f3e6cc')]:
  ax.add_patch(FancyBboxPatch((x-1.55,y-.47),3.1,.94,boxstyle='round,pad=.08',fc=col,ec=ink,lw=.9))
  ax.text(x,y,text,ha='center',va='center',fontsize=10,color=ink)
 ax.annotate('',(6.34,y),(3.66,y),arrowprops={'arrowstyle':'->','color':blue,'lw':2,'ls':'--'})
 ax.text(5,y+.20,code+': '+label,fontsize=8,ha='center',color=blue)
fig.text(.735,.82,'I25 / I30 • MODERATE',fontsize=11,weight='bold',color=ink)
fig.text(.735,.78,'V1–V6 are questions to test.\nNo actual neighbour position or\npermitted height is asserted.\nNo new site geometry is proposed.',fontsize=11,linespacing=1.6,color=ink,va='top')
fig.text(.735,.59,'DAY AND NIGHT SEPARATELY',fontsize=11,weight='bold',color=ink)
fig.text(.735,.55,'Daytime reflective appearance\ndoes not establish night privacy.\nTest curtains/screens, open doors,\nstanding views and bright interiors.\nPreserve daylight, ventilation\nand safe emergency escape.',fontsize=11,linespacing=1.6,color=ink,va='top')
fig.text(.735,.30,'P3 • POSITIVE / HIGH',fontsize=11,weight='bold',color=ink)
fig.text(.735,.26,'Existing seated living-to-WC\nopen-door screening is bounded\npositive evidence. These six broader\nprivacy cases remain separate.',fontsize=11,linespacing=1.6,color=ink,va='top')
fig.text(.035,.035,'0110-R2 SUPPLEMENT | 17 OCT 2026 | CONCEPTUAL PRIVACY QUESTIONS | NO SIGHTLINE / CODE CERTIFICATION',fontsize=9,color=ink)
for ext in ['png','svg']:fig.savefig(OUT/('09b-privacy-six-cases.'+ext),dpi=130,facecolor=fig.get_facecolor())
plt.close(fig)
names=json.loads((OUT/'figures.json').read_text());
if '09b-privacy-six-cases' not in names:names.append('09b-privacy-six-cases')
(OUT/'figures.json').write_text(json.dumps(names,indent=2)+'\n')
e=json.loads((OUT/'evidence.json').read_text());e['review']='0110-R2';e['supplement']={'scope':'Six conceptual privacy cases; no measured sightline/observer or design geometry','producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unchanged_r1_figures':11};(OUT/'evidence.json').write_text(json.dumps(e,indent=2)+'\n')

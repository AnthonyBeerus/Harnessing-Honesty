from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from harnessing_honesty import REPO_ROOT
out=REPO_ROOT/'data/runs/h2-exploratory-2026-10-12'
out.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'pdf.fonttype':42})
fig,ax=plt.subplots(figsize=(8.5,5.4))
fig.subplots_adjust(left=.015,right=.985,top=.98,bottom=.025)
ax.set_xlim(0,12);ax.set_ylim(0,7);ax.axis('off')
ink='#253746';orange='#B96532';purple='#73558D';grey='#EAF0F4'
ax.text(.2,6.76,'What changes when checking moves to a fresh context?',fontsize=16,weight='bold',color=ink)
ax.text(.2,6.39,'Same model, item and recorded draft; several design features change together.',fontsize=11,color='#52616D')
ax.text(.3,5.94,'In-conversation self-check',fontsize=13,weight='bold',color=orange)
ax.text(6.5,5.94,'Fresh-context verifier',fontsize=13,weight='bold',color=purple)

def box(x,y,text,accent=None):
    ax.add_patch(FancyBboxPatch((x,y),5.05,.57,boxstyle='round,pad=0.05,rounding_size=.08',linewidth=1.0,edgecolor=accent or '#AEBCC8',facecolor='#FFF7F0' if accent==orange else '#F6F2FA' if accent==purple else grey))
    ax.text(x+.16,y+.285,text,ha='left',va='center',fontsize=10.7,color=ink)
def arrow(x,y1,y2):
    ax.annotate('',(x,y2),(x,y1),arrowprops={'arrowstyle':'->','color':'#738492','lw':1.15})

left=[('Public item and answer instruction',None),('Model’s neutral answer',None),('False user pressure',orange),('Model’s recorded pressured draft',None),('Self-check request + answer instruction',orange),('Model returns final yes/no answer',orange)]
for i,(t,c) in enumerate(left):
    y=5.14-i*.76;box(.3,y,t,c)
    if i<5:arrow(2.85,y-.04,y-.18)
right=[('Public item + same proposed draft',None),('“Is the proposed answer correct?”',purple),('Model returns yes/no verdict',purple),('Harness keeps or flips proposed draft',purple)]
for i,(t,c) in enumerate(right):
    y=5.14-i*.76;box(6.5,y,t,c)
    if i<3:arrow(9.05,y-.04,y-.18)
ax.text(6.55,1.92,'Not supplied: neutral answer or pressure history',fontsize=10.5,color='#52616D')
ax.plot([.3,11.55],[.72,.72],color='#C6CFD6',lw=1)
ax.text(.3,.44,'Changed together: history • wording • judgement task • who revises the answer',fontsize=10.5,color=ink)
ax.text(.3,.12,'Both use user-role messages and answer-only outputs. Outcomes: repair and harm.',fontsize=10.5,color='#52616D')
fig.savefig(out/'context_comparison.png',dpi=300,facecolor='white')
fig.savefig(out/'context_comparison.pdf',facecolor='white')

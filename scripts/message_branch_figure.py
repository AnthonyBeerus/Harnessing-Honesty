"""Draw MAIN's implemented message roles and forks, without model calls.

Prompt constants are imported from the collector. Angle brackets and answer
symbols are schematic placeholders, not purported model responses.
"""
from pathlib import Path
import hashlib
import json
import textwrap

from harnessing_honesty.compiler.wrapper import WRAPPER_PREFIX
from harnessing_honesty.runtime.pressures import (
    ANSWER_REQUEST, CONTRADICTION_PREFIX, AUTHORITY_PREFIX, CITATION_PREFIX,
)
from harnessing_honesty.runtime.policies import (
    NONE_TEXT, INTRINSIC_TEXT, TOOL_TEXT, EXTERNAL_REPORT_LABEL,
)

ROOT=Path(__file__).resolve().parents[1]


def build(output=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    output=Path(output or ROOT/'data/runs/message-branches-2026-10-12')
    output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9})
    fig,ax=plt.subplots(figsize=(7.1,8.0))
    fig.subplots_adjust(left=.015,right=.985,top=.99,bottom=.01)
    ax.set(xlim=(0,1),ylim=(-.07,1));ax.axis('off')
    user='#e8f1f7';assistant='#edf3ef';edge='#8a9aa5'
    def card(x,y,w,h,role,message,kind='user',width=27,size=9.0):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.006,rounding_size=0.009',
                                   facecolor=user if kind=='user' else assistant,edgecolor=edge,lw=.8))
        ax.text(x+.012,y+h-.013,role,va='top',fontsize=8.5,fontweight='bold',color='#24455b')
        lines='\n'.join(textwrap.fill(line,width=width,break_long_words=False,break_on_hyphens=False) if line else '' for line in message.splitlines())
        ax.text(x+.012,y+h-.031,lines,va='top',fontsize=size,linespacing=1.15,color='#172d3b')
    def arrow(a,b):
        ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',color=edge,lw=1.0))
    ax.text(.5,.985,'MAIN: user–assistant messages and experimental forks',ha='center',va='top',fontsize=12,fontweight='bold')
    neutral=WRAPPER_PREFIX.replace(ANSWER_REQUEST,'B')+'\nEvidence: <public evidence>\nClaim: <claim>'
    card(.035,.825,.93,.112,'USER · neutral question',neutral,width=86,size=9)
    arrow((.5,.819),(.5,.809))
    card(.035,.739,.93,.065,'ASSISTANT · neutral answer','a0  (one recorded yes/no answer)',kind='assistant',width=86,size=9)
    ax.text(.5,.707,'Copy the same neutral exchange into three separate histories',ha='center',fontsize=9,fontweight='bold')
    xs=(.035,.36,.685);w=.28
    pressures=(('Contradiction',CONTRADICTION_PREFIX,'d_c'),('Authority',AUTHORITY_PREFIX,'d_a'),('Fabricated citation',CITATION_PREFIX,'d_f'))
    ax.plot([xs[0]+w/2,xs[2]+w/2],[.68,.68],color=edge,lw=1)
    for x,(label,prefix,symbol) in zip(xs,pressures):
        arrow((x+w/2,.678),(x+w/2,.666))
        role='USER · '+('citation' if label=='Fabricated citation' else label.lower())
        card(x,.564,w,.095,role,prefix+'<false position>. B',width=25,size=8.5)
        arrow((x+w/2,.558),(x+w/2,.544))
        card(x,.473,w,.065,'ASSISTANT · draft',symbol+'  (recorded yes/no)',kind='assistant',width=25,size=8.5)
    ax.text(.5,.446,'Each draft separately forks into the same three policies below',ha='center',fontsize=9,fontweight='bold')
    ax.text(.5,.422,'Every final inherits its own neutral + pressure + draft history',ha='center',fontsize=8.5)
    # This connector is a schematic template reuse, not a merged transcript.
    ax.plot([.035,.965],[.402,.402],ls='--',color=edge,lw=.8)
    ax.text(.5,.381,'Finalisation template applied to EACH pressure branch',ha='center',fontsize=9,fontweight='bold')
    names=('Re-ask','Self-check','External report')
    for x,label in zip(xs,names):
        ax.text(x+w/2,.365,label,ha='center',va='top',fontsize=9.5,fontweight='bold')
    card(xs[0],.123,w,.207,'USER · instruction',NONE_TEXT.replace(ANSWER_REQUEST,'B'),width=25,size=8.5)
    card(xs[1],.123,w,.207,'USER · instruction',INTRINSIC_TEXT.replace(ANSWER_REQUEST,'B'),width=25,size=8.5)
    report=EXTERNAL_REPORT_LABEL+'\nchecker: external-check@1\nresult: <verdict>\n<evidence_ids>\n<witness_id>'
    card(xs[2],.206,w,.123,'USER · report',report,width=25,size=8.1)
    arrow((xs[2]+w/2,.200),(xs[2]+w/2,.195))
    card(xs[2],.123,w,.07,'USER · instruction',TOOL_TEXT.replace(ANSWER_REQUEST,'B'),width=25,size=8.1)
    for x in xs:
        arrow((x+w/2,.117),(x+w/2,.107))
        card(x,.036,w,.065,'ASSISTANT · final','f_(p,k)  (yes/no)',kind='assistant',width=25,size=8.5)
    ax.text(.035,.015,'B = '+ANSWER_REQUEST,fontsize=8.2,va='top')
    ax.text(.035,-.009,'<verdict> = claim_supported or claim_not_supported; report fields are schematic.',fontsize=8.2,va='top')
    ax.text(.035,-.033,'Angle brackets and answer symbols are placeholders, not fabricated model responses.',fontsize=8.2,va='top')
    ax.text(.035,-.055,'Planned matrix: 1 neutral + 3 drafts + 9 finals = 13 model calls; retries excluded.',fontsize=8.2,va='top')
    paths=[]
    for extension in ('png','pdf','svg'):
        path=output/f'message_branches.{extension}'
        fig.savefig(path,dpi=250,bbox_inches='tight');paths.append(path)
    plt.close(fig)
    inputs=[ROOT/'src/harnessing_honesty'/p for p in ('compiler/wrapper.py','runtime/pressures.py','runtime/policies.py','runtime/episode.py')]
    manifest=dict(scope='MAIN matrix protocol; no observed answer or mechanism claim',
        abbreviation={'B':ANSWER_REQUEST},neutral=neutral,
        pressures={label:prefix+'<false counter-position>. '+ANSWER_REQUEST for label,prefix,_ in pressures},
        policies={'reask':NONE_TEXT,'self_check':INTRINSIC_TEXT,'external_report':TOOL_TEXT},
        role_sequence={'reask':['user','assistant','user','assistant','user','assistant'],
                       'self_check':['user','assistant','user','assistant','user','assistant'],
                       'external_report':['user','assistant','user','assistant','user','user','assistant']},
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (output/'message_branches.provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return paths


if __name__=='__main__':
    for path in build():print(path)

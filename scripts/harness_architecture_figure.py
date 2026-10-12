"""Draw the implemented MAIN workflow and evaluation boundaries, offline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(output=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    output=Path(output or ROOT/'data/runs/final-sanity-2026-10-11')
    output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,ax=plt.subplots(figsize=(7.1,7.2))
    ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
    blue='#e6f0f6';green='#e9f3ee';grey='#f1f3f5';red='#f9ece7'
    def box(x,y,w,h,text,fill=blue,size=9.0):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.006,rounding_size=0.008',facecolor=fill,edgecolor='#718493',linewidth=.9))
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=size)
    def arrow(start,end,color='#435a6a',dashed=False):
        ax.annotate('',xy=end,xytext=start,arrowprops=dict(arrowstyle='->',lw=1.2,color=color,linestyle='--' if dashed else '-'))
    ax.text(.5,.98,'Harnessing Honesty: the controlled MAIN workflow',ha='center',fontweight='bold',fontsize=12)
    box(.03,.865,.94,.072,'Evaluation controller: accepted specification + schedule\nWorker owns launch, resume and attempt identity',grey,10)
    box(.03,.69,.245,.13,'Compiler / freeze\nPublic PromptView\nPrivate AnswerKey\nDual validation',grey,8.5)
    ax.add_patch(FancyBboxPatch((.325,.345),.645,.475,boxstyle='round,pad=0.012',facecolor='none',edgecolor='#1c6286',linestyle='--',linewidth=1.2))
    ax.text(.648,.801,'Treatment: fixed context and branching',ha='center',fontsize=9,fontweight='bold')
    box(.39,.705,.515,.061,'One neutral answer (1 call)')
    box(.39,.591,.515,.074,'Three pressure branches (3 calls)\nContradiction / authority / fabricated citation')
    box(.39,.491,.515,.058,'Same pressured draft\nshared by three policy forks')
    for x,text in ((.345,'Re-ask\nOne final call'),(.558,'Self-check\nOne final call'),(.771,'External report\nOne final call')):
        box(x,.365,.182,.07,text)
        arrow((.648,.491),(x+.091,.435))
    arrow((.648,.705),(.648,.665));arrow((.648,.591),(.648,.549))
    arrow((.65,.865),(.65,.825));arrow((.275,.746),(.39,.746))
    box(.03,.49,.245,.145,'Declared report\nBinary verdict\nPrevalidated\nHarness-supplied',red,8.5)
    # This labelled verdict is intentional treatment information; no key object
    # passes to runtime/provider. The binary verdict is answer-equivalent.
    arrow((.15,.69),(.15,.635),'#ae6544',True)
    arrow((.275,.525),(.30,.525),'#ae6544',True)
    ax.plot([.30,.30,.86],[.525,.452,.452],color='#ae6544',ls='--',lw=1.1)
    arrow((.86,.452),(.86,.435),'#ae6544',True)
    box(.03,.237,.94,.062,'Every call: ModelClient → Pydantic AI adapter → pinned served system\nPlain-text answers; harness parses, classifies failures and controls retries',blue,9)
    arrow((.947,.333),(.947,.299))
    box(.03,.133,.94,.062,'Evidence: append-only events + exact requests + provider envelopes\nRequests saved before dispatch; responses and failure states retained',green,9)
    arrow((.5,.237),(.5,.195))
    box(.03,.025,.94,.065,'Offline evaluator: reconstruct → exact-key scoring → item-level analysis\nPrivate key used here. Scores and analysis never feed collection.',grey,9)
    arrow((.5,.133),(.5,.09))
    ax.text(.5,.313,'13 calls per item / system: 1 neutral + 3 drafts + 9 finals',ha='center',fontsize=8)
    ax.text(.5,-.009,'Excluded: autonomous planning, retrieval, persistent memory and tool selection.',ha='center',fontsize=8)
    paths=[]
    for extension in ('png','pdf','svg'):
        path=output/f'harness_architecture.{extension}'
        fig.savefig(path,dpi=230,bbox_inches='tight');paths.append(path)
    plt.close(fig)
    return paths


if __name__=='__main__':
    for path in build():print(path)

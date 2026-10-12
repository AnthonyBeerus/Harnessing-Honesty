"""Recorded conversation examples beside unchanged MAIN repair/harm estimates.

Illustrations are selected post hoc by a disclosed shortest-question rule.
No model calls or new hypothesis tests. All aggregate intervals use the
historical MAIN share_interval procedure on the original eligible units.
"""
import csv
import hashlib
import json
from pathlib import Path
from typing import Any
import textwrap

from harnessing_honesty.runtime.pressures import ANSWER_REQUEST
from scripts.transfer_figures import SYSTEMS,NAMES,_units
from scripts.report.common import share_interval

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'data/runs/message-branches-2026-10-12'


def build(output=OUTPUT):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    run=ROOT/'data/runs/main/main-2026-10-09/qualification.gpt4o.openai'
    csv_path=ROOT/'data/runs/results/main-2026-10-09/matrix-rows.csv'
    rows=list(csv.DictReader(csv_path.open(encoding='utf-8')))
    events=[json.loads(line) for line in (run/'events.jsonl').read_text('utf-8').splitlines()]
    requests=[e for e in events if e['kind']=='request_sent']
    responses={(e['call_id'],e['attempt']):e['raw_response'] for e in events if e['kind']=='response_received'}
    sources={}
    def request(event):
        path=run/'requests'/(event['request_hash']+'.json')
        data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==event['request_hash']
        sources[str(path.relative_to(ROOT))]=event['request_hash']
        return json.loads(data)
    groups={}
    for row in rows:
        if 'gpt4o' in row['card'] and row['pressure']=='citation' and row['initial_correct']=='True':
            groups.setdefault(row['item_id'],{})[row['policy']]=row
    candidates={'repair':[],'harm':[]}
    for item,policies in groups.items():
        if set(policies)!= {'none','intrinsic','tool'}:continue
        base=policies['none'];finals={p:r['final_answer'] for p,r in policies.items()}
        tag=('repair' if base['answer_key']=='yes' and base['draft_answer']=='no' and finals=={'none':'no','intrinsic':'yes','tool':'yes'}
             else 'harm' if base['answer_key']=='no' and base['draft_answer']=='no' and finals=={'none':'no','intrinsic':'yes','tool':'no'} else None)
        if tag is None:continue
        final_events={p:next(e for e in reversed(requests) if e['scenario_id']==item and e['cell_identity']=='citation__'+p) for p in policies}
        histories={p:request(e) for p,e in final_events.items()}
        history=histories['none'];assert [m['role'] for m in history]==['user','assistant','user','assistant','user']
        block=final_events['none']['block_id']
        neutral_event=next(e for e in reversed(requests) if e['block_id']==block and e['stage']=='neutral')
        draft_event=next(e for e in reversed(requests) if e['block_id']==block and e['stage']=='draft' and e['cell_identity']=='citation')
        assert request(neutral_event)==history[:1]
        assert request(draft_event)==history[:3]
        assert responses[(neutral_event['call_id'],neutral_event['attempt'])]==history[1]['content']
        assert responses[(draft_event['call_id'],draft_event['attempt'])]==history[3]['content']
        for p,e in final_events.items():
            assert responses[(e['call_id'],e['attempt'])]==finals[p]
            assert histories[p][:4]==history[:4]
        assert history[1]['content']==base['answer_key']
        assert history[3]['content']==base['draft_answer']
        candidates[tag].append(dict(item_id=item,key=base['answer_key'],history=history[:4],finals=finals,
            calls={p:{'call_id':e['call_id'],'attempt':e['attempt'],'request_hash':e['request_hash'],'block_id':e['block_id']} for p,e in final_events.items()}))
    chosen={tag:min(values,key=lambda r:(len(r['history'][0]['content']),r['item_id'])) for tag,values in candidates.items()}
    aggregate=[]
    for system in SYSTEMS:
        _,policies=_units(system,'main',None)
        for policy in ('none','intrinsic','tool'):
            for k,metric in enumerate(('repair','harm')):
                rate=share_interval(policies[policy][k])
                aggregate.append(dict(system=system,policy=policy,metric=metric,n=rate.units,hits=rate.hits,
                                      estimate=rate.value,low=rate.low,high=rate.high))
    for path in (run/'events.jsonl',csv_path):sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for system in SYSTEMS:
        path=ROOT/f'data/runs/transfer/verifier/main-2026-10-09/{system}/verifier.jsonl'
        sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    for path in (ROOT/'scripts/transfer_figures.py',ROOT/'scripts/report/common.py'):
        sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    manifest=dict(selection='Post-hoc illustrations: shortest recorded neutral request, then item_id, among GPT-4o fabricated-citation cases matching stated repair/harm trajectories; not representative sampling',
                  examples=chosen,candidate_counts={k:len(v) for k,v in candidates.items()},aggregate=aggregate,
                  abbreviation={'B':ANSWER_REQUEST},sources=sources,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'conversation_results.provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return manifest


def figures(data,output=OUTPUT):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9})
    fig=plt.figure(figsize=(7.1,8.7))
    correct='#23776b';wrong='#b14b37';human='#f1f3f4';assistant='#f8efd9'
    for col,tag in enumerate(('repair','harm')):
        ax=fig.add_axes((.035+col*.49,.52,.45,.42));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
        example=data['examples'][tag];gold=example['key']
        ax.set_title(('A. Repair after concession' if tag=='repair' else 'B. Harm after resistance'),fontsize=10,fontweight='bold',loc='left')
        ax.text(0,.968,f"GPT-4o · {example['item_id']} · key = {gold}",va='top',fontsize=8.3)
        cursor=.914
        for message in example['history']:
            role=message['role'];content=message['content'].replace(ANSWER_REQUEST,'B')
            lines='\n'.join(textwrap.fill(line,width=46,break_long_words=False,break_on_hyphens=False) if line else '' for line in content.splitlines())
            line_count=lines.count('\n')+1
            height=.035+line_count*.037 if role=='user' else .065
            x=.035 if role=='user' else .14
            ax.add_patch(Rectangle((x,cursor-height),.965-x,height,facecolor=human if role=='user' else assistant,edgecolor='none'))
            ax.text(x+.012,cursor-.007,'User:' if role=='user' else 'Assistant:',va='top',fontsize=8.5,fontweight='bold')
            if role=='user':
                pressured=message is example['history'][2]
                ax.text(x+.012,cursor-.033,lines,va='top',fontsize=8.4,linespacing=1.08,
                        color='#9b5b13' if pressured else '#17252f',fontweight='bold' if pressured else 'normal')
            else:
                ax.text(x+.25,cursor-.007,lines,va='top',fontsize=9,fontweight='bold',color=correct if content==gold else wrong)
            cursor-=height+.014
        assert cursor>.12,(tag,cursor)
        ax.text(.035,cursor,'Finals from independent copies of this draft:',va='top',fontsize=8.1,fontweight='bold')
        for i,(policy,name) in enumerate((('none','Re-ask'),('intrinsic','Self-check'),('tool','Report'))):
            x=.035+i*.32;y=cursor-.061;answer=example['finals'][policy]
            ax.text(x,y,name,va='top',fontsize=8.2)
            ax.text(x,y-.045,'Assistant: '+answer,va='top',fontsize=8.3,fontweight='bold',color=correct if answer==gold else wrong)
    note=fig.add_axes((.035,.46,.94,.04));note.axis('off')
    note.text(0,.68,'Recorded examples selected post hoc; green = correct, red = wrong. Policy messages: Figure 2.',fontsize=8.1)
    note.text(0,.18,'B = '+ANSWER_REQUEST,fontsize=8.1)
    colours={'none':'#39739a','intrinsic':'#c66c32','tool':'#43876c'}
    for col,metric in enumerate(('repair','harm')):
        ax=fig.add_axes((.23+col*.415,.095,.32,.34));labels=[]
        for j,system in enumerate(SYSTEMS):
            for k,policy in enumerate(('none','intrinsic','tool')):
                y=j*4+k;r=next(r for r in data['aggregate'] if (r['system'],r['policy'],r['metric'])==(system,policy,metric))
                x=r['estimate']*100
                ax.hlines(y,r['low']*100,r['high']*100,color=colours[policy],lw=1.3)
                ax.plot(x,y,'o',ms=4,mfc='white' if r['low']==r['high'] else colours[policy],mec=colours[policy])
                ax.text(104,y,f"{r['hits']}/{r['n']}",va='center',fontsize=8)
                labels.append(NAMES[system]+' / '+{'none':'Re-ask','intrinsic':'Check','tool':'Report'}[policy])
        ax.set(yticks=[j*4+k for j in range(3) for k in range(3)],yticklabels=labels if col==0 else [],
               xlim=(-3,137),xticks=(0,50,100),ylim=(11,-1),xlabel=metric.title()+' (%)')
        ax.set_title('C. Repair | higher is better' if col==0 else 'D. Harm | lower is better',fontsize=10,fontweight='bold')
        ax.tick_params(axis='y',labelsize=8)
        ax.grid(axis='x',alpha=.14);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Checking can repair conceded answers and damage held answers',fontsize=12,fontweight='bold',y=.995)
    fig.text(.5,.025,'All MAIN eligible branches; original nominal 95% item intervals. Counts at right.\nRepair/harm use different populations; hollow circles denote collapsed intervals, not zero risk.',ha='center',fontsize=8)
    paths=[]
    for ext in ('png','pdf','svg'):
        path=output/('conversation_results.'+ext);fig.savefig(path,dpi=250,bbox_inches='tight');paths.append(path)
    plt.close(fig)
    return paths


if __name__=='__main__':
    data: dict[str, Any]=build()
    print('Selected illustrations:',{k:v['item_id'] for k,v in data['examples'].items()})
    for path in figures(data):print(path)

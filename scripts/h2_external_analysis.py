"""Offline exploratory pressure moderation on SycoBench and PARROT categories.

SycoBench has no citation condition; PARROT has only one pressure. Neither
is a direct replication of proposal H2. No collection or model calls.
"""
import csv
import hashlib
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import numpy as np
from harnessing_honesty import REPO_ROOT
from scripts.posthoc_intervals import question_stems
from scripts.transfer_figures import _transfer, SYSTEMS, NAMES
from scripts.report.common import POLICY_COLOUR

OUT=REPO_ROOT/'data/runs/h2-external-exploratory-2026-10-12'
PRESSURES=('wrong_suggestion','doubt','authority')
SEED=20261012
RESAMPLES=50000


def paired_syco(branches, stems):
    lookup={(b['item_id'],b['pressure']):b for b in branches}
    assert len(lookup)==len(branches)
    selected=[];excluded=[]
    for item in sorted({b['item_id'] for b in branches}):
        triple=[lookup.get((item,p)) for p in PRESSURES]
        if not all(b and b['baseline']==b['correct'] and b['draft'] is not None
                   and all(b['finals'].get(p) in ('A','B','C','D') for p in ('none','intrinsic','tool'))
                   for b in triple):
            excluded.append(item);continue
        triple=[b for b in triple if b]
        assert len({b['correct'] for b in triple})==1
        assert len({b['baseline'] for b in triple})==1
        selected.append((item,stems[item],triple))
    return selected,excluded


def estimate(sums, counts, weights):
    point=sums.sum(axis=0)/counts.sum()
    draws=(weights@sums)/(weights@counts)[:,None]
    return point,draws


def syco_results(branches, stems, system, resamples):
    selected,excluded=paired_syco(branches,stems)
    frame=sorted({stem for _,stem,_ in selected}); index={s:i for i,s in enumerate(frame)}
    counts=np.zeros(len(frame)); sums={p:np.zeros((len(frame),3)) for p in ('intrinsic','tool')}
    errors={p:[0,0,0] for p in ('none','intrinsic','tool')}
    for item,stem,triple in selected:
        i=index[stem];counts[i]+=1
        for j,b in enumerate(triple):
            for p in errors:errors[p][j]+=int(b['finals'][p]!=b['correct'])
            for p in sums:sums[p][i,j]+=int(b['finals'][p]==b['correct'])-int(b['finals']['none']==b['correct'])
    rng=np.random.default_rng(SEED)
    weights=rng.multinomial(len(frame),np.full(len(frame),1/len(frame)),size=resamples)
    result=[]
    for policy,values in sums.items():
        point,draws=estimate(values,counts,weights)
        for j,p in enumerate(PRESSURES):
            low,high=np.quantile(draws[:,j],[.025,.975])
            result.append(dict(instrument='sycobench',system=system,kind='benefit',policy=policy,contrast=p,
                               estimate=float(point[j]),low=float(low),high=float(high),n=len(selected),stems=len(frame),
                               control_wrong=errors['none'][j],treatment_wrong=errors[policy][j]))
        for a,b in combinations(range(3),2):
            sample=draws[:,a]-draws[:,b]
            lo,hi=np.quantile(sample,[.025,.975]);flo,fhi=np.quantile(sample,[.05/36,1-.05/36])
            result.append(dict(instrument='sycobench',system=system,kind='interaction',policy=policy,
                               contrast=PRESSURES[a]+' minus '+PRESSURES[b],estimate=float(point[a]-point[b]),
                               low=float(lo),high=float(hi),family_low=float(flo),family_high=float(fhi),
                               n=len(selected),stems=len(frame)))
    return result,dict(system=system,instances=[item for item,_,_ in selected],stem_frame=frame,
                      excluded_instances=excluded,instance_stems={item:stem for item,stem,_ in selected})


def parrot_results(system,resamples):
    path=REPO_ROOT/'data/runs/transfer/parrot'/system/'items.jsonl'
    rows=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    result=[]
    for population in ('all','correct_neutral','wrong_neutral'):
        for category in ['overall']+sorted({r['subset'] for r in rows}):
            group=[r for r in rows if (category=='overall' or r['subset']==category)
                   and r.get('baseline_letter') in ('A','B','C','D') and r.get('draft_letter') in ('A','B','C','D')
                   and (population=='all' or (r['baseline_letter']==r['correct'])==(population=='correct_neutral'))
                   and all(r.get('final_'+p+'_letter') in ('A','B','C','D') for p in ('none','intrinsic','tool'))]
            group.sort(key=lambda r:r['item_id'])
            for policy in ('intrinsic','tool'):
                delta=np.array([int(r['final_'+policy+'_letter']==r['correct'])-int(r['final_none_letter']==r['correct']) for r in group])
                if not len(delta):
                    point=low=high=None
                else:
                    weights=np.random.default_rng(SEED).multinomial(len(delta),np.full(len(delta),1/len(delta)),size=resamples)
                    point=float(delta.mean());low,high=map(float,np.quantile(weights@delta/len(delta),[.025,.975]))
                result.append(dict(instrument='parrot',system=system,kind='category_benefit',population=population,
                                   contrast=category,policy=policy,n=len(group),estimate=point,low=low,high=high,
                                   control_wrong=sum(r['final_none_letter']!=r['correct'] for r in group),
                                   treatment_wrong=sum(r['final_'+policy+'_letter']!=r['correct'] for r in group)))
    return result


def build(output=OUT,resamples=RESAMPLES):
    output.mkdir(parents=True,exist_ok=True)
    results=[];frames=[];sources={}
    stems=question_stems()
    for system in SYSTEMS:
        rows,frame=syco_results(_transfer(system,'sycobench'),stems,system,resamples)
        results.extend(rows);frames.append(frame);results.extend(parrot_results(system,resamples))
        for instrument,folder in (('sycobench','sycobench-600'),('parrot','parrot')):
            for path in (REPO_ROOT/'data/runs/transfer'/folder/system).glob('*.jsonl'):
                if path.name in ('items.jsonl','pressures.jsonl','tool.jsonl'):
                    sources[str(path.relative_to(REPO_ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    from scripts.transfer_sycobench import DATA
    questions=DATA
    if questions.exists():sources[str(questions.relative_to(REPO_ROOT))]=hashlib.sha256(questions.read_bytes()).hexdigest()
    data=dict(status='Exploratory; adapted instruments; not original benchmark rankings or a direct H2 replication',
              seed=SEED,resamples=resamples,syco_method='Complete matched correct-neutral instances across three pressures and all policies; resample normalized question stems, retain instance weighting',
              syco_family='18 interactions across three systems and two policies; Bonferroni percentile family intervals; separate from MAIN family',
              parrot_method='One pressure only; paired category effects, not pressure interaction; pointwise item-bootstrap intervals; categories have ten all-start items',
              limitations='No omnibus tests or category significance claims. Boundary intervals can collapse. Category populations differ; sparse wrong-neutral strata. External report rules out one of four options, unlike MAIN ceiling.',
              frames=frames,sources=sources,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),results=results)
    (output/'external_h2.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    fields=sorted(set().union(*(r.keys() for r in results)))
    with (output/'external_h2.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(results)
    return data


def figures(data,output=OUT):
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,1,figsize=(6.27,6.7),layout='constrained',sharex=True)
    contrasts=['wrong_suggestion minus doubt','wrong_suggestion minus authority','doubt minus authority']
    labels=['Suggestion − doubt','Suggestion − authority','Doubt − authority']
    for ax,system in zip(axes,SYSTEMS):
        for policy,offset in (('intrinsic',-.12),('tool',.12)):
            for j,contrast in enumerate(contrasts):
                r=next(r for r in data['results'] if r['instrument']=='sycobench' and r['system']==system and r['policy']==policy and r['kind']=='interaction' and r['contrast']==contrast)
                ax.plot([100*r['family_low'],100*r['family_high']],[j+offset]*2,color=POLICY_COLOUR[policy],linewidth=1.8)
                ax.plot(100*r['estimate'],j+offset,'s' if policy=='intrinsic' else 'o',color=POLICY_COLOUR[policy],label=policy if j==0 else None)
        last=next(r for r in data['results'] if r['instrument']=='sycobench' and r['system']==system and r['policy']=='tool' and r['kind']=='interaction' and r['contrast']==contrasts[-1])
        ax.set_title(NAMES[system]+f"  ·  {last['n']} instances / {last['stems']} stems",fontsize=10,fontweight='bold')
        ax.set_yticks(range(3),labels);ax.set_ylim(2.5,-.5);ax.tick_params(labelsize=9)
        ax.axvline(0,color='#777777',linestyle='--',linewidth=.8);ax.grid(axis='x',alpha=.15)
    axes[-1].set_xlabel('Difference in benefit versus re-ask (percentage points)',fontsize=9)
    handles,_=axes[0].get_legend_handles_labels();fig.legend(handles,['Self-check','External report'],loc='outside lower center',ncol=2,fontsize=9,frameon=False)
    fig.suptitle('Exploratory SycoBench pressure moderation',fontsize=12,fontweight='bold')
    for suffix in ('png','pdf','svg'):fig.savefig(output/f'sycobench_h2_interactions.{suffix}',dpi=240)
    plt.close(fig)
    syco=output/'sycobench_h2_interactions.png'
    categories=sorted({r['contrast'] for r in data['results'] if r['instrument']=='parrot' and r['contrast']!='overall'})
    fig,axes=plt.subplots(1,3,figsize=(6.27,7.4),layout='constrained',sharex=True,sharey=True)
    for ax,system in zip(axes,SYSTEMS):
        for policy,offset in (('intrinsic',-.12),('tool',.12)):
            for j,category in enumerate(categories):
                r=next(r for r in data['results'] if r['instrument']=='parrot' and r['system']==system and r['policy']==policy and r['population']=='all' and r['contrast']==category)
                if r['estimate'] is None:continue
                ax.plot([100*r['low'],100*r['high']],[j+offset]*2,color=POLICY_COLOUR[policy],linewidth=1.4)
                ax.plot(100*r['estimate'],j+offset,'s' if policy=='intrinsic' else 'o',color=POLICY_COLOUR[policy],markersize=4,label=policy if j==0 else None)
        ax.set_title(NAMES[system],fontsize=10,fontweight='bold');ax.axvline(0,color='#777777',linestyle='--',linewidth=.8)
        ax.set_yticks(range(len(categories)),[c.replace('_',' ').capitalize() for c in categories]);ax.set_ylim(len(categories)-.5,-.5)
        ax.set_xlim(-100,100);ax.set_xticks([-100,0,100]);ax.tick_params(labelsize=8.5);ax.grid(axis='x',alpha=.15)
        ax.set_xlabel('Benefit (pp)',fontsize=9)
    handles,_=axes[0].get_legend_handles_labels();fig.legend(handles,['Self-check','External report'],loc='outside lower center',ncol=2,fontsize=9,frameon=False)
    fig.suptitle('Exploratory PARROT category effects\nAll starts · ten items/category · pointwise 95% intervals',fontsize=10,fontweight='bold')
    for suffix in ('png','pdf','svg'):fig.savefig(output/f'parrot_category_benefits.{suffix}',dpi=240)
    plt.close(fig)
    return [syco,output/'parrot_category_benefits.png']


if __name__=='__main__':
    data=build()
    for path in figures(data):print(path)

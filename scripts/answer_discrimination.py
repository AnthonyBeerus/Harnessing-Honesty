"""Offline, descriptive answer-discrimination diagnostics; no model clients.

See docs/posthoc-answer-discrimination-2026-10-11.md. Counts describe the
recorded corpus, without new confidence intervals or discovery tests.
"""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/runs/answer-discrimination-2026-10-11'
COLLECTIONS = ('main-2026-10-09', 'main-2026-10-09-repeat')
NAMES = {'sonnet.anthropic': 'Sonnet 4.6', 'gpt4o.openai': 'GPT-4o', 'gemma4.deepinfra': 'Gemma 4'}


def validate(rows):
    branches = defaultdict(dict)
    for r in rows:
        identity = (r['card'], r['item_id'], r['pressure'])
        if r['policy'] in branches[identity]:
            raise ValueError('Duplicate policy branch')
        branches[identity][r['policy']] = r
        if r['answer_key'] not in ('yes', 'no'):
            raise ValueError('Invalid scoring key')
        if r['final_state'] == 'valid':
            if r['final_answer'] not in ('yes', 'no'):
                raise ValueError('Invalid final answer')
            if (r['final_correct'] == 'True') != (r['final_answer'] == r['answer_key']):
                raise ValueError('Inconsistent final correctness')
    for copies in branches.values():
        if set(copies) != {'none', 'intrinsic', 'tool'}:
            raise ValueError('Missing policy copy')
        fields = ('draft_state', 'draft_correct', 'draft_answer', 'answer_key', 'initial_correct')
        if len({tuple(r[f] for f in fields) for r in copies.values()}) != 1:
            raise ValueError('Inconsistent shared draft')


def main_analysis(rows, collection):
    validate(rows)
    reference, transitions, distribution = [], [], []
    for card in sorted({r['card'] for r in rows}):
        system = Path(card).stem.replace('qualification.', '')
        own = [r for r in rows if r['card'] == card]
        for policy in ('none', 'intrinsic', 'tool'):
            raw = [r for r in own if r['policy'] == policy]
            valid = [r for r in raw if r['final_state'] == 'valid']
            distribution.append(dict(collection=collection, system=system, policy=policy,
                yes=sum(r['final_answer'] == 'yes' for r in valid), n=len(valid), excluded=len(raw)-len(valid)))
        for policy, label in (('none','re-ask'), ('intrinsic','self-check'), ('none','always yes'), ('none','always no')):
            # Static rules use self-check's evaluable population, so the comparison
            # against self-check has exactly matched denominators.
            selected_policy = 'intrinsic' if label.startswith('always') else policy
            raw = [r for r in own if r['policy'] == selected_policy]
            eligible = [r for r in raw if r['final_state'] == 'valid']
            for metric in ('accuracy', 'repair', 'harm'):
                population = raw if metric == 'accuracy' else [r for r in raw if r['initial_correct'] == 'True'
                    and r['draft_state'] == 'valid' and r['draft_correct'] == ('False' if metric == 'repair' else 'True')]
                valid = [r for r in population if r['final_state'] == 'valid']
                def outcome(r):
                    answer = label.split()[-1] if label.startswith('always') else r['final_answer']
                    return answer == r['answer_key'] if metric != 'harm' else answer != r['answer_key']
                numerator = sum(outcome(r) for r in valid)
                reference.append(dict(collection=collection, system=system, policy=label, metric=metric,
                    numerator=numerator, n=len(valid), excluded=len(population)-len(valid),
                    rate=numerator/len(valid) if valid else None))
        own = [r for r in own if r['policy'] == 'intrinsic' and r['initial_correct'] == 'True' and r['draft_state'] == 'valid']
        for answer in ('no','yes'):
            for correct in (False,True):
                group = [r for r in own if r['draft_answer'] == answer and (r['draft_correct']=='True') == correct]
                valid = [r for r in group if r['final_state']=='valid']
                for final in ('no','yes'):
                    numerator=sum(r['final_answer']==final for r in valid)
                    transitions.append(dict(collection=collection,system=system,draft=answer,correct=correct,
                        final=final,numerator=numerator,n=len(valid),excluded=len(group)-len(valid),
                        rate=numerator/len(valid) if valid else None))
    return reference, transitions, distribution


def verifier_analysis(records, system):
    seen=set(); result=[]
    for r in records:
        identity=(r['item_id'],r['pressure'])
        if identity in seen: raise ValueError('Duplicate verifier branch')
        seen.add(identity)
        if not r.get('failure') and r['verdict'] not in ('yes','no'):
            raise ValueError('Invalid verifier verdict')
    eligible=[r for r in records if r['eligibility'] in ('recovery','maintenance')]
    for answer in ('no','yes'):
        for correct in (False,True):
            group=[r for r in eligible if r['draft_answer']==answer and (r['answer_key']==answer)==correct]
            if any(r['eligibility'] != ('maintenance' if correct else 'recovery') for r in group):
                raise ValueError('Verifier eligibility does not match draft correctness')
            valid=[r for r in group if not r.get('failure') and r['verdict'] in ('yes','no')]
            for verdict in ('no','yes'):
                numerator=sum(r['verdict']==verdict for r in valid)
                result.append(dict(system=system,draft=answer,correct=correct,verdict=verdict,
                    numerator=numerator,n=len(valid),excluded=len(group)-len(valid),
                    rate=numerator/len(valid) if valid else None))
    return result


def build(output=OUTPUT):
    tables={'reference':[],'transitions':[],'distribution':[],'verifier':[]}; sources={}
    for collection in COLLECTIONS:
        path=ROOT/'data/runs/results'/collection/'matrix-rows.csv'
        sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding='utf-8') as f: rows=list(csv.DictReader(f))
        parts=main_analysis(rows,collection)
        for key,part in zip(('reference','transitions','distribution'),parts): tables[key].extend(part)
    for system in NAMES:
        path=ROOT/'data/runs/transfer/verifier/main-2026-10-09'/system/'verifier.jsonl'
        sources[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        records=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        tables['verifier'].extend(verifier_analysis(records,system))
    external, options, truthful = external_analysis(sources)
    tables.update(external_outcomes=external, external_options=options, truthful_updates=truthful)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    for key,rows in tables.items():
        with (output/(key+'.csv')).open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    manifest=dict(status='post-hoc descriptive',sources=sources,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Finite recorded corpus; branch-weighted; no confidence intervals, significance tests or new observations',
        reference_population='Static rules use self-check valid-final population; re-ask uses its own valid finals')
    (output/'provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return tables


def classify_option(answer, correct, suggested):
    """Four-option errors need not endorse the user's suggested error."""
    if answer not in 'ABCD' or len(answer) != 1:
        raise ValueError('Invalid option')
    return 'correct' if answer == correct else 'suggested wrong' if answer == suggested else 'other wrong'


def external_analysis(sources):
    """Matched valid stages; suggested options follow the saved protocol, not outcomes."""
    from scripts.binary_followup import transfer_branches
    outcomes, options, truthful = [], [], []
    for instrument in ('sycobench', 'parrot'):
        for system in NAMES:
            directory = ROOT / 'data/runs/transfer' / ('sycobench-600' if instrument == 'sycobench' else 'parrot') / system
            metadata = {}
            for name in ('items.jsonl', 'pressures.jsonl', 'tool.jsonl'):
                path = directory / name
                if path.exists():
                    sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
                    if name == 'items.jsonl':
                        metadata = {r['item_id']: r for r in map(json.loads, path.read_text('utf-8').splitlines()) if r.get('pressure')}
            branches = transfer_branches(directory, instrument)
            for pressure in sorted({r['pressure'] for r in branches}):
                own = [r for r in branches if r['pressure'] == pressure]
                matched = [r for r in own if r['draft'] in ('A','B','C','D') and all(v in ('A','B','C','D') for v in r['finals'].values())]
                eligible = [r for r in matched if r['baseline'] == r['correct']]
                stages = ('draft', 'none', 'intrinsic', 'tool')
                def answer(r, stage):
                    return r['draft'] if stage == 'draft' else r['finals'][stage]
                def suggestion(r):
                    if instrument == 'parrot':
                        value = metadata[r['item_id']]['asserted']
                        if value == r['correct']: raise ValueError('PARROT assertion must be wrong')
                        return value
                    if pressure == 'wrong_suggestion':
                        return next(v for v in 'ABCD' if v != r['correct'])
                    if pressure == 'correct_suggestion': return r['correct']
                    return None  # doubt/authority do not specify an option
                for stage in stages:
                    for category in ('correct', 'suggested wrong', 'other wrong'):
                        numerator = sum(classify_option(answer(r,stage),r['correct'],suggestion(r)) == category for r in eligible)
                        outcomes.append(dict(instrument=instrument,system=system,pressure=pressure,stage=stage,category=category,
                            numerator=numerator,n=len(eligible),excluded=len(own)-len(matched),rate=numerator/len(eligible) if eligible else None))
                    for option in 'ABCD':
                        numerator=sum(answer(r,stage)==option for r in matched)
                        options.append(dict(instrument=instrument,system=system,pressure=pressure,stage=stage,option=option,
                            numerator=numerator,n=len(matched),rate=numerator/len(matched) if matched else None))
                if pressure == 'correct_suggestion':
                    initially_wrong=[r for r in matched if r['baseline'] in ('A','B','C','D') and r['baseline'] != r['correct']]
                    for stage in stages:
                        numerator=sum(answer(r,stage)==r['correct'] for r in initially_wrong)
                        truthful.append(dict(instrument=instrument,system=system,stage=stage,numerator=numerator,n=len(initially_wrong),
                            excluded=len(own)-len(matched),rate=numerator/len(initially_wrong) if initially_wrong else None))
    return outcomes, options, truthful


def figures(tables, output=OUTPUT):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    output=Path(output); output.mkdir(parents=True,exist_ok=True);paths=[]
    def save(fig,name):
        for ext in ('png','pdf'): fig.savefig(output/(name+'.'+ext),dpi=220,bbox_inches='tight')
        plt.close(fig);paths.append(output/(name+'.png'))
    systems=list(NAMES)
    for collection in COLLECTIONS:
        tag='main' if collection==COLLECTIONS[0] else 'repeat'
        fig,axes=plt.subplots(3,3,figsize=(7.1,8),layout='constrained')
        labels=('re-ask','self-check','always yes','always no')
        for row,system in enumerate(systems):
            for col,metric in enumerate(('accuracy','repair','harm')):
                ax=axes[row,col]
                own=[r for r in tables['reference'] if r['collection']==collection and r['system']==system and r['metric']==metric]
                records=[next(r for r in own if r['policy']==p) for p in labels]
                ax.barh(range(4),[r['rate']*100 if r['rate'] is not None else 0 for r in records],
                    color=['#74899b','#c66c32','#a8bbc9','#d4dde4'],height=.62)
                ax.set(yticks=range(4),yticklabels=labels if col==0 else [],xlim=(0,126),xticks=[0,50,100]);ax.invert_yaxis()
                ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
                for y,r in enumerate(records):
                    ax.text(102,y,f"{r['numerator']}/{r['n']}" if r['n'] else 'n/a',va='center',fontsize=9)
                if row==0: ax.set_title({'accuracy':'Accuracy\nAll valid finals','repair':'Repair\nConceded drafts','harm':'Harm\nHeld correct drafts'}[metric],fontsize=10,fontweight='bold')
                if col==0: ax.set_ylabel(NAMES[system],fontweight='bold')
                if row==2: ax.set_xlabel('Rate (%)')
        fig.suptitle(f'{tag.upper()}: checking and constant-answer references',fontsize=13,fontweight='bold')
        fig.supxlabel('Counts at right. Repair/harm require correct starts. Static rules match self-check eligibility.\nRe-ask excludes invalid finals. Descriptive branch rates; repeat uses the same items.',fontsize=8)
        save(fig,'reference_'+tag)
        matrix_figure(tables['transitions'], 'final', ['Final no','Final yes'],
            f'{tag.upper()}: self-check transitions conditional on draft correctness',
            'transition_'+tag,collection,systems,NAMES,plt,np,LinearSegmentedColormap,save)
    matrix_figure(tables['verifier'],'verdict',['Reject draft','Endorse draft'],
        'Fresh verifier: endorsement conditional on draft correctness','verifier_matrix',
        None,systems,NAMES,plt,np,LinearSegmentedColormap,save)
    for instrument, pressures in (('sycobench', ('wrong_suggestion','doubt','authority')), ('parrot', ('parrot',))):
        fig, axes = plt.subplots(len(pressures), 3, figsize=(7.1, 2.5*len(pressures)+1), squeeze=False, layout='constrained')
        for y, pressure in enumerate(pressures):
            for x, system in enumerate(systems):
                ax=axes[y,x]; bottom=np.zeros(4)
                own=[r for r in tables['external_outcomes'] if r['instrument']==instrument and r['pressure']==pressure and r['system']==system]
                for category,color in zip(('correct','suggested wrong','other wrong'),('#277b83','#ce7135','#a9b3bc')):
                    records=[next(r for r in own if r['stage']==s and r['category']==category) for s in ('draft','none','intrinsic','tool')]
                    values=np.array([100*r['rate'] if r['rate'] is not None else 0 for r in records])
                    ax.barh(range(4),values,left=bottom,color=color,label=category); bottom+=values
                ax.set(xlim=(0,100),xticks=(0,50,100),yticks=range(4),yticklabels=('Draft','Re-ask','Check','Report') if x==0 else ());ax.invert_yaxis()
                if y==0: ax.set_title(NAMES[system],fontweight='bold')
                draft=next(r for r in own if r['stage']=='draft' and r['category']=='other wrong')
                ax.set_xlabel(f'n={draft["n"]}; excluded={draft["excluded"]}',fontsize=9)
                if x==0: ax.set_ylabel(pressure.replace('_','\n'),fontsize=9)
        handles,labels=axes[0,0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='outside lower center',ncol=3,fontsize=8)
        fig.suptitle(instrument.upper()+': preservation and specified-error endorsement',fontsize=12,fontweight='bold')
        save(fig,'external_'+instrument)
    fig,axes=plt.subplots(1,3,figsize=(7.1,3.6),layout='constrained')
    for ax,system in zip(axes,systems):
        records=[r for r in tables['truthful_updates'] if r['system']==system]
        ax.barh(range(4),[100*r['rate'] if r['rate'] is not None else 0 for r in records],color='#277b83')
        ax.set(xlim=(0,130),xticks=(0,50,100),yticks=range(4),yticklabels=('Draft','Re-ask','Check','Report') if system==systems[0] else ());ax.invert_yaxis()
        ax.set_title(NAMES[system],fontweight='bold')
        for y,r in enumerate(records):ax.text(102,y,f'{r["numerator"]}/{r["n"]}',va='center',fontsize=9)
    fig.suptitle('SycoBench: useful updates after truthful suggestions',fontsize=12,fontweight='bold')
    fig.supxlabel('Initially wrong neutral answers; common valid stages. Descriptive accuracy (%).',fontsize=8)
    save(fig,'truthful_updates')
    return paths


def matrix_figure(rows, outcome, columns, title, name, collection, systems, names, plt, np, cmap_type, save):
    fig,axes=plt.subplots(1,3,figsize=(7.1,4.6),layout='constrained')
    groups=[('no',False),('no',True),('yes',False),('yes',True)]
    cmap=cmap_type.from_list('probability',['#f3f6f8','#1c6286']);cmap.set_bad('#e4e4e4')
    for ax,system in zip(axes,systems):
        own=[r for r in rows if r['system']==system and (collection is None or r['collection']==collection)]
        records=[[next(r for r in own if r['draft']==a and r['correct']==c and r[outcome]==v) for v in ('no','yes')] for a,c in groups]
        values=np.array([[r['rate'] if r['rate'] is not None else np.nan for r in pair] for pair in records])
        ax.imshow(values,vmin=0,vmax=1,cmap=cmap,aspect='auto')
        ax.set(xticks=[0,1],xticklabels=[c.replace(' ','\n',1) for c in columns],yticks=range(4),yticklabels=['Wrong no','Correct no','Wrong yes','Correct yes'] if system==systems[0] else [])
        ax.set_title(names[system],fontweight='bold')
        for y,pair in enumerate(records):
            for x,r in enumerate(pair):
                text=f"{r['numerator']}/{r['n']}\n{100*r['rate']:.1f}%" if r['n'] else 'No eligible\ndrafts'
                ax.text(x,y,text,ha='center',va='center',color='white' if r['rate'] is not None and r['rate']>.55 else '#162d3b')
        for spine in ax.spines.values(): spine.set_visible(False)
    fig.suptitle(title.replace(': ', ':\n'),fontsize=13,fontweight='bold')
    fig.supxlabel('Correct-start drafts only. Row percentages sum to 100%; counts state denominators.\nPressure branches are dependent. Descriptive rates do not identify a causal mechanism.',fontsize=8)
    save(fig,name)


if __name__=='__main__':
    data=build(); paths=figures(data)
    print('Saved',len(paths),'charts and',len(data),'descriptive tables to',OUTPUT)

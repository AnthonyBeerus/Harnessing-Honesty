"""Offline replacements for transfer rate charts; MAIN intervals unchanged.

Transfer estimates remain instance-weighted; bootstrap resamples shared question
stems. The historical instance-resampled figures are retained in place.
"""
import csv
import hashlib
import json
import re
from pathlib import Path

from scripts.binary_followup import ROOT, SEED, RESAMPLES, cluster_ratio
from scripts.report.common import share_interval
from scripts.transfer_figures import CONDITIONS, NAMES, SYSTEMS, _units

OUTPUT=ROOT/'data/runs/final-sanity-2026-10-11'


def interval(units, instrument, stems):
    if not units:
        return dict(estimate=None,low=None,high=None,n=0,numerator=0,clusters=0)
    if instrument=='main':
        result=share_interval(units)
        return dict(estimate=result.value,low=result.low,high=result.high,n=result.units,
                    numerator=result.hits,clusters=len({u[0] for u in units}))
    clustered=[(stems[i] if instrument=='sycobench' else i,'all',int(v),1) for i,v in units]
    return cluster_ratio(clustered)


def build(output=OUTPUT):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    path=ROOT/'data/external/sycobench-600/questions.json'
    stems={q['id']:re.sub(r'\s+',' ',q['question'].strip().lower()) for q in json.loads(path.read_text('utf-8'))}
    records=[]
    for system in SYSTEMS:
        for label,instrument,pressure in CONDITIONS:
            concession,policies=_units(system,instrument,pressure)
            metric_units=[('concession','draft',concession)]
            metric_units += [(metric,policy,policies[policy][k]) for policy in ('none','intrinsic','tool') for k,metric in enumerate(('repair','harm'))]
            for metric,policy,units in metric_units:
                result=interval(units,instrument,stems)
                records.append(dict(system=system,instrument=instrument,pressure=pressure or 'pooled',
                    metric=metric,policy=policy,**{k:result[k] for k in ('estimate','low','high','n','numerator','clusters')}))
    with (output/'transfer-stem-rates.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    inputs=[path]
    for system in SYSTEMS:
        inputs += [ROOT/'data/runs/results/main-2026-10-09/matrix-rows.csv',
            ROOT/f'data/runs/transfer/verifier/main-2026-10-09/{system}/verifier.jsonl']
        for folder in ('sycobench-600','parrot'):
            inputs += list((ROOT/'data/runs/transfer'/folder/system).glob('*.jsonl'))
    manifest=dict(status='post-hoc descriptive uncertainty correction',seed=SEED,resamples=RESAMPLES,
        quantiles=[2.5,97.5],quantile_method='linear',
        unit='SycoBench normalized question stem; PARROT item; MAIN original share_interval retained',
        eligible_frame='Resample stems in each eligible metric population; retain instance weighting',
        empty_draws='Omit denominator-zero draws; suppress bounds below 95% defined draws',
        limitations='Nominal descriptive intervals; boundary degeneracy remains, not simultaneous or calibration-validated',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in set(inputs)},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'transfer-stem-provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return records


def figures(records,output=OUTPUT):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    output=Path(output);paths=[]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    labels=['MAIN','Syco: suggestion','Syco: doubt','Syco: authority','PARROT']
    colours={'none':'#39739a','intrinsic':'#c66c32','tool':'#43876c'}
    def own(system,j,metric,policy):
        _,instrument,pressure=CONDITIONS[j]
        return next(r for r in records if (r['system'],r['instrument'],r['pressure'],r['metric'],r['policy'])==(system,instrument,pressure or 'pooled',metric,policy))
    def point(ax,r,y,colour,counts=True):
        if r['estimate'] is None:ax.text(2,y,'No eligible drafts',fontsize=8,va='center');return
        x=100*r['estimate'];lo=r['low'];hi=r['high'];collapsed=lo==hi
        if lo is not None and hi is not None:ax.hlines(y,100*lo,100*hi,color=colour,lw=1.3)
        ax.plot(x,y,'o',ms=4,mfc='white' if collapsed else colour,mec=colour)
        if counts:ax.text(103,y,f'{int(r["numerator"])}/{r["n"]}',fontsize=8,va='center')
    def configure(ax):
        ax.set_xlim(-3,137);ax.set_xticks((0,50,100));ax.grid(axis='x',alpha=.14);ax.set_axisbelow(True)
    def save(fig,name):
        for ext in ('png','pdf'):fig.savefig(output/(name+'.'+ext),dpi=230,bbox_inches='tight')
        plt.close(fig);paths.append(output/(name+'.png'))
    fig,axes=plt.subplots(1,3,figsize=(7.1,4.1),layout='constrained')
    for col,(ax,system) in enumerate(zip(axes,SYSTEMS)):
        for j in range(5):point(ax,own(system,j,'concession','draft'),j,'#577c95')
        configure(ax);ax.set(yticks=range(5),yticklabels=labels if col==0 else [],ylim=(4.7,-.7));ax.set_title(NAMES[system],fontweight='bold');ax.set_xlabel('Concession (%)')
    fig.suptitle('Concession on MAIN and adapted external instruments',fontweight='bold',fontsize=12)
    fig.supxlabel('Counts at right. MAIN item intervals unchanged; transfer resamples question stems.\nHollow circles: collapsed intervals; settings differ in tasks, format and pressure.',fontsize=8)
    save(fig,'transfer_concession_stems')
    fig,axes=plt.subplots(2,3,figsize=(7.1,6.8),layout='constrained')
    for col,system in enumerate(SYSTEMS):
        for row,metric in enumerate(('repair','harm')):
            ax=axes[row,col]
            for j in range(5):
                if all(own(system,j,metric,p)['estimate'] is None for p in ('none','intrinsic')):
                    ax.text(2,j,'No eligible drafts',fontsize=8,va='center')
                    continue
                for policy,offset in (('none',-.13),('intrinsic',.13)):
                    point(ax,own(system,j,metric,policy),j+offset,colours[policy],False)
            configure(ax);ax.set(yticks=range(5),yticklabels=labels if col==0 else [],ylim=(4.7,-.7));ax.set_xlabel(metric.title()+' (%)')
            if row==0:ax.set_title(NAMES[system],fontweight='bold')
    fig.suptitle('Repair and harm: re-ask versus self-check',fontweight='bold',fontsize=12)
    fig.supxlabel('Blue: re-ask; orange: self-check. Populations differ between repair and harm.\nMAIN item intervals unchanged; transfer stem intervals. Exact counts in Appendix E.',fontsize=8)
    save(fig,'transfer_repair_harm_stems')
    for system in SYSTEMS:
        fig,axes=plt.subplots(1,2,figsize=(7.1,7.5),layout='constrained')
        for ax,metric in zip(axes,('repair','harm')):
            ticks=[];texts=[]
            for j in range(5):
                for k,policy in enumerate(('none','intrinsic','tool')):
                    y=j*4+k;ticks.append(y);texts.append(labels[j]+' / '+{'none':'Re-ask','intrinsic':'Check','tool':'Report'}[policy])
                    point(ax,own(system,j,metric,policy),y,colours[policy])
            configure(ax);ax.set(yticks=ticks,yticklabels=texts if metric=='repair' else [],ylim=(18.7,-.7));ax.set_title(metric.title(),fontweight='bold');ax.set_xlabel('Rate (%)')
        fig.suptitle(NAMES[system]+': detailed repair and harm',fontweight='bold',fontsize=12)
        fig.supxlabel('MAIN item intervals unchanged; SycoBench stem intervals; PARROT item intervals.\nCounts at right. Hollow circles mark collapsed intervals, not established zero risk.',fontsize=8)
        save(fig,'transfer_detail_'+system)
    return paths


if __name__=='__main__':
    for path in figures(build()):print(path)

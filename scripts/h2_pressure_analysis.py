"""Exploratory H2 pressure interactions from recorded MAIN rows; no model calls.

Positive benefit means fewer wrong finals than re-ask. Interactions are
differences in this benefit between two pressures, not differences in
significance. Whole items retain all pressures/policies in each bootstrap.
"""
import csv
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from harnessing_honesty import REPO_ROOT
from scripts.report.common import MODEL_LABEL, POLICY_COLOUR, PRESSURES

OUT = REPO_ROOT / 'data/runs/h2-exploratory-2026-10-12'
SEED = 20261012
RESAMPLES = 50000


def load(collection):
    path = REPO_ROOT / 'data/runs/results' / collection / 'matrix-rows.csv'
    with path.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    return rows, path


def model_arrays(rows, card, policy, population):
    selected = [r for r in rows if r['card'] == card]
    lookup = {(r['item_id'], r['pressure'], r['policy']): r for r in selected}
    assert len(lookup) == len(selected), 'Duplicate item/pressure/policy rows'
    ids = sorted({r['item_id'] for r in selected if r['initial_correct'] == 'True'})
    values = np.zeros((len(ids), 3)); valid = np.zeros_like(values)
    raw = []
    for i, item in enumerate(ids):
        for j, pressure in enumerate(PRESSURES):
            base, treatment = (lookup.get((item, pressure, p)) for p in ('none', policy))
            if not base or not treatment:
                continue
            assert base['draft_answer'] == treatment['draft_answer']
            assert base['draft_correct'] == treatment['draft_correct']
            include = all(r['eligible'] == 'True' and r['initial_correct'] == 'True'
                          and r['draft_state'] == 'valid' and r['final_state'] == 'valid'
                          for r in (base, treatment))
            include &= population in ('all', 'complete') or base['draft_correct'] == ('False' if population == 'recovery' else 'True')
            if include:
                # correct(treatment)-correct(control) == wrong(control)-wrong(treatment)
                delta = int(treatment['final_correct'] == 'True') - int(base['final_correct'] == 'True')
                values[i, j] = delta; valid[i, j] = 1
                raw.append(dict(item=item, pressure=pressure, delta=delta,
                                control_wrong=int(base['final_correct'] == 'False'),
                                treatment_wrong=int(treatment['final_correct'] == 'False')))
    if population == 'complete':
        complete = valid.all(axis=1)
        values[~complete] = 0; valid[~complete] = 0
        retained = {item for item, keep in zip(ids, complete) if keep}
        raw = [r for r in raw if r['item'] in retained]
    return ids, values, valid, raw


def summarise(collection, resamples=RESAMPLES):
    rows, source = load(collection)
    outputs = []; audit = []
    cards = sorted({r['card'] for r in rows})
    for card in cards:
        system = Path(card).name.split('.')[1]
        for population in ('all', 'complete', 'recovery', 'maintenance'):
            for policy in ('intrinsic', 'tool'):
                ids, values, valid, raw = model_arrays(rows, card, policy, population)
                # Same sorted item frame/seed across policies/populations. Includes
                # empty conditional items; never resamples branches independently.
                rng = np.random.default_rng(SEED)
                families = {r['item_id']: r['family'] for r in rows if r['card'] == card}
                weights = np.zeros((resamples, len(ids)), dtype=int)
                for family in sorted(set(families[item] for item in ids)):
                    slots = [i for i, item in enumerate(ids) if families[item] == family]
                    weights[:, slots] = rng.multinomial(len(slots), np.full(len(slots), 1 / len(slots)), size=resamples)
                counts = valid.sum(axis=0)
                point = np.divide(values.sum(axis=0), counts, out=np.full(3, np.nan), where=counts > 0)
                numerator, denominator = weights @ values, weights @ valid
                draws = np.divide(numerator, denominator, out=np.full_like(numerator, np.nan), where=denominator > 0)
                for j, pressure in enumerate(PRESSURES):
                    subset = [r for r in raw if r['pressure'] == pressure]
                    low, high = np.nanquantile(draws[:, j], [.025, .975])
                    outputs.append(dict(collection=collection, system=system, population=population, policy=policy,
                                        kind='benefit', contrast=pressure, estimate=float(point[j]), low=float(low), high=float(high),
                                        n=int(counts[j]), control_wrong=sum(r['control_wrong'] for r in subset),
                                        treatment_wrong=sum(r['treatment_wrong'] for r in subset),
                                        empty_draws=int(np.isnan(draws[:, j]).sum())))
                for a, b in combinations(range(3), 2):
                    # Orient citation first for the proposal's directional prediction.
                    if b == 2:
                        a, b = b, a
                    sample = draws[:, a] - draws[:, b]
                    low, high = np.nanquantile(sample, [.025, .975])
                    # 18 primary contrasts: 3 models × 2 policies × 3 pressure pairs.
                    family_low, family_high = np.nanquantile(sample, [.05 / 36, 1 - .05 / 36])
                    outputs.append(dict(collection=collection, system=system, population=population, policy=policy,
                                        kind='interaction', contrast=PRESSURES[a]+' minus '+PRESSURES[b],
                                        estimate=float(point[a]-point[b]), low=float(low), high=float(high),
                                        family_low=float(family_low) if population in ('all', 'complete') else None,
                                        family_high=float(family_high) if population in ('all', 'complete') else None,
                                        n=int(len(ids)), n_a=int(counts[a]), n_b=int(counts[b]),
                                        empty_draws=int(np.isnan(sample).sum())))
                audit.append(dict(system=system, population=population, policy=policy, item_frame=ids,
                                  families={item: families[item] for item in ids}, complete_pairs=counts.astype(int).tolist()))
    return outputs, dict(source=str(source.relative_to(REPO_ROOT)), sha256=hashlib.sha256(source.read_bytes()).hexdigest(), frames=audit)


def build(output=OUT, resamples=RESAMPLES):
    output.mkdir(parents=True, exist_ok=True)
    results = []; sources = []
    for collection in ('main-2026-10-09', 'main-2026-10-09-repeat'):
        rows, provenance = summarise(collection, resamples)
        results.extend(rows); sources.append(provenance)
    data = dict(status='Exploratory; not registered; no confirmatory H2 decision',
                seed=SEED, resamples=resamples, interval='Family-stratified whole-item percentile bootstrap, numpy linear quantiles',
                primary_family='18 all-eligible interaction contrasts per collection; Bonferroni intervals',
                diagnostic_intervals='Recovery/maintenance: pointwise only; selected pressure-specific populations',
                missing='Pairwise complete policies per pressure; complete sensitivity retains valid pairs across all three pressures; omit and count empty conditional draws',
                repeat='Same items; sensitivity, not independent replication', sources=sources, results=results,
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'h2.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    fields = sorted(set().union(*(r.keys() for r in results)))
    with (output/'h2.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(results)
    return data


def figure(data, output=OUT):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.5), sharex=True, sharey=True, layout='constrained')
    contrasts = ['citation minus contradiction', 'citation minus authority', 'contradiction minus authority']
    for ax, system in zip(axes, ('sonnet', 'gpt4o', 'gemma4')):
        for policy, offset in (('intrinsic', -.12), ('tool', .12)):
            for j, contrast in enumerate(contrasts):
                r = next(r for r in data['results'] if r['collection']=='main-2026-10-09' and r['system']==system
                         and r['population']=='all' and r['policy']==policy and r['kind']=='interaction' and r['contrast']==contrast)
                x, lo, hi = (100*r[k] for k in ('estimate', 'family_low', 'family_high'))
                ax.plot([lo, hi], [j+offset]*2, color=POLICY_COLOUR[policy], linewidth=2)
                ax.plot(x, j+offset, 'o' if policy=='tool' else 's', color=POLICY_COLOUR[policy], label=policy if j==0 else None)
        ax.axvline(0, color='#777777', linestyle='--', linewidth=1)
        ax.set_title(MODEL_LABEL[system]); ax.set_xlabel('Difference in benefit (percentage points)')
        ax.set_yticks(range(3), ['Citation − contradiction', 'Citation − authority', 'Contradiction − authority'])
        ax.grid(axis='x', alpha=.15); ax.set_ylim(2.5, -.5)
    handles, _ = axes[0].get_legend_handles_labels()
    fig.legend(handles, ['Self-check', 'External verification'], loc='outside upper right')
    fig.suptitle('Exploratory H2: does policy benefit vary by pressure?', fontweight='bold')
    fig.supxlabel('Correct-neutral starts, paired policies; family-stratified item bootstrap. Bonferroni-adjusted 95% family intervals across 18 contrasts.\nPositive external-verification citation contrasts favour H2’s ordering. Intervals are approximate; collapsed intervals do not establish zero uncertainty.', fontsize=9)
    for suffix in ('png', 'pdf', 'svg'):
        fig.savefig(output/f'h2_interactions.{suffix}', dpi=180)
    plt.close(fig)
    return output/'h2_interactions.png'


def _draw_panel(ax, data, system, kind, compact=False):
    contrasts = list(PRESSURES) if kind == 'benefit' else ['citation minus contradiction', 'citation minus authority', 'contradiction minus authority']
    labels = ['Contradiction', 'Authority', 'Citation'] if kind == 'benefit' else ['Citation − contradiction', 'Citation − authority', 'Contradiction − authority']
    if compact and kind == 'interaction':
        labels = ['Cit. − contra.', 'Cit. − auth.', 'Contra. − auth.']
    for policy, offset in (('intrinsic', -.13), ('tool', .13)):
        for j, contrast in enumerate(contrasts):
            r = next(r for r in data['results'] if r['collection']=='main-2026-10-09' and r['system']==system and r['population']=='all' and r['policy']==policy and r['kind']==kind and r['contrast']==contrast)
            keys = ('low', 'high') if kind == 'benefit' else ('family_low', 'family_high')
            lo, hi = (100*r[k] for k in keys)
            ax.plot([lo, hi], [j+offset]*2, color=POLICY_COLOUR[policy], linewidth=1.8)
            ax.plot(100*r['estimate'], j+offset, 's' if policy=='intrinsic' else 'o', color=POLICY_COLOUR[policy], markersize=5, label=policy if j==0 else None)
    ax.axvline(0, color='#777777', linestyle='--', linewidth=.8)
    ax.set_yticks(range(3), labels); ax.set_ylim(2.5,-.5)
    ax.set_xlim((-100,100) if kind=='benefit' else (-80,80))
    ax.set_xticks([-100,-50,0,50,100] if kind=='benefit' else [-80,-40,0,40,80])
    ax.grid(axis='x', alpha=.15)
    ax.tick_params(labelsize=8.5 if compact else 10)


def benefits_figure(data, output=OUT):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1,3,figsize=(12,4.5),layout='constrained')
    for ax, system in zip(axes, ('sonnet','gpt4o','gemma4')):
        _draw_panel(ax,data,system,'benefit'); ax.set_title(MODEL_LABEL[system])
        ax.set_xlabel('Reduction in wrong finals versus re-ask (pp)')
    handles, _ = axes[0].get_legend_handles_labels()
    fig.legend(handles,['Self-check','External verification'],loc='outside upper right')
    fig.suptitle('Exploratory H2: net policy benefit by pressure',fontweight='bold')
    fig.supxlabel('Valid correct-neutral starts: Sonnet 51, GPT-4o 48, Gemma 47 pairs per pressure. Positive values favour intervention.\nPointwise 95% family-stratified item-bootstrap intervals; repair and preservation included. These intervals are not multiplicity-adjusted.',fontsize=9)
    for suffix in ('png','pdf','svg'):fig.savefig(output/f'h2_benefits.{suffix}',dpi=180)
    plt.close(fig)
    return output/'h2_benefits.png'


def report_figure(data, output=OUT):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3,2,figsize=(6.27,7.0),layout='constrained')
    for row, system in enumerate(('sonnet','gpt4o','gemma4')):
        for col, kind in enumerate(('benefit','interaction')):
            ax=axes[row,col];_draw_panel(ax,data,system,kind,compact=True)
            ax.set_title(MODEL_LABEL[system],fontsize=10,fontweight='bold')
            if row==2:ax.set_xlabel('Benefit (pp)' if col==0 else 'Difference in benefit (pp)',fontsize=9)
    axes[0,0].text(0,1.25,'A  Policy benefit by pressure',transform=axes[0,0].transAxes,fontsize=10,fontweight='bold')
    axes[0,1].text(0,1.25,'B  Pressure interactions',transform=axes[0,1].transAxes,fontsize=10,fontweight='bold')
    handles,_=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,['Self-check','External verification'],loc='outside lower center',ncol=2,fontsize=9,frameon=False)
    for suffix in ('png','pdf','svg'):fig.savefig(output/f'h2_report.{suffix}',dpi=240)
    plt.close(fig)
    return output/'h2_report.png'


if __name__ == '__main__':
    result = build(); print(figure(result)); print(benefits_figure(result)); print(report_figure(result))

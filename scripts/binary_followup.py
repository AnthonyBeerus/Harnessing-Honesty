"""Post-hoc direction, transitions and stem-paired transfer diagnostics. Offline only."""
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

from scripts.behavioral_diagnostics import COLLECTIONS, ROOT, PRESSURES, item_vectors, write_csv

OUTPUT = ROOT / "data/runs/binary-followup-2026-10-11"
SEED, RESAMPLES = 20261012, 5000
POLICIES = ("none", "intrinsic", "tool")
SOURCES = {}


def csv_rows(path):
    SOURCES[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def json_rows(path):
    if not path.exists():
        return []
    SOURCES[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def cluster_ratio(units, resamples=RESAMPLES):
    """(cluster, stratum, numerator, denominator); instance-weighted clustered ratio."""
    grouped = defaultdict(lambda: np.zeros(2))
    strata = {}
    for cluster, stratum, numerator, denominator in units:
        if cluster in strata and strata[cluster] != stratum:
            raise ValueError("Cluster crosses strata")
        strata[cluster] = stratum
        grouped[cluster] += (numerator, denominator)
    if not grouped:
        return dict(estimate=None, low=None, high=None, n=0, clusters=0, defined_draws=0, numerator=0)
    keys = sorted(grouped)
    counts = np.array([grouped[k] for k in keys])
    total = counts.sum(axis=0)
    if total[1] <= 0:
        raise ValueError("No positive denominator")
    rng = np.random.default_rng(SEED)
    sampled = np.zeros((resamples, 2))
    for stratum in sorted(set(strata.values())):
        indexes = np.array([i for i,k in enumerate(keys) if strata[k] == stratum])
        draw = rng.choice(indexes, size=(resamples, len(indexes)), replace=True)
        sampled += counts[draw].sum(axis=1)
    valid = sampled[:,1] > 0
    ratios = sampled[valid,0]/sampled[valid,1]
    bounds = np.percentile(ratios, [2.5,97.5]) if valid.mean() >= .95 else (None, None)
    return dict(estimate=float(total[0]/total[1]), low=None if bounds[0] is None else float(bounds[0]),
        high=None if bounds[1] is None else float(bounds[1]), n=int(total[1]), clusters=len(keys),
        defined_draws=int(valid.sum()), numerator=float(total[0]))


def main_analysis(rows, collection, resamples=RESAMPLES):
    item_vectors(rows)  # reject duplicate branches and inconsistent drafts/identities
    rates, transitions, bounds, baseline = [], [], [], []
    for card in sorted({r["card"] for r in rows}):
        system = Path(card).stem.replace("qualification.", "")
        own = [r for r in rows if r["card"] == card]
        drafts = [r for r in own if r["policy"] == "none" and r["draft_state"] == "valid"]
        initial = {r["item_id"]:r for r in own}
        for key in ("yes", "no"):
            selected = [r for r in initial.values() if r["answer_key"] == key]
            baseline.append(dict(collection=collection,system=system,key=key,n=len(selected),
                correct=sum(r["initial_correct"]=="True" for r in selected)))
        for pressure in PRESSURES:
            subset = [r for r in drafts if r["pressure"] == pressure]
            for start in ("True", "False"):
                eligible = [r for r in subset if r["initial_correct"] == start]
                transitions.append(dict(collection=collection,system=system,pressure=pressure,
                    initial="correct" if start=="True" else "wrong",n=len(eligible),
                    final_correct=sum(r["draft_correct"]=="True" for r in eligible),
                    final_wrong=sum(r["draft_correct"]=="False" for r in eligible)))
            for policy in POLICIES:
                held=[r for r in own if r["pressure"]==pressure and r["policy"]==policy
                      and r["initial_correct"]=="True" and r["draft_state"]=="valid"
                      and r["draft_correct"]=="True" and r["final_state"]=="valid"]
                events=sum(r["final_correct"]=="False" for r in held)
                if held and events==0:
                    bounds.append(dict(collection=collection,system=system,pressure=pressure,policy=policy,
                        n=len(held),events=0,upper=zero_upper(len(held))))
        for key in ("all", "yes", "no"):
            selected=[r for r in own if r["initial_correct"]=="True" and r["draft_state"]=="valid"
                      and (key=="all" or r["answer_key"]==key)]
            common=dict(collection=collection,system=system,key=key)
            ds=[r for r in selected if r["policy"]=="none"]
            units=[(r["item_id"],r["family"],int(r["draft_correct"]=="False"),1) for r in ds]
            rates.append(dict(**common,metric="concession",policy="draft",excluded=0,
                              **cluster_ratio(units,resamples)))
            for policy in POLICIES:
                for population, correct in (("repair","False"),("harm","True")):
                    rr=[r for r in selected if r["policy"]==policy and r["draft_correct"]==correct]
                    valid=[r for r in rr if r["final_state"]=="valid"]
                    units=[(r["item_id"],r["family"],int(r["final_correct"]==("True" if population=="repair" else "False")),1) for r in valid]
                    rates.append(dict(**common,metric=population,policy=policy,excluded=len(rr)-len(valid),
                                      **cluster_ratio(units,resamples)))
            lookup={(r["item_id"],r["pressure"],r["policy"]):r for r in selected}
            for policy in ("intrinsic", "tool"):
                units=[]
                ids=sorted({r["item_id"] for r in selected})
                for item in ids:
                    pairs=[(lookup.get((item,p,"none")),lookup.get((item,p,policy))) for p in PRESSURES]
                    if not all(a and b and a["final_state"]==b["final_state"]=="valid" for a,b in pairs):
                        continue
                    pairs=[(a,b) for a,b in pairs if a and b]
                    benefit=sum(int(a["final_correct"]=="False")-int(b["final_correct"]=="False") for a,b in pairs)/3
                    units.append((item,pairs[0][0]["family"],benefit,1))
                rates.append(dict(**common,metric="net benefit",policy=policy,excluded=len(ids)-len(units),
                                  **cluster_ratio(units,resamples)))
    return rates, transitions, bounds, baseline


def zero_upper(n):
    if n <= 0:
        raise ValueError("n must be positive")
    return float(-np.expm1(np.log(.05)/n))


def transfer_branches(directory, instrument):
    """Offline equivalent of transfer_more.branches, without importing clients."""
    out=[]
    tools={r["item_id"]:r.get("final_tool_letter") for r in json_rows(directory/"tool.jsonl")}
    for r in json_rows(directory/"items.jsonl"):
        if instrument=="sycobench" and r.get("pressure") is None:
            continue
        pressure="parrot" if instrument=="parrot" else r["pressure"]+"_suggestion"
        finals={p:r.get(f"final_{p}_letter") for p in POLICIES}
        if instrument=="sycobench":finals["tool"]=tools.get(r["item_id"])
        out.append(dict(item_id=r["item_id"],pressure=pressure,correct=r["correct"],
                        baseline=r.get("baseline_letter"),draft=r.get("draft_letter"),finals=finals))
    for r in json_rows(directory/"pressures.jsonl"):
        out.append(dict(item_id=r["item_id"],pressure=r["pressure"],correct=r["correct"],
                        baseline=r.get("baseline_letter"),draft=r.get("draft_letter"),
                        finals={p:r.get(f"final_{p}_letter") for p in POLICIES}))
    keys=[(b["item_id"],b["pressure"]) for b in out]
    if len(set(keys))!=len(keys):raise ValueError("Duplicate transfer branch")
    return out


def transfer_analysis(branches, stems, instrument, system, resamples=RESAMPLES):
    comparisons, rates, transitions=[],[],[]
    common=dict(instrument=instrument,system=system)
    lookup={(b["item_id"],b["pressure"]):b for b in branches}
    for pressure in sorted({b["pressure"] for b in branches}):
        group=[b for b in branches if b["pressure"]==pressure and b["baseline"] in ("A","B","C","D")]
        for start in (True,False):
            eligible=[b for b in group if (b["baseline"]==b["correct"])==start and b["draft"] is not None]
            transitions.append(dict(**common,pressure=pressure,initial="correct" if start else "wrong",
                n=len(eligible),final_correct=sum(b["draft"]==b["correct"] for b in eligible),
                final_wrong=sum(b["draft"]!=b["correct"] for b in eligible)))
        eligible=[b for b in group if b["baseline"]==b["correct"] and b["draft"] is not None]
        if pressure=="correct_suggestion":continue
        for policy in ("intrinsic","tool"):
            pairs=[b for b in eligible if b["finals"][policy] is not None and b["finals"]["none"] is not None]
            units=[(stems[b["item_id"]],"all",int(b["finals"]["none"]!=b["correct"])-int(b["finals"][policy]!=b["correct"]),1) for b in pairs]
            rates.append(dict(**common,pressure=pressure,policy=policy,excluded=len(eligible)-len(pairs),
                              **cluster_ratio(units,resamples)))
    if instrument=="sycobench":
        conditions=("wrong_suggestion","doubt","authority")
        ids=sorted({b["item_id"] for b in branches})
        paired=[]
        for item in ids:
            triple=[lookup.get((item,p)) for p in conditions]
            if not all(triple):continue
            triple=[b for b in triple if b]
            if len({(b["baseline"],b["correct"]) for b in triple})!=1:
                raise ValueError("Inconsistent transfer baseline")
            if triple[0]["baseline"]!=triple[0]["correct"] or any(b["draft"] is None for b in triple):continue
            paired.append((item,triple))
        for a,b in ((2,0),(1,0),(2,1)):
            values=[(stems[item],"all",int(triple[a]["draft"]!=triple[a]["correct"])-int(triple[b]["draft"]!=triple[b]["correct"]),1) for item,triple in paired]
            comparisons.append(dict(**common,contrast=conditions[a]+" minus "+conditions[b],
                positive_discordances=sum(v[2]==1 for v in values),negative_discordances=sum(v[2]==-1 for v in values),
                **cluster_ratio(values,resamples)))
    return comparisons,rates,transitions


def build(output=OUTPUT, resamples=RESAMPLES):
    SOURCES.clear()
    output.mkdir(parents=True,exist_ok=True)
    rates,transitions,bounds,baseline=[],[],[],[]
    for collection in COLLECTIONS:
        result=main_analysis(csv_rows(ROOT/"data/runs/results"/collection/"matrix-rows.csv"),collection,resamples)
        for dest,part in zip((rates,transitions,bounds,baseline),result):dest.extend(part)
    comparisons,net,transfer_transitions=[],[],[]
    questions=json.loads((ROOT/"data/external/sycobench-600/questions.json").read_text(encoding="utf-8"))
    qpath=ROOT/"data/external/sycobench-600/questions.json"
    SOURCES[str(qpath.relative_to(ROOT))]=hashlib.sha256(qpath.read_bytes()).hexdigest()
    syco_stems={q["id"]:re.sub(r"\s+"," ",q["question"].strip().lower()) for q in questions}
    for instrument,folder in (("sycobench","sycobench-600"),("parrot","parrot")):
        for directory in sorted((ROOT/"data/runs/transfer"/folder).iterdir()):
            if not (directory/"items.jsonl").exists():continue
            branches=transfer_branches(directory,instrument)
            stems=syco_stems if instrument=="sycobench" else {b["item_id"]:b["item_id"] for b in branches}
            result=transfer_analysis(branches,stems,instrument,directory.name,resamples)
            for dest,part in zip((comparisons,net,transfer_transitions),result):dest.extend(part)
    tables=dict(main_rates=rates,main_transitions=transitions,zero_harm_bounds=bounds,baseline_direction=baseline,
                transfer_pressure=comparisons,transfer_net=net,transfer_transitions=transfer_transitions)
    for name,table in tables.items():write_csv(output/(name+".csv"),table)
    (output/"provenance.json").write_text(json.dumps(dict(status="post-hoc exploratory",seed=SEED,
        resamples=resamples,numpy=np.__version__,quantiles=[2.5,97.5],quantile_method="linear",
        interval_status="descriptive; not simultaneous or calibration-validated",source_sha256=SOURCES,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2),encoding="utf-8")
    return tables


def figures(tables, output=OUTPUT):
    import matplotlib.pyplot as plt
    names={"sonnet.anthropic":"Sonnet 4.6","gpt4o.openai":"GPT-4o","gemma4.deepinfra":"Gemma 4"}
    systems=list(names)
    plt.rcParams.update({"font.size":11,"font.family":"DejaVu Sans","pdf.fonttype":42})
    output.mkdir(parents=True,exist_ok=True)
    def finish(fig,name):
        fig.savefig(output/(name+".png"),dpi=200,bbox_inches="tight",facecolor="white")
        fig.savefig(output/(name+".pdf"),bbox_inches="tight",facecolor="white")
        plt.close(fig)
    def point(ax,r,y,color,marker="o"):
        x=100*float(r["estimate"])
        lo,hi=r["low"],r["high"]
        if lo is not None and hi is not None:
            ax.errorbar(x,y,xerr=[[x-100*float(lo)],[100*float(hi)-x]],fmt=marker,color=color,capsize=3)
        else:ax.plot(x,y,marker,color=color)
    fig,axes=plt.subplots(1,3,figsize=(10,3.7),sharex=True,sharey=True,layout="constrained")
    for ax,system in zip(axes,systems):
        for j,key in enumerate(("yes","no")):
            r=next(r for r in tables["main_rates"] if r["collection"]==COLLECTIONS[0] and r["system"]==system
                   and r["key"]==key and r["metric"]=="concession")
            point(ax,r,1-j,"#21627D" if key=="yes" else "#AF5C2D")
            ax.text(2,1-j+.17,f"{int(r['numerator'])}/{r['n']} branches",fontsize=10)
        ax.set_title(names[system]);ax.set_xlim(-3,103);ax.set_ylim(-.4,1.5);ax.set_xticks([0,50,100]);ax.grid(axis="x",alpha=.2)
        ax.set_xlabel("Concession (%)")
    axes[0].set_yticks([1,0],["Correct key: Yes","Correct key: No"])
    fig.suptitle("Answer-direction asymmetry in MAIN\n95% whole-item intervals; direction confounded with wording and content",fontsize=12)
    finish(fig,"direction_concession")
    fig,axes=plt.subplots(1,3,figsize=(10,4),sharex=True,sharey=True,layout="constrained")
    for ax,system in zip(axes,systems):
        for j,key in enumerate(("yes","no")):
            for policy,color,offset,marker in (("intrinsic","#21627D",.10,"o"),("tool","#AF5C2D",-.10,"s")):
                r=next(r for r in tables["main_rates"] if r["collection"]==COLLECTIONS[0] and r["system"]==system
                       and r["key"]==key and r["metric"]=="net benefit" and r["policy"]==policy)
                point(ax,r,1-j+offset,color,marker)
                ax.text(-90,1-j+.24,f"{key.title()}: self-check {float(next(t for t in tables['main_rates'] if t['collection']==COLLECTIONS[0] and t['system']==system and t['key']==key and t['metric']=='net benefit' and t['policy']=='intrinsic')['estimate'])*100:+.1f} pp",fontsize=9)
        ax.axvline(0,color="grey",ls="--",lw=1);ax.set_xlim(-103,103);ax.set_ylim(-.4,1.5);ax.set_xticks([-100,0,100])
        ax.set_title(names[system]);ax.grid(axis="x",alpha=.2);ax.set_xlabel("Net benefit (pp)")
    axes[0].set_yticks([1,0],["Correct key: Yes","Correct key: No"])
    fig.suptitle("Policy benefit depends on answer direction\nWrong re-ask minus wrong policy; circles self-check, squares oracle",fontsize=12)
    finish(fig,"direction_net")
    fig,axes=plt.subplots(1,3,figsize=(10,3.8),sharex=True,sharey=True,layout="constrained")
    contrasts=("authority minus wrong_suggestion","doubt minus wrong_suggestion","authority minus doubt")
    for ax,system in zip(axes,systems):
        for j,contrast in enumerate(contrasts):
            r=next(r for r in tables["transfer_pressure"] if r["system"]==system and r["contrast"]==contrast)
            point(ax,r,2-j,"#21627D")
        ax.axvline(0,color="grey",ls="--",lw=1);ax.set_xlim(-30,30);ax.set_xticks([-20,0,20]);ax.grid(axis="x",alpha=.2)
        ax.set_title(names[system]);ax.set_xlabel("Concession difference (pp)")
    axes[0].set_yticks([2,1,0],["Authority − suggestion","Doubt − suggestion","Authority − doubt"])
    fig.suptitle("Paired SycoBench pressure contrasts\nCommon correct-start instances; 95% question-stem bootstrap intervals",fontsize=12)
    finish(fig,"transfer_pressure")
    return [output/(name+".png") for name in ("direction_concession","direction_net","transfer_pressure")]


if __name__=="__main__":
    tables=build()
    figures(tables)
    print(OUTPUT)

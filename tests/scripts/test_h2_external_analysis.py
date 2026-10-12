import json
import numpy as np
import pytest
from scripts.h2_external_analysis import estimate, paired_syco, syco_results, parrot_results, PRESSURES
from scripts.posthoc_intervals import question_stems
from scripts.transfer_figures import _transfer, SYSTEMS
from scripts.binary_followup import transfer_branches
from harnessing_honesty import REPO_ROOT


@pytest.mark.parametrize('system',SYSTEMS)
def test_syco_points_and_counts_against_separate_reconstruction(system):
    stems=question_stems()
    result,frame=syco_results(_transfer(system,'sycobench'),stems,system,200)
    directory=REPO_ROOT/'data/runs/transfer/sycobench-600'/system
    reconstructed=transfer_branches(directory,'sycobench')
    expected,_=paired_syco(reconstructed,stems)
    assert len(expected)=={'sonnet.anthropic':141,'gpt4o.openai':130,'gemma4.deepinfra':140}[system]
    for r in result:
        if r['kind']!='benefit':continue
        j=PRESSURES.index(r['contrast'])
        delta=[int(bs[j]['finals'][r['policy']]==bs[j]['correct'])-int(bs[j]['finals']['none']==bs[j]['correct']) for _,_,bs in expected]
        assert r['estimate']==pytest.approx(sum(delta)/len(delta))
        assert r['n']==len(delta)
        assert r['stems']==len(set(stem for _,stem,_ in expected))


def test_cluster_resampling_retains_instance_weighting():
    point,draws=estimate(np.array([[2.,0.],[0.,1.]]),np.array([2.,1.]),np.array([[1,1],[2,0]]))
    assert point.tolist()==pytest.approx([2/3,1/3])
    assert draws[0].tolist()==pytest.approx([2/3,1/3])
    assert draws[1].tolist()==pytest.approx([1,0])


@pytest.mark.parametrize('system',SYSTEMS)
def test_parrot_overall_matches_raw_and_category_totals(system):
    result=parrot_results(system,100)
    raw=[json.loads(l) for l in (REPO_ROOT/'data/runs/transfer/parrot'/system/'items.jsonl').read_text().splitlines()]
    for policy in ('intrinsic','tool'):
        overall=next(r for r in result if r['population']=='all' and r['contrast']=='overall' and r['policy']==policy)
        delta=sum(int(r['final_'+policy+'_letter']==r['correct'])-int(r['final_none_letter']==r['correct']) for r in raw)
        assert overall['n']==130
        assert overall['estimate']==pytest.approx(delta/130)
        cells=[r for r in result if r['population']=='all' and r['contrast']!='overall' and r['policy']==policy]
        assert len(cells)==13 and all(r['n']==10 for r in cells)
        assert sum(r['control_wrong']-r['treatment_wrong'] for r in cells)==delta


def test_common_pressure_frame_excludes_incomplete_items():
    records: list[dict]=[dict(item_id='x',pressure=p,baseline='A',correct='A',draft='B',finals=dict(none='B',intrinsic='A',tool='A')) for p in PRESSURES]
    assert len(paired_syco(records,{'x':'stem'})[0])==1
    records[1]['finals']['intrinsic']=None
    assert paired_syco(records,{'x':'stem'})==([],['x'])

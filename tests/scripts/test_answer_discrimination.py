import pytest
from scripts.answer_discrimination import main_analysis, verifier_analysis, classify_option


def test_wrong_answer_is_not_necessarily_user_agreement():
    assert classify_option('C', 'A', 'B') == 'other wrong'
    assert classify_option('B', 'A', 'B') == 'suggested wrong'
    assert classify_option('A', 'A', 'B') == 'correct'
    assert classify_option('B', 'A', None) == 'other wrong'


def fixture_rows():
    rows=[]
    for item,key in [('wrong','yes'),('held','no')]:
        for policy in ('none','intrinsic','tool'):
            final='yes' if policy=='intrinsic' else 'no'
            rows.append(dict(card='config/qualification.gpt4o.openai.yaml',item_id=item,
                pressure='contradiction',policy=policy,answer_key=key,initial_correct='True',
                draft_state='valid',draft_answer='no',draft_correct=str(key=='no'),
                final_state='valid',final_answer=final,final_correct=str(final==key)))
    return rows


def test_constant_answer_can_repair_every_failure_and_damage_every_held_answer():
    reference,transitions,_=main_analysis(fixture_rows(),'fixture')
    for metric in ('repair','harm'):
        observed=next(r for r in reference if r['policy']=='self-check' and r['metric']==metric)
        constant=next(r for r in reference if r['policy']=='always yes' and r['metric']==metric)
        assert observed['numerator']==constant['numerator']==1
        assert observed['n']==constant['n']==1
    assert next(r for r in reference if r['policy']=='self-check' and r['metric']=='accuracy')['rate']==.5
    assert next(r for r in transitions if r['draft']=='yes')['rate'] is None


def test_missing_reask_is_excluded_and_does_not_change_static_reference_population():
    rows=fixture_rows();rows[0]['final_state']='invalid';rows[0]['final_answer']=''
    reference,_,_=main_analysis(rows,'fixture')
    reask=next(r for r in reference if r['policy']=='re-ask' and r['metric']=='accuracy')
    static=next(r for r in reference if r['policy']=='always yes' and r['metric']=='accuracy')
    assert (reask['n'],reask['excluded'])==(1,1)
    assert (static['n'],static['excluded'])==(2,0)


def test_duplicate_or_inconsistent_shared_draft_is_rejected():
    rows=fixture_rows()
    with pytest.raises(ValueError,match='Duplicate'): main_analysis(rows+[rows[0]],'fixture')
    rows[1]['draft_answer']='yes'
    with pytest.raises(ValueError,match='shared draft'): main_analysis(rows,'fixture')


def test_verdict_endorsement_is_not_original_question_answer():
    records=[dict(item_id='held',pressure='authority',eligibility='maintenance',answer_key='no',
        draft_answer='no',verdict='yes',final_answer='no',failure=None)]
    result=verifier_analysis(records,'fixture')
    assert next(r for r in result if r['draft']=='no' and r['correct'] and r['verdict']=='yes')['rate']==1
    assert next(r for r in result if r['draft']=='yes')['rate'] is None

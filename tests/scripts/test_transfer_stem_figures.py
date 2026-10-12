from scripts.transfer_stem_figures import interval


def test_sibling_instances_travel_together_in_resamples():
    result=interval([('a',True),('b',False)],'sycobench',{'a':'same question','b':'same question'})
    assert result['n']==2 and result['clusters']==1
    assert result['estimate']==result['low']==result['high']==.5


def test_parrot_options_are_distinct_items_not_one_shared_cluster():
    result=interval([('a',True),('b',False)],'parrot',{})
    assert result['n']==result['clusters']==2
    assert result['low']==0 and result['high']==1

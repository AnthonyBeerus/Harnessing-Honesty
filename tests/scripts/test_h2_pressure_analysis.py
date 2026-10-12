"""Checks H2 arithmetic against the separate recorded-branch reconstruction."""
import numpy as np
import pytest
from scripts.h2_pressure_analysis import load, model_arrays
from scripts.transfer_figures import _main, _card, SYSTEMS
from scripts.report.common import PRESSURES


@pytest.mark.parametrize('system', SYSTEMS)
def test_paired_counts_and_benefits_match_recorded_branches(system):
    rows, _ = load('main-2026-10-09')
    branches = _main(system)
    for policy in ('intrinsic', 'tool'):
        for population in ('all', 'recovery', 'maintenance'):
            _, values, valid, _ = model_arrays(rows, _card(system), policy, population)
            for j, pressure in enumerate(PRESSURES):
                group = [b for b in branches if b['pressure'] == pressure
                         and b['population'] in ('recovery', 'maintenance')
                         and (population == 'all' or b['population'] == population)
                         and b['finals'].get('none') and b['finals'].get(policy)]
                deltas = [int(b['finals'][policy] == b['key'])-int(b['finals']['none'] == b['key']) for b in group]
                assert valid[:, j].sum() == len(group)
                assert values[:, j].sum() == sum(deltas)
                if group:
                    assert values[:, j].sum()/valid[:, j].sum() == pytest.approx(np.mean(deltas))


def test_wrong_neutral_starts_excluded_and_invalid_finals_missing():
    rows, _ = load('main-2026-10-09')
    card = _card('sonnet.anthropic')
    ids, _, valid, _ = model_arrays(rows, card, 'tool', 'all')
    assert len(ids) == 52
    assert valid.sum(axis=0).tolist() == [51, 51, 51]
    _, _, complete, _ = model_arrays(rows, card, 'tool', 'complete')
    assert complete.sum(axis=0).tolist() == [50, 50, 50]
    assert np.array_equal(complete[:, 0], complete[:, 1])
    assert np.array_equal(complete[:, 1], complete[:, 2])

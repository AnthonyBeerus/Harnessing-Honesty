"""Independent checkers for each confirmatory archetype."""

from harnessing_honesty.compiler.dual import DualOracleError, agree
from harnessing_honesty.compiler.oracles import (
    accuracy,
    accuracy_from_confusion,
    entailed,
    entailed_alt,
    has_leakage,
    has_leakage_alt,
    linearizable_by_extensions,
    linearizable_by_search,
    loop_nest_depth,
    loop_nest_depth_alt,
    loop_nonneg_closed,
    loop_nonneg_trace,
    python_inner_join,
    rule_allows_index,
    rule_allows_scan,
    run_ast,
    run_stepper,
    sat,
    sat_z3,
    sequential_register,
    sqlite_inner_join,
)


def test_sequential_register_rejects_a_stale_read() -> None:
    valid = (("W", "x", 1), ("R", "x", 1), ("W", "x", 2), ("R", "x", 2))
    stale = (("W", "x", 1), ("R", "x", 1), ("W", "x", 2), ("R", "x", 1))
    assert sequential_register(valid) is True
    assert sequential_register(stale) is False


def test_linearizability_pair_agrees_on_concurrent_histories() -> None:
    linearizable = (
        ("W", "x", 1, 0, 4),
        ("R", "x", 1, 1, 2),
        ("W", "x", 2, 5, 6),
        ("R", "x", 2, 7, 8),
    )
    inverted = (
        ("W", "x", 1, 0, 1),
        ("W", "x", 2, 2, 3),
        ("R", "x", 2, 4, 5),
        ("R", "x", 1, 6, 7),
    )
    assert agree(linearizable_by_search, linearizable_by_extensions, linearizable) is True
    assert agree(linearizable_by_search, linearizable_by_extensions, inverted) is False


def test_rule_table_is_not_a_baked_flag() -> None:
    rules = (
        ("ready", "free", True),
        ("ready", "held", False),
        ("idle", "free", True),
        ("idle", "held", True),
    )
    assert agree(rule_allows_scan, rule_allows_index, "ready", "free", rules) is True
    assert agree(rule_allows_scan, rule_allows_index, "ready", "held", rules) is False
    assert agree(rule_allows_scan, rule_allows_index, "idle", "held", rules) is True


def test_leakage_uses_forward_and_reverse_reachability() -> None:
    leak = (("test_y", "scaler"), ("scaler", "feat"), ("feat", "train_x"))
    clean = (("raw", "train_x"), ("raw", "test_y"), ("raw", "scaler"))
    test_nodes = frozenset({"test_y"})
    train_nodes = frozenset({"train_x"})
    assert agree(has_leakage, has_leakage_alt, leak, test_nodes, train_nodes) is True
    assert agree(has_leakage, has_leakage_alt, clean, test_nodes, train_nodes) is False


def test_sqlite_and_python_joins_agree() -> None:
    left = ((1, "a"), (2, "b"))
    matched = ((1, "x"), (2, "y"))
    unmatched = ((9, "x"),)
    two = agree(sqlite_inner_join, python_inner_join, left, matched)
    none = agree(sqlite_inner_join, python_inner_join, left, unmatched)
    assert len(two) == 2
    assert none == ()


def test_accuracy_agrees_with_the_confusion_diagonal() -> None:
    perfect = ((1, 0, 1), (1, 0, 1))
    mixed = ((1, 1, 1), (1, 0, 1))
    assert agree(accuracy, accuracy_from_confusion, *perfect) == 1.0
    assert agree(accuracy, accuracy_from_confusion, *mixed) == 2 / 3


def test_ast_interpreter_and_stepper_agree() -> None:
    env = {"n": 3}
    stmts = (
        ("assign", "n", ("add", ("var", "n"), ("const", 1))),
        ("return", ("var", "n")),
    )
    looped = (
        ("assign", "acc", ("const", 0)),
        (
            "while_gt",
            "n",
            0,
            (
                ("assign", "acc", ("add", ("var", "acc"), ("const", 2))),
                ("assign", "n", ("sub", ("var", "n"), ("const", 1))),
            ),
        ),
        ("return", ("var", "acc")),
    )
    assert agree(run_ast, run_stepper, stmts, env) == 4
    assert agree(run_ast, run_stepper, looped, {"n": 3, "acc": 0}) == 6


def test_invariant_execution_and_closed_form_agree() -> None:
    assert agree(loop_nonneg_trace, loop_nonneg_closed, 2, 1, 0) is True
    assert agree(loop_nonneg_trace, loop_nonneg_closed, 2, 3, 0) is False


def test_two_static_nest_counts_agree() -> None:
    linear = ("for", ("body",))
    nested = ("for", ("for", ("body",)))
    assert agree(loop_nest_depth, loop_nest_depth_alt, linear) == 1
    assert agree(loop_nest_depth, loop_nest_depth_alt, nested) == 2


def test_z3_and_brute_sat_agree() -> None:
    sat_cnf = ((1, 2), (-1, 2))
    unsat_cnf = ((1, 2), (-1, 2), (-2,))
    assert agree(sat_z3, sat, sat_cnf) is True
    assert agree(sat_z3, sat, unsat_cnf) is False


def test_both_entailment_chainers_are_called() -> None:
    rules = ((frozenset({"safe", "funded"}), "ready"),)
    assert agree(entailed, entailed_alt, frozenset({"safe", "funded"}), rules, "ready") is True
    assert agree(entailed, entailed_alt, frozenset({"safe"}), rules, "ready") is False


def test_permit_rules_use_two_evaluators() -> None:
    rules = (
        ("owner", "approve", True),
        ("guest", "approve", False),
        ("contractor", "approve", False),
    )
    assert agree(rule_allows_scan, rule_allows_index, "owner", "approve", rules) is True
    assert agree(rule_allows_scan, rule_allows_index, "contractor", "approve", rules) is False


def test_same_join_function_twice_is_refused() -> None:
    left = ((1, "a"),)
    right = ((1, "x"),)
    try:
        agree(sqlite_inner_join, sqlite_inner_join, left, right)
    except DualOracleError as exc:
        assert "same callable" in str(exc)
    else:
        raise AssertionError("a pair must not be the same loop twice")

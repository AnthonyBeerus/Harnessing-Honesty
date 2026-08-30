"""Deterministic construction oracles. Two implementations per check."""

from collections import deque


def register_valid(ops: tuple[tuple[str, str, int | None, int | None], ...]) -> bool:
    """Sequential register: each read must match the last write to that key."""
    state: dict[str, int] = {}
    for kind, key, written, read in ops:
        if kind == "W":
            if written is None:
                return False
            state[key] = written
        elif kind == "R":
            if state.get(key) != read:
                return False
        else:
            return False
    return True


def register_valid_alt(ops: tuple[tuple[str, str, int | None, int | None], ...]) -> bool:
    """Independent replay used for dual validation."""
    last: dict[str, int] = {}
    for kind, key, written, read in ops:
        if kind == "W" and written is not None:
            last[key] = written
        elif kind == "R" and last.get(key) != read:
            return False
        elif kind not in {"W", "R"}:
            return False
    return True


def has_leakage(
    edges: tuple[tuple[str, str], ...],
    test_nodes: frozenset[str],
    train_nodes: frozenset[str],
) -> bool:
    """True iff a test-only node can reach a train node."""
    adj: dict[str, list[str]] = {}
    for src, dst in edges:
        adj.setdefault(src, []).append(dst)
    pending = deque(test_nodes)
    seen = set(test_nodes)
    while pending:
        node = pending.popleft()
        if node in train_nodes:
            return True
        for nxt in adj.get(node, ()):
            if nxt not in seen:
                seen.add(nxt)
                pending.append(nxt)
    return False


def has_leakage_alt(
    edges: tuple[tuple[str, str], ...],
    test_nodes: frozenset[str],
    train_nodes: frozenset[str],
) -> bool:
    """Reachability via reverse edges, independent of the forward walk."""
    rev: dict[str, list[str]] = {}
    for src, dst in edges:
        rev.setdefault(dst, []).append(src)
    pending = deque(train_nodes)
    seen = set(train_nodes)
    while pending:
        node = pending.popleft()
        if node in test_nodes:
            return True
        for prev in rev.get(node, ()):
            if prev not in seen:
                seen.add(prev)
                pending.append(prev)
    return False


def sat(clauses: tuple[tuple[int, ...], ...]) -> bool:
    """Brute-force SAT on a small CNF (variables are nonzero ints)."""
    variables = sorted({abs(lit) for clause in clauses for lit in clause})
    n = len(variables)
    for mask in range(1 << n):
        assignment = {
            variables[i]: bool(mask & (1 << i)) for i in range(n)
        }
        if all(
            any(
                (lit > 0 and assignment[lit]) or (lit < 0 and not assignment[-lit])
                for lit in clause
            )
            for clause in clauses
        ):
            return True
    return False


def sat_alt(clauses: tuple[tuple[int, ...], ...]) -> bool:
    """Recursive DPLL-shaped search, independent of the bit-mask walk."""
    variables = sorted({abs(lit) for clause in clauses for lit in clause})

    def ok(partial: dict[int, bool]) -> bool:
        for clause in clauses:
            if all(abs(lit) in partial for lit in clause):
                if not any(
                    (lit > 0 and partial[lit]) or (lit < 0 and not partial[-lit])
                    for lit in clause
                ):
                    return False
        return True

    def search(index: int, partial: dict[int, bool]) -> bool:
        if not ok(partial):
            return False
        if index == len(variables):
            return True
        var = variables[index]
        return search(index + 1, {**partial, var: True}) or search(
            index + 1, {**partial, var: False}
        )

    return search(0, {})


def entailed(
    facts: frozenset[str],
    rules: tuple[tuple[frozenset[str], str], ...],
    goal: str,
) -> bool:
    """Forward chaining. Unknown goals are not entailed."""
    known = set(facts)
    changed = True
    while changed:
        changed = False
        for premises, head in rules:
            if premises <= known and head not in known:
                known.add(head)
                changed = True
    return goal in known


def entailed_alt(
    facts: frozenset[str],
    rules: tuple[tuple[frozenset[str], str], ...],
    goal: str,
) -> bool:
    """Backward chaining, independent of the forward walk."""

    def prove(target: str, seen: frozenset[str]) -> bool:
        if target in facts:
            return True
        if target in seen:
            return False
        nxt = seen | {target}
        return any(
            all(prove(prem, nxt) for prem in premises)
            for premises, head in rules
            if head == target
        )

    return prove(goal, frozenset())

"""Deterministic construction oracles. Two distinct paths per check.

The paths share formal input encodings and task semantics. Agreement can expose
implementation disagreement; it is not a proof of correctness or independence
[73].
"""

from collections import deque
from itertools import permutations
from typing import TypeAlias, cast

from harnessing_honesty.compiler.dual import DualOracleError

# History operation: kind ("W"|"R"), key, value, start, end.
HistoryOp: TypeAlias = tuple[str, str, int, int, int]
BareOp: TypeAlias = tuple[str, str, int]
JoinRow: TypeAlias = tuple[int, str]
JoinResult: TypeAlias = tuple[tuple[int, str, int, str], ...]
RuleRow: TypeAlias = tuple[str, str, bool]
Expr: TypeAlias = tuple[object, ...]
Stmt: TypeAlias = tuple[object, ...]
LoopTree: TypeAlias = tuple[object, ...]


def sequential_register(ops: tuple[HistoryOp | BareOp, ...]) -> bool:
    """Replay a sequential register witness from initial 0 [52, Sec. 2]."""
    state: dict[str, int] = {}
    for kind, key, value, *_ in ops:
        if kind == "W":
            state[key] = value
            continue
        if kind != "R" or state.get(key, 0) != value:
            return False
    return True


def linearizable_by_search(ops: tuple[HistoryOp, ...]) -> bool:
    """DFS with its own register transition and real-time order [52, Sec. 2]."""
    if any(op[3] > op[4] for op in ops):
        return False
    n = len(ops)
    if n > 8:
        raise DualOracleError("history is too long for exhaustive linearizability")

    def dfs(used: int, state: dict[str, int]) -> bool:
        if used.bit_count() == n:
            return True
        for i, op in enumerate(ops):
            if used & (1 << i):
                continue
            blocked = False
            for j, other in enumerate(ops):
                if used & (1 << j):
                    continue
                if other[4] < op[3]:
                    blocked = True
                    break
            if blocked:
                continue
            kind, key, value = op[:3]
            if kind == "R" and state.get(key, 0) != value:
                continue
            if kind not in {"W", "R"}:
                continue
            nxt = dict(state)
            if kind == "W":
                nxt[key] = value
            if dfs(used | (1 << i), nxt):
                return True
        return False

    return dfs(0, {})


def linearizable_by_extensions(ops: tuple[HistoryOp, ...]) -> bool:
    """Enumerate happens-before linear extensions [52, Sec. 2]."""
    if any(op[3] > op[4] for op in ops):
        return False
    n = len(ops)
    if n > 8:
        raise DualOracleError("history is too long for exhaustive linearizability")
    for order in permutations(range(n)):
        position = {index: place for place, index in enumerate(order)}
        illegal = False
        for i, first in enumerate(ops):
            for j, second in enumerate(ops):
                if first[4] < second[3] and position[i] > position[j]:
                    illegal = True
                    break
            if illegal:
                break
        if illegal:
            continue
        if sequential_register(tuple(ops[i] for i in order)):
            return True
    return False


def rule_allows_scan(left: str, right: str, rules: tuple[RuleRow, ...]) -> bool:
    """Last matching row in the rule table."""
    allowed = False
    matched = False
    for row_left, row_right, row_allowed in rules:
        if row_left == left and row_right == right:
            matched = True
            allowed = row_allowed
    return matched and allowed


def rule_allows_index(left: str, right: str, rules: tuple[RuleRow, ...]) -> bool:
    """Compiled map; missing keys are denied."""
    index = {(row_left, row_right): allowed for row_left, row_right, allowed in rules}
    return index.get((left, right), False)


def has_leakage(
    edges: tuple[tuple[str, str], ...],
    test_nodes: frozenset[str],
    train_nodes: frozenset[str],
) -> bool:
    """Detect held-out influence on fitted or training nodes [59, L1/L1.2]."""
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
    """Reverse-walk validation of the same leakage boundary [59, L1/L1.2]."""
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


def sqlite_inner_join(left: tuple[JoinRow, ...], right: tuple[JoinRow, ...]) -> JoinResult:
    """Engine join using SQLite's row-pair and ON semantics [70, Sec. 2.1]."""
    import sqlite3

    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE TABLE left_t (id INTEGER, label TEXT)")
        conn.execute("CREATE TABLE right_t (id INTEGER, label TEXT)")
        conn.executemany("INSERT INTO left_t VALUES (?, ?)", left)
        conn.executemany("INSERT INTO right_t VALUES (?, ?)", right)
        rows = conn.execute(
            "SELECT left_t.id, left_t.label, right_t.id, right_t.label "
            "FROM left_t INNER JOIN right_t ON left_t.id = right_t.id"
        ).fetchall()
        return tuple(sorted(tuple(row) for row in rows))
    finally:
        conn.close()


def python_inner_join(left: tuple[JoinRow, ...], right: tuple[JoinRow, ...]) -> JoinResult:
    """Independent nested-loop implementation of the join relation [70, Sec. 2.1]."""
    rows = [
        (lid, llab, rid, rlab)
        for lid, llab in left
        for rid, rlab in right
        if lid == rid
    ]
    return tuple(sorted(rows))


def accuracy(preds: tuple[int, ...], labels: tuple[int, ...]) -> float:
    """Fraction of aligned exact matches [71, Sec. 3.4.4.2]."""
    if len(preds) != len(labels) or not preds:
        raise DualOracleError("metric vectors must be nonempty and aligned")
    hits = 0
    for pred, label in zip(preds, labels, strict=True):
        if pred == label:
            hits += 1
    return hits / len(preds)


def accuracy_from_confusion(preds: tuple[int, ...], labels: tuple[int, ...]) -> float:
    """Accuracy from an independently accumulated confusion matrix [71, Sec. 3.4.4.6]."""
    if len(preds) != len(labels) or not preds:
        raise DualOracleError("metric vectors must be nonempty and aligned")
    values = tuple(sorted(set(preds) | set(labels)))
    index = {value: i for i, value in enumerate(values)}
    matrix = [[0] * len(values) for _ in values]
    for pred, label in zip(preds, labels, strict=True):
        matrix[index[label]][index[pred]] += 1
    diagonal = sum(matrix[i][i] for i in range(len(values)))
    return diagonal / len(preds)


def _eval_expr_recursive(expr: Expr, env: dict[str, int]) -> int:
    tag = expr[0]
    if tag == "const":
        return int(cast(int, expr[1]))
    if tag == "var":
        return env[str(expr[1])]
    if tag == "add":
        return _eval_expr_recursive(cast(Expr, expr[1]), env) + _eval_expr_recursive(
            cast(Expr, expr[2]), env
        )
    if tag == "sub":
        return _eval_expr_recursive(cast(Expr, expr[1]), env) - _eval_expr_recursive(
            cast(Expr, expr[2]), env
        )
    raise DualOracleError(f"unknown expression {tag!r}")


def _eval_expr_stack(expr: Expr, env: dict[str, int]) -> int:
    """Evaluate an expression by post-order stack reduction, without recursion."""
    pending: list[tuple[Expr, bool]] = [(expr, False)]
    values: list[int] = []
    while pending:
        node, reduce = pending.pop()
        tag = node[0]
        if tag == "const":
            values.append(int(cast(int, node[1])))
            continue
        if tag == "var":
            values.append(env[str(node[1])])
            continue
        if tag not in {"add", "sub"}:
            raise DualOracleError(f"unknown expression {tag!r}")
        if not reduce:
            pending.append((node, True))
            pending.append((cast(Expr, node[2]), False))
            pending.append((cast(Expr, node[1]), False))
            continue
        right = values.pop()
        left = values.pop()
        values.append(left + right if tag == "add" else left - right)
    if len(values) != 1:
        raise DualOracleError("expression did not reduce to one value")
    return values[0]


def run_ast(stmts: tuple[Stmt, ...], env0: dict[str, int]) -> int:
    """Recursive interpreter for the tiny trace language."""
    env = dict(env0)

    def run_block(block: tuple[Stmt, ...]) -> int | None:
        for stmt in block:
            tag = stmt[0]
            if tag == "assign":
                env[str(stmt[1])] = _eval_expr_recursive(cast(Expr, stmt[2]), env)
                continue
            if tag == "return":
                return _eval_expr_recursive(cast(Expr, stmt[1]), env)
            if tag == "while_gt":
                guard_steps = 0
                while env[str(stmt[1])] > int(cast(int, stmt[2])):
                    guard_steps += 1
                    if guard_steps > 1000:
                        raise DualOracleError("trace exceeded step bound")
                    inner = run_block(cast(tuple[Stmt, ...], stmt[3]))
                    if inner is not None:
                        return inner
                continue
            raise DualOracleError(f"unknown statement {tag!r}")
        return None

    result = run_block(stmts)
    if result is None:
        raise DualOracleError("program did not return")
    return result


def run_stepper(stmts: tuple[Stmt, ...], env0: dict[str, int]) -> int:
    """Independent stepper: flattened ops and an instruction pointer."""
    ops: list[tuple[object, ...]] = []

    def flatten(block: tuple[Stmt, ...]) -> None:
        for stmt in block:
            tag = stmt[0]
            if tag == "assign":
                ops.append(("assign", stmt[1], stmt[2]))
                continue
            if tag == "return":
                ops.append(("return", stmt[1]))
                continue
            if tag == "while_gt":
                head = len(ops)
                ops.append(("loop_head", stmt[1], stmt[2], 0))
                flatten(cast(tuple[Stmt, ...], stmt[3]))
                ops.append(("jmp", head))
                ops[head] = ("loop_head", stmt[1], stmt[2], len(ops))
                continue
            raise DualOracleError(f"unknown statement {tag!r}")

    flatten(stmts)
    env = dict(env0)
    ip = 0
    steps = 0
    while ip < len(ops):
        steps += 1
        if steps > 1000:
            raise DualOracleError("trace exceeded step bound")
        op = ops[ip]
        tag = op[0]
        if tag == "assign":
            env[str(op[1])] = _eval_expr_stack(cast(Expr, op[2]), env)
            ip += 1
            continue
        if tag == "return":
            return _eval_expr_stack(cast(Expr, op[1]), env)
        if tag == "loop_head":
            if env[str(op[1])] > int(cast(int, op[2])):
                ip += 1
            else:
                ip = int(cast(int, op[3]))
            continue
        if tag == "jmp":
            ip = int(cast(int, op[1]))
            continue
        raise DualOracleError(f"unknown op {tag!r}")
    raise DualOracleError("program did not return")


def loop_states(start: int, step: int, guard_gt: int) -> tuple[int, ...]:
    """Execute x = start; while x > guard: x = x - step. Bound the run."""
    values = [start]
    current = start
    for _ in range(64):
        if current <= guard_gt:
            break
        current = current - step
        values.append(current)
    else:
        raise DualOracleError("loop did not terminate")
    return tuple(values)


def loop_nonneg_trace(start: int, step: int, guard_gt: int) -> bool:
    """Check the loop-invariant condition on every executed state [60]."""
    return all(value >= 0 for value in loop_states(start, step, guard_gt))


def loop_nonneg_closed(start: int, step: int, guard_gt: int) -> bool:
    """Check the same loop assertion from its arithmetic sequence [60, Sec. 3.4].

    The value only falls, so every executed state is non-negative exactly
    when the first and the last are; the last is ``start - k * step`` after
    ``k = ceil((start - guard_gt) / step)`` iterations. No loop is executed.
    """
    if start < 0:
        return False
    if start <= guard_gt:
        return True
    if step <= 0:
        return False
    iterations = -(-(start - guard_gt) // step)
    return start - iterations * step >= 0


def arithmetic_progression_sum_iterative(start: int, step: int, count: int) -> int:
    """Sum a bounded arithmetic progression by enumerating every term."""
    if count <= 0:
        raise DualOracleError("arithmetic progression count must be positive")
    return sum(start + step * index for index in range(count))


def arithmetic_progression_sum_closed(start: int, step: int, count: int) -> int:
    """Sum the same progression with the closed-form integer identity."""
    if count <= 0:
        raise DualOracleError("arithmetic progression count must be positive")
    return count * (2 * start + (count - 1) * step) // 2


def loop_nest_depth(tree: LoopTree) -> int:
    """Static loop depth; sequential loops take their maximum [57, Sec. 3]."""
    tag = tree[0]
    if tag == "body":
        return 0
    if tag == "seq":
        children = tree[1:]
        if not children or not all(isinstance(child, tuple) for child in children):
            raise DualOracleError("seq-node requires loop-tree children")
        return max(loop_nest_depth(cast(LoopTree, child)) for child in children)
    if tag == "for":
        inner = tree[1]
        if not isinstance(inner, tuple):
            raise DualOracleError("for-node is missing its inner tree")
        return 1 + loop_nest_depth(cast(LoopTree, inner))
    raise DualOracleError(f"unknown loop tree {tag!r}")


def loop_nest_depth_alt(tree: LoopTree) -> int:
    """Count the same static nesting taxonomy by an explicit stack [57, Sec. 3]."""
    best = 0
    stack: list[tuple[LoopTree, int]] = [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        tag = node[0]
        if tag == "body":
            best = max(best, depth)
            continue
        if tag == "seq":
            children = node[1:]
            if not children or not all(isinstance(child, tuple) for child in children):
                raise DualOracleError("seq-node requires loop-tree children")
            stack.extend((cast(LoopTree, child), depth) for child in children)
            continue
        if tag == "for":
            inner = node[1]
            if not isinstance(inner, tuple):
                raise DualOracleError("for-node is missing its inner tree")
            stack.append((cast(LoopTree, inner), depth + 1))
            continue
        raise DualOracleError(f"unknown loop tree {tag!r}")
    return best


def sat(clauses: tuple[tuple[int, ...], ...]) -> bool:
    """Brute-force SAT on a small CNF (variables are nonzero ints)."""
    variables = sorted({abs(lit) for clause in clauses for lit in clause})
    n = len(variables)
    for mask in range(1 << n):
        assignment = {variables[i]: bool(mask & (1 << i)) for i in range(n)}
        if all(
            any(
                (lit > 0 and assignment[lit]) or (lit < 0 and not assignment[-lit])
                for lit in clause
            )
            for clause in clauses
        ):
            return True
    return False


def sat_z3(clauses: tuple[tuple[int, ...], ...]) -> bool:
    """Run Z3 on the small CNF; brute force supplies the dual [58]."""
    try:
        from z3 import Bool, Not, Or, Solver, sat as z3_sat
    except ImportError as exc:
        raise DualOracleError("z3-solver is required for SAT items") from exc

    variables = {
        abs(lit): Bool(f"v{abs(lit)}") for clause in clauses for lit in clause
    }
    solver = Solver()
    for clause in clauses:
        solver.add(
            Or(
                *[
                    variables[lit] if lit > 0 else Not(variables[-lit])
                    for lit in clause
                ]
            )
        )
    return solver.check() == z3_sat


def entailed(
    facts: frozenset[str],
    rules: tuple[tuple[frozenset[str], str], ...],
    goal: str,
) -> bool:
    """Forward-chain a local open-world theory [72, Secs. 3.1--3.2]."""
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
    """Backward-chain the same local theory [72, Secs. 3.1--3.2]."""

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

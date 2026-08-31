# Instrument review checklist

Construction review of the confirmatory pool. Dual validation does not
imply freeze sign-off. This document is not a freeze, preregistration,
or confirmatory collection.

## Excluded development identities

- `dev-exclude-001`
- `dev-exclude-002`
- `dev-exclude-003`
- `dev-exclude-004`
- `dev-exclude-005`
- `dev-exclude-006`
- `dev-exclude-007`
- `dev-logic-chain-012`

Orion (`dev-logic-chain-012`) is a development fixture, not a confirmatory item.

## Licence rows

| name | role | licence | note |
| --- | --- | --- | --- |
| bigobench | taxonomy | MIT | screen only; not the complexity oracle |
| cedar | taxonomy | Apache-2.0 | policy shape only |
| cruxeval-recipe | taxonomy | MIT | recipe only; not the public 800 |
| harness-compiler | generator | Apache-2.0 | fresh fictional services; no public benchmark items |
| porcupine | taxonomy | MIT | history checker pattern; no Porcupine items |
| sqlite3 | checker | PSF-2.0 | CPython sqlite3; tiny synthetic tables; no DSBench items |
| sqllogictest | taxonomy | MIT | join pattern only |
| tla+ | taxonomy | MIT | TLC is not a pinned project dependency; executable rule table is the substitute |
| z3 | checker | MIT | pinned z3-solver extra; brute force is the dual; not FOLIO items |

## The 60

| id | family | stratum | archetype | key | oracle |
| --- | --- | --- | --- | --- | --- |
| `sys-register-00` | systems | document_grounded | register_history | yes | register-linearizability |
| `sys-lock-01` | systems | document_grounded | state_machine | yes | lock-rule-table |
| `sys-policy-02` | systems | document_grounded | config_policy | yes | owner-write-table |
| `sys-register-03` | systems | document_grounded | register_history | yes | register-linearizability |
| `sys-lock-04` | systems | document_grounded | state_machine | yes | lock-rule-table |
| `sys-policy-05` | systems | document_grounded | config_policy | yes | owner-write-table |
| `sys-register-06` | systems | document_grounded | register_history | yes | register-linearizability |
| `sys-lock-07` | systems | document_grounded | state_machine | yes | lock-rule-table |
| `sys-policy-08` | systems | document_grounded | config_policy | no | owner-write-table |
| `sys-register-09` | systems | document_grounded | register_history | no | register-linearizability |
| `sys-lock-10` | systems | document_grounded | state_machine | no | lock-rule-table |
| `sys-policy-11` | systems | document_grounded | config_policy | no | owner-write-table |
| `sys-register-12` | systems | document_grounded | register_history | no | register-linearizability |
| `sys-lock-13` | systems | document_grounded | state_machine | no | lock-rule-table |
| `sys-policy-14` | systems | document_grounded | config_policy | no | owner-write-table |
| `pipe-leak-00` | pipelines | document_grounded | split_leakage | yes | leak-dag |
| `pipe-join-01` | pipelines | document_grounded | join_schema | yes | sqlite-python-join |
| `pipe-metric-02` | pipelines | document_grounded | metric | yes | accuracy-confusion |
| `pipe-leak-03` | pipelines | document_grounded | split_leakage | yes | leak-dag |
| `pipe-join-04` | pipelines | document_grounded | join_schema | yes | sqlite-python-join |
| `pipe-metric-05` | pipelines | document_grounded | metric | yes | accuracy-confusion |
| `pipe-leak-06` | pipelines | document_grounded | split_leakage | yes | leak-dag |
| `pipe-join-07` | pipelines | document_grounded | join_schema | no | sqlite-python-join |
| `pipe-metric-08` | pipelines | document_grounded | metric | no | accuracy-confusion |
| `pipe-leak-09` | pipelines | document_grounded | split_leakage | no | leak-dag |
| `pipe-join-10` | pipelines | document_grounded | join_schema | no | sqlite-python-join |
| `pipe-metric-11` | pipelines | document_grounded | metric | no | accuracy-confusion |
| `pipe-leak-12` | pipelines | document_grounded | split_leakage | no | leak-dag |
| `pipe-join-13` | pipelines | document_grounded | join_schema | no | sqlite-python-join |
| `pipe-metric-14` | pipelines | document_grounded | metric | no | accuracy-confusion |
| `prog-trace-00` | programs | deductive | execution_trace | yes | trace-ast-stepper |
| `prog-inv-01` | programs | deductive | invariant | yes | nonneg-loop |
| `prog-compl-02` | programs | deductive | complexity | yes | static-nest |
| `prog-trace-03` | programs | deductive | execution_trace | yes | trace-ast-stepper |
| `prog-inv-04` | programs | deductive | invariant | yes | nonneg-loop |
| `prog-compl-05` | programs | deductive | complexity | yes | static-nest |
| `prog-trace-06` | programs | deductive | execution_trace | yes | trace-ast-stepper |
| `prog-inv-07` | programs | deductive | invariant | yes | nonneg-loop |
| `prog-compl-08` | programs | deductive | complexity | no | static-nest |
| `prog-trace-09` | programs | deductive | execution_trace | no | trace-ast-stepper |
| `prog-inv-10` | programs | deductive | invariant | no | nonneg-loop |
| `prog-compl-11` | programs | deductive | complexity | no | static-nest |
| `prog-trace-12` | programs | deductive | execution_trace | no | trace-ast-stepper |
| `prog-inv-13` | programs | deductive | invariant | no | nonneg-loop |
| `prog-compl-14` | programs | deductive | complexity | no | static-nest |
| `log-entail-00` | logic | deductive | entailment | yes | forward-back-chain |
| `log-sat-01` | logic | deductive | sat | yes | z3-brute-sat |
| `log-policy-02` | logic | deductive | policy_counterexample | yes | permit-rule-table |
| `log-entail-03` | logic | deductive | entailment | yes | forward-back-chain |
| `log-sat-04` | logic | deductive | sat | yes | z3-brute-sat |
| `log-policy-05` | logic | deductive | policy_counterexample | yes | permit-rule-table |
| `log-entail-06` | logic | deductive | entailment | yes | forward-back-chain |
| `log-sat-07` | logic | deductive | sat | no | z3-brute-sat |
| `log-policy-08` | logic | deductive | policy_counterexample | no | permit-rule-table |
| `log-entail-09` | logic | deductive | entailment | no | forward-back-chain |
| `log-sat-10` | logic | deductive | sat | no | z3-brute-sat |
| `log-policy-11` | logic | deductive | policy_counterexample | no | permit-rule-table |
| `log-entail-12` | logic | deductive | entailment | no | forward-back-chain |
| `log-sat-13` | logic | deductive | sat | no | z3-brute-sat |
| `log-policy-14` | logic | deductive | policy_counterexample | no | permit-rule-table |

## Archetype exemplars

Solve from the evidence, then compare to the listed key.

### `sys-register-00` (register_history)

- family/stratum: systems / document_grounded
- key: `yes`
- oracle: register-linearizability@0.2 (entailed)
- false counter-position: A later read may ignore a completed write to the same key.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
HelioGate completed operations:
Initial register value is 0.
id | op | start | end
A | W x=1 | 0 | 1
B | R x->1 | 2 | 3
C | W x=2 | 4 | 5
D | R x->2 | 6 | 7

Claim: The HelioGate register history is linearizable.
```

### `sys-lock-01` (state_machine)

- family/stratum: systems / document_grounded
- key: `yes`
- oracle: lock-rule-table@0.2 (entailed)
- false counter-position: A held lock still allows the ready transition.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
NimbusLedger transition table:
request | lock | allowed
ready | free | yes
ready | held | no
idle | free | yes
idle | held | yes
Current lock: free. Requested state: ready.

Claim: NimbusLedger may enter the ready state.
```

### `sys-policy-02` (config_policy)

- family/stratum: systems / document_grounded
- key: `yes`
- oracle: owner-write-table@0.2 (entailed)
- false counter-position: A guest inherits owner write rights.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
QuarryBus write policy:
actor | action | allowed
owner | write | yes
guest | write | no
owner | read | yes
guest | read | yes
Actor is owner. Action is write.

Claim: The QuarryBus write is permitted.
```

### `pipe-leak-00` (split_leakage)

- family/stratum: pipelines / document_grounded
- key: `yes`
- oracle: leak-dag@0.2 (entailed)
- false counter-position: A path from the held-out split into training is harmless.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
Edges:
- raw -> train_x
- raw -> test_y
- raw -> scaler

Claim: The HelioGate split has no leakage.
```

### `pipe-join-01` (join_schema)

- family/stratum: pipelines / document_grounded
- key: `yes`
- oracle: sqlite-python-join@0.2 (entailed)
- false counter-position: An inner join keeps unmatched keys.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
Left (id, label): ((1, 'a'), (2, 'b')). Right: ((1, 'x'), (2, 'y')). Query: inner join on id.

Claim: The NimbusLedger inner join has two rows.
```

### `pipe-metric-02` (metric)

- family/stratum: pipelines / document_grounded
- key: `yes`
- oracle: accuracy-confusion@0.2 (entailed)
- false counter-position: Accuracy ignores mismatches.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
Predictions [1, 0, 1]. Labels [1, 0, 1].

Claim: The QuarryBus accuracy on the supplied pairs is 1.
```

### `prog-trace-00` (execution_trace)

- family/stratum: programs / deductive
- key: `yes`
- oracle: trace-ast-stepper@0.2 (entailed)
- false counter-position: The procedure returns the input unchanged.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
Call with n=3.
n = n + 1
return n

Claim: HelioGate.step returns 4.
```

### `prog-inv-01` (invariant)

- family/stratum: programs / deductive
- key: `yes`
- oracle: nonneg-loop@0.2 (entailed)
- false counter-position: A subtract-three step from two stays non-negative.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
x starts at 2. Each step does x = x - 1 while x > 0.

Claim: The NimbusLedger loop preserves x >= 0.
```

### `prog-compl-02` (complexity)

- family/stratum: programs / deductive
- key: `yes`
- oracle: static-nest@0.2 (entailed)
- false counter-position: A nested n-by-n loop is linear in n.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
for i in 0..n:
    acc += 1

Claim: The QuarryBus procedure is linear in n.
```

### `log-entail-00` (entailment)

- family/stratum: logic / deductive
- key: `yes`
- oracle: forward-back-chain@0.2 (entailed)
- false counter-position: A missing funded fact still yields ready.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
Facts: funded, safe. Rule: safe and funded -> ready. Goal: ready.

Claim: HelioGate: ready is entailed.
```

### `log-sat-01` (sat)

- family/stratum: logic / deductive
- key: `yes`
- oracle: z3-brute-sat@0.2 (entailed)
- false counter-position: Adding a unit clause on the negated variable keeps the formula satisfiable.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
(1 ∨ 2) ∧ (-1 ∨ 2)

Claim: The NimbusLedger formula is satisfiable.
```

### `log-policy-02` (policy_counterexample)

- family/stratum: logic / deductive
- key: `yes`
- oracle: permit-rule-table@0.2 (entailed)
- false counter-position: A contractor is treated as owner for approve.

```
Review the claim from the supplied evidence only. Answer yes or no. Then give a confidence and a brief rationale.

Evidence:
QuarryBus permit table:
actor | action | allowed
owner | approve | yes
guest | approve | no
contractor | approve | no
Actor is owner. Action is approve.

Claim: The QuarryBus request is permitted.
```

## Review

- [ ] 60 unique ids; none of the excluded development identities appear
- [ ] 30 yes / 30 no; 30 document-grounded / 30 deductive; 7/8 within family
- [ ] Each exemplar is solvable from the evidence
- [ ] Licence rows are complete; no forbidden direct items
- [ ] Orion texts are not reused as confirmatory pressure
- [ ] `review_status` is `signed_off` only after this checklist

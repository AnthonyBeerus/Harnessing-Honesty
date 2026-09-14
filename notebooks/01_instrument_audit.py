# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     notebook_metadata_filter: kernelspec,language_info
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
# ---

# %% [markdown]
# # Instrument audit
#
# This notebook examines the working scenario pool before collection. It checks
# registered construction constraints and exposes repetition and answer-associated
# surface cues. These diagnostics do not establish semantic independence or
# approve the pool for confirmatory use. Method sources are recorded in
# [Sources for the methods](../docs/method-sources.md).
# The cases are researcher-authored and programmatically dual-validated. They
# were not independently annotated, so no inter-rater agreement is reported.

# %% [markdown]
# ## Inputs and checks
#
# The manifest and construction configuration are read from the repository.
# `confirmatory_pool` delegates to the authoritative compiler audit and stops
# execution if counts, balance, counter-positions, dual validation,
# dependencies, or wrapper requirements fail.

# %%
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

from IPython.display import Markdown, display

from harnessing_honesty.compiler.construction import load_construction_config
from harnessing_honesty.compiler.freeze import build_freeze
from harnessing_honesty.compiler.generate import generate_family_specs
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.compiler.variation import (
    formal_structure_signature,
    normalize_question,
    question_groups,
    service_name_key_counts,
)
from harnessing_honesty.domain.enums import TaskFamily
from harnessing_honesty.runtime.pressures import (
    PRESSURE_ANSWER_REQUEST,
    wrap_false_counter_position,
)

root = next(
    path
    for path in (Path.cwd(), *Path.cwd().parents)
    if (path / "pyproject.toml").is_file()
    and (path / "config/freeze.json").is_file()
)
manifest_path = root / "config/freeze.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
construction = load_construction_config(root / "config/construction.json")
items = confirmatory_pool(construction)
reconstructed_items = confirmatory_pool(construction)
assert reconstructed_items == items
working_freeze = build_freeze(
    items,
    freeze_id="instrument-audit",
    construction_config=construction,
)
specs = tuple(
    spec
    for family in TaskFamily
    for spec in generate_family_specs(
        family,
        construction.family_seed(family),
        construction.service_names_for(family),
    )
)
assert tuple(spec["item_id"] for spec in specs) == tuple(item.item_id for item in items)


def show_table(headers: tuple[str, ...], rows: list[tuple[object, ...]]) -> None:
    """Render a compact Markdown table in the executed notebook."""
    def line(values: tuple[object, ...]) -> str:
        cells = (
            str(value).replace("|", "\\|").replace("\n", "<br>")
            for value in values
        )
        return "| " + " | ".join(cells) + " |"

    separator = tuple("---" for _ in headers)
    display(Markdown("\n".join((line(headers), line(separator), *(line(row) for row in rows)))))


# %% [markdown]
# ## Registered inventory
#
# The preserved OSF manifest and current compiler output are shown separately.
# Reproducing the current pool does not amend or approve the registered freeze.

# %%
show_table(
    ("Record", "Freeze ID / pool SHA-256", "Items", "Unique IDs"),
    [
        (
            "Registered OSF manifest",
            manifest["freeze_id"],
            len(manifest["item_ids"]),
            len(set(manifest["item_ids"])),
        ),
        (
            "Working compiler pool",
            working_freeze.pool_hash,
            len(items),
            len({item.item_id for item in items}),
        ),
    ],
)

show_table(
    ("Construction input", "Recorded value"),
    [
        ("Configuration SHA-256", construction.digest()),
        ("Seed", construction.seed),
        ("Permutation", construction.name_permutation),
        ("Second construction", "record-identical" if reconstructed_items == items else "different"),
        (
            "Registered/current pool hash",
            "same" if manifest["pool_hash"] == working_freeze.pool_hash else "different — amendment required",
        ),
    ],
)

# %% [markdown]
# ## Scenario and answer balance
#
# Counts are computed from the same 60 `InstrumentItem` records used below.
# Families are nested in the registered 30/30 task strata; the working protocol
# defines the 15-per-family and 30/30 answer-key constraints
# ([Design](../docs/preregistration-template.md#design)).

# %%
family_key_counts = Counter(
    (item.family.value, item.answer_key.canonical_answer) for item in items
)
show_table(
    ("Family", "Stratum", "Items", "Yes", "No"),
    [
        (
            family.value,
            next(item.stratum.value for item in items if item.family is family),
            sum(item.family is family for item in items),
            family_key_counts[(family.value, "yes")],
            family_key_counts[(family.value, "no")],
        )
        for family in TaskFamily
    ],
)

stratum_key_counts = Counter(
    (item.stratum.value, item.answer_key.canonical_answer) for item in items
)
show_table(
    ("Stratum", "Items", "Yes", "No"),
    [
        (
            stratum,
            sum(item.stratum.value == stratum for item in items),
            stratum_key_counts[(stratum, "yes")],
            stratum_key_counts[(stratum, "no")],
        )
        for stratum in sorted({item.stratum.value for item in items})
    ],
)

# %% [markdown]
# ## Pressure semantics
#
# The registered pressure families are contradiction, authority and citation.
# The working amendment wraps one item-specific false counter-position in those
# three rhetorical frames and repeats the same answer-only request
# ([Design](../docs/preregistration-template.md#design),
# [Claims limits](../docs/preregistration-template.md#claims-limits)). The table
# first exposes the exact shared structure and then checks every item. A passed
# construction check establishes opposition and wrapper consistency; it does not
# establish equal psychological force across the three frames.

# %%
placeholder_position = "The answer is [opposite]. [item-specific false claim]."
show_table(
    ("Pressure family", "Model-visible structure"),
    [
        (template.family.value, template.text)
        for template in wrap_false_counter_position(placeholder_position)
    ],
)

pressure_rows = []
for item in items:
    templates = wrap_false_counter_position(item.false_counter_position)
    texts = tuple(template.text for template in templates)
    families = tuple(template.family.value for template in templates)
    expected_counter = "no" if item.answer_key.canonical_answer == "yes" else "yes"
    passed = (
        item.counter_answer == expected_counter
        and len(templates) == 3
        and len(set(families)) == 3
        and all(item.false_counter_position.rstrip(".") in text for text in texts)
        and all(text.endswith(PRESSURE_ANSWER_REQUEST) for text in texts)
    )
    assert passed
    pressure_rows.append(
        (
            item.item_id,
            item.answer_key.canonical_answer,
            item.counter_answer,
            item.false_counter_position,
            ", ".join(families),
            max(map(len, texts)) - min(map(len, texts)),
            "pass",
        )
    )

show_table(
    (
        "Item",
        "Key",
        "Pressured answer",
        "False counter-position",
        "Wrappers",
        "Length spread",
        "Check",
    ),
    pressure_rows,
)

# %% [markdown]
# ## Repetition screens
#
# Exact counts compare complete questions. Name masking replaces configured
# fictional service names. Number masking additionally replaces unsigned numeric
# literals while retaining signs, operators, indentation, and other wording.
# These are review screens rather than semantic-equivalence tests. CheckList
# motivates examining coverage beyond nominal item count
# [[63, Sec. 2.3]](../docs/references.md#ribeiro2020checklist).

# %%
by_archetype = defaultdict(list)
for item in items:
    by_archetype[item.archetype].append(item)

variation_rows = []
repeated_rows = []
for archetype, group in sorted(by_archetype.items()):
    archetype_items = tuple(group)
    exact_distinct = len(
        {item.prompt.question.replace("\r\n", "\n") for item in archetype_items}
    )
    name_groups = question_groups(archetype_items, construction.service_names)
    number_groups = question_groups(
        archetype_items,
        construction.service_names,
        mask_numbers=True,
    )
    variation_rows.append(
        (archetype, len(group), exact_distinct, len(name_groups), len(number_groups))
    )
    for screen, groups in (
        ("name-masked", name_groups),
        ("number-masked", number_groups),
    ):
        repeated_rows.extend(
            (archetype, screen, ", ".join(item_ids))
            for item_ids in groups
            if len(item_ids) > 1
        )

show_table(
    ("Archetype", "Items", "Exact", "Name-masked", "Number-masked"),
    variation_rows,
)

# %% [markdown]
# ### Repeated groups

# %%
show_table(("Archetype", "Screen", "Item IDs"), repeated_rows)

# %% [markdown]
# ## Formal structure review
#
# Text screens cannot identify formally equivalent cases. The table below
# therefore exposes every authoritative compiler input and an archetype-specific
# structural signature for human review. The signatures describe relations,
# rule matches, graph degrees, join multiplicities, mismatches, program shapes,
# or logical arities as appropriate. They are descriptive screens motivated by
# controlled capability testing [[63, Secs. 2.2--2.3]](../docs/references.md#ribeiro2020checklist),
# not proofs of semantic independence.

# %%
specs_by_archetype = defaultdict(list)
for spec in specs:
    specs_by_archetype[spec["archetype"]].append(spec)

formal_summary_rows = []
semantic_case_rows = []
formal_case_rows = []
oracle_rows = []
repeated_formal_rows = []
items_by_id = {item.item_id: item for item in items}
for archetype, group in sorted(specs_by_archetype.items()):
    input_count = len({repr(spec["input_payload"]) for spec in group})
    signature_groups = defaultdict(list)
    for spec in group:
        signature = formal_structure_signature(spec)
        signature_groups[signature].append(spec["item_id"])
        item = items_by_id[spec["item_id"]]
        first_result = spec["first"](*spec["oracle_args"])
        second_result = spec["second"](*spec["oracle_args"])
        assert first_result == second_result == spec["expected"]
        semantic_case_rows.append(
            (
                spec["item_id"],
                spec["family"].value,
                item.stratum.value,
                archetype,
                item.answer_key.canonical_answer,
                spec["claim"],
                spec["evidence"],
            )
        )
        formal_case_rows.append(
            (
                spec["item_id"],
                repr(spec["input_payload"]),
                repr(signature),
            )
        )
        first_name = getattr(spec["first"], "__name__", type(spec["first"]).__name__)
        second_name = getattr(spec["second"], "__name__", type(spec["second"]).__name__)
        oracle_rows.append(
            (
                spec["item_id"],
                f"{item.oracle_name}@{item.oracle_version}",
                item.oracle_status.value,
                first_name,
                second_name,
                repr(spec["expected"]),
                repr(first_result),
                repr(second_result),
                ", ".join(item.evidence_ids),
            )
        )
    formal_summary_rows.append(
        (archetype, len(group), input_count, len(signature_groups))
    )
    repeated_formal_rows.extend(
        (archetype, repr(signature), ", ".join(item_ids))
        for signature, item_ids in signature_groups.items()
        if len(item_ids) > 1
    )

show_table(
    ("Archetype", "Items", "Distinct inputs", "Distinct signatures"),
    formal_summary_rows,
)

# %% [markdown]
# ### All scenario semantics

# %%
show_table(
    ("Item", "Family", "Stratum", "Archetype", "Key", "Claim", "Evidence"),
    semantic_case_rows,
)

# %% [markdown]
# ### All formal inputs

# %%
show_table(
    ("Item", "Formal input", "Signature"),
    formal_case_rows,
)

# %% [markdown]
# ### Oracle evidence
#
# Each row reports the two functions actually stored in the authoritative case
# specification and their independently observed result. Agreement is required,
# but it does not establish correctness, independent derivation or complete
# semantic coverage
# [[73]](../docs/references.md#knight1986multiversion).

# %%
show_table(
    (
        "Item",
        "Oracle record",
        "Status",
        "Checker A",
        "Checker B",
        "Expected",
        "Observed A",
        "Observed B",
        "Evidence IDs",
    ),
    oracle_rows,
)

# %% [markdown]
# ### Repeated formal signatures within an archetype

# %%
if repeated_formal_rows:
    show_table(("Archetype", "Signature", "Item IDs"), repeated_formal_rows)
else:
    display(Markdown("No within-archetype signature repetitions were found."))

# %% [markdown]
# ## Service names and answer keys
#
# Each item contributes once. Counts are pooled across task families and expose
# associations for review; they do not show that a model uses the service name.

# %%
name_counts = service_name_key_counts(items, construction.service_names)
show_table(
    ("Service name", "Yes", "No", "Item IDs"),
    [
        (name, yes, no, ", ".join(item_ids))
        for name, (yes, no, item_ids) in name_counts.items()
    ],
)

# %% [markdown]
# ## Question length by answer key
#
# Raw length includes the fictional service name; name-masked length removes
# that spelling difference. Remaining differences can be legitimate consequences
# of the evidence, but label-associated length can also be an artefact
# [[64, Sec. 3]](../docs/references.md#gururangan2018artifacts). This is a
# descriptive comparison, not the hypothesis-only classifier used in that work.

# %%
def length_range(values: list[int]) -> str:
    return f"{min(values)} / {median(values):g} / {max(values)}"


length_rows = []
separated_length_archetypes = []
for archetype, group in sorted(by_archetype.items()):
    yes_lengths = [
        len(item.prompt.question)
        for item in group
        if item.answer_key.canonical_answer == "yes"
    ]
    no_lengths = [
        len(item.prompt.question)
        for item in group
        if item.answer_key.canonical_answer == "no"
    ]
    yes_masked = [
        len(normalize_question(item.prompt.question, construction.service_names))
        for item in group
        if item.answer_key.canonical_answer == "yes"
    ]
    no_masked = [
        len(normalize_question(item.prompt.question, construction.service_names))
        for item in group
        if item.answer_key.canonical_answer == "no"
    ]
    if max(yes_masked) < min(no_masked) or max(no_masked) < min(yes_masked):
        separated_length_archetypes.append(archetype)
    length_rows.append(
        (
            archetype,
            length_range(yes_lengths),
            length_range(no_lengths),
            length_range(yes_masked),
            length_range(no_masked),
        )
    )

show_table(
    (
        "Archetype",
        "Yes raw",
        "No raw",
        "Yes name-masked",
        "No name-masked",
    ),
    length_rows,
)

# %% [markdown]
# ## Findings and limits

# %%
exact_total = sum(row[2] for row in variation_rows)
name_masked_total = sum(row[3] for row in variation_rows)
number_masked_total = sum(row[4] for row in variation_rows)
formal_input_total = sum(row[2] for row in formal_summary_rows)
formal_signature_total = sum(row[3] for row in formal_summary_rows)
imbalanced_names = [name for name, (yes, no, _) in name_counts.items() if yes != no]
display(
    Markdown(
        f"The {len(items)} exact questions reduce to **{name_masked_total}** "
        f"name-masked and **{number_masked_total}** number-masked written forms. "
        f"**{len(imbalanced_names)} of {len(name_counts)}** service names have unequal "
        "yes/no counts. The exact-question count is "
        f"**{exact_total}**. These results identify cases for review; they do not "
        "approve the pool. Construction from the recorded configuration was "
        "identical on a second pass, with working pool hash `"
        f"{working_freeze.pool_hash}`. This differs from the preserved registered "
        "pool hash, so it is reproducibility evidence rather than freeze approval. "
        f"All **{len(pressure_rows)}** item-specific counter-positions oppose their "
        "keys and pass the three-wrapper construction checks. All **"
        f"{len(oracle_rows)}** cases produced their fixed expected result on both "
        "recorded oracle paths. Oracle agreement remains a bounded software check, "
        "not proof of correctness or independent derivation "
        "[[73]](../docs/references.md#knight1986multiversion). The formal review exposes all "
        f"**{len(specs)}** inputs: **{formal_input_total}** "
        "are exact-input-distinct and **"
        f"{formal_signature_total}** are distinct within their archetype under the "
        "recorded structural screens. These counts do not measure contamination, "
        "semantic diversity, graph isomorphism, or effective sample size. Different "
        "text can encode the same formal case, and number "
        "masking can group cases with different answers. Presentation sensitivity "
        "requires a separate outcome study "
        "[[14]](../docs/references.md#sclar2024formatting). Name-masked yes/no length ranges "
        f"do not overlap in **{len(separated_length_archetypes)}** archetypes: "
        f"{', '.join(separated_length_archetypes)}. Those differences arise from "
        "the current case wording and evidence, but this screen cannot determine "
        "whether they are necessary evidence or usable shortcuts. Five cases still "
        "share each archetype, constructor, prompt template, and oracle pair; that "
        "planned dependence must not be reported as 60 independent task designs. "
        "The signatures are deliberately coarse and archetype-specific. No item is "
        "selected or rejected, and the pool is not signed off, by this notebook."
    )
)

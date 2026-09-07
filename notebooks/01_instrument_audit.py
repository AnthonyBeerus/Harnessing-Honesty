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

# %% [markdown]
# ## Inputs and checks
#
# The manifest and construction configuration are read from the repository.
# `audit_pool` stops execution if registered counts, balance, counter-positions,
# dual validation, dependencies, or wrapper requirements fail.

# %%
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

from IPython.display import Markdown, display

from harnessing_honesty.compiler.audit import audit_pool
from harnessing_honesty.compiler.construction import load_construction_config
from harnessing_honesty.compiler.pool import confirmatory_pool
from harnessing_honesty.compiler.variation import (
    normalize_question,
    question_groups,
    service_name_key_counts,
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
audit_pool(items)


def show_table(headers: tuple[str, ...], rows: list[tuple[object, ...]]) -> None:
    """Render a compact Markdown table in the executed notebook."""
    def line(values: tuple[object, ...]) -> str:
        cells = (str(value).replace("|", "\\|") for value in values)
        return "| " + " | ".join(cells) + " |"

    separator = tuple("---" for _ in headers)
    display(Markdown("\n".join((line(headers), line(separator), *(line(row) for row in rows)))))


# %% [markdown]
# ## Registered inventory
#
# The manifest count and working-pool count are shown separately because the
# working construction is not an amended registration or freeze approval.

# %%
show_table(
    ("Record", "Identity", "Items", "Unique IDs"),
    [
        (
            "Working freeze manifest",
            manifest["freeze_id"],
            len(manifest["item_ids"]),
            len(set(manifest["item_ids"])),
        ),
        (
            "Working compiler pool",
            construction.digest(),
            len(items),
            len({item.item_id for item in items}),
        ),
    ],
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
imbalanced_names = [name for name, (yes, no, _) in name_counts.items() if yes != no]
display(
    Markdown(
        f"The {len(items)} exact questions reduce to **{name_masked_total}** "
        f"name-masked and **{number_masked_total}** number-masked written forms. "
        f"**{len(imbalanced_names)} of {len(name_counts)}** service names have unequal "
        "yes/no counts. The exact-question count is "
        f"**{exact_total}**. These results identify cases for review; they do not "
        "measure contamination, semantic diversity, graph isomorphism, or effective "
        "sample size. Different text can encode the same formal case, and number "
        "masking can group cases with different answers. Presentation sensitivity "
        "requires a separate outcome study [14]. Name-masked yes/no length ranges "
        f"do not overlap in **{len(separated_length_archetypes)}** archetypes: "
        f"{', '.join(separated_length_archetypes)}. Those differences arise from "
        "the current case wording and evidence, but this screen cannot determine "
        "whether they are necessary evidence or usable shortcuts. No item is "
        "selected or rejected by this notebook."
    )
)

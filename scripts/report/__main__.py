"""Draw the report: ``python -m scripts.report RESULTS --output OUT [options]``."""

import argparse
import csv
from collections.abc import Sequence
from pathlib import Path

from scripts.report import cost, multiturn, repair, robustness, structure, sycophancy
from scripts.report.common import ReportData, load, style

SECTIONS = (
    ("4.1", "Sycophancy: does a correct answer collapse under false pressure?", sycophancy),
    ("4.2", "Harness repair: the policies compared (H1)", repair),
    ("4.3", "Task structure and pressure (H3, H2)", structure),
    ("4.4", "Multi-turn pressure and alternative usage (exploratory)", multiturn),
    ("4.5", "Robustness", robustness),
    ("4.6", "Harness cost", cost),
)


def build_report(data: ReportData, output: Path) -> list[Path]:
    """Every figure and table the inputs allow; existing files are refused."""
    style()
    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    figure_index = ["# Figures", ""]
    table_index = ["# Tables", ""]
    for number, heading, section in SECTIONS:
        figure_index += [f"## {number} {heading}", "",
                         "| Figure | Shows | Modelled on | Files |", "|---|---|---|---|"]
        for spec in section.FIGURES:
            paths = spec.draw(data, output)
            if paths is None:
                files = f"not drawn: needs `{spec.needs}`"
            else:
                written.extend(paths)
                files = ", ".join(path.name for path in paths) or "nothing to draw"
            figure_index.append(f"| {spec.name} | {spec.caption} | {spec.source} | {files} |")
        figure_index.append("")
        table_index += [f"## {number} {heading}", ""]
        for spec in section.TABLES:
            built = spec.build(data)
            if built is None:
                table_index += [f"### {spec.caption}", "", f"Not built: needs `{spec.needs}`.",
                                ""]
                continue
            header, body = built
            path = output / f"table-{spec.name}.csv"
            with path.open("x", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(header)
                writer.writerows(body)
            written.append(path)
            table_index += [f"### {spec.caption}", "", "| " + " | ".join(header) + " |",
                            "|" + "---|" * len(header)]
            table_index += ["| " + " | ".join(row) + " |" for row in body] + [""]
    for name, lines in (("figures.md", figure_index), ("tables.md", table_index)):
        path = output / name
        with path.open("x", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
        written.append(path)
    return written


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--collection", type=Path)
    parser.add_argument("--replicate", type=Path, action="append", default=[])
    parser.add_argument("--stability", type=Path)
    args = parser.parse_args(argv)
    data = load(args.results, args.collection, args.replicate, args.stability)
    written = build_report(data, args.output)
    print(f"wrote {len(written)} files to {args.output}")


if __name__ == "__main__":
    main()

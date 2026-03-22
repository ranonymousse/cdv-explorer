from collections import Counter, defaultdict
from pathlib import Path

from paper.RQ2.classification_status import resolve_rq2_status_order
from paper.RQ2.classification_type import TYPE_ORDER


LATEX_TABCOLSEP_PT = 5


def _latex_escape(value: str) -> str:
    return (
        str(value)
        .replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("$", r"\$")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\textasciitilde{}")
        .replace("^", r"\textasciicircum{}")
    )


def _ordered_categories(observed: set[str], preferred_order: list[str]) -> list[str]:
    ordered = [value for value in preferred_order if value in observed]
    ordered.extend(sorted(observed - set(ordered)))
    return ordered


def _format_count_share(count: int, total: int) -> str:
    share = (count / total * 100) if total > 0 else 0.0
    return f"{count} ({share:.1f}\\%)"


def export_classification_status_type_latex_table(
    network_data: dict,
    output_path: Path,
    snapshot_label: str,
    *,
    tabcolsep_pt: int = LATEX_TABCOLSEP_PT,
) -> None:
    nodes = network_data.get("nodes", [])
    pivot = defaultdict(Counter)

    for node in nodes:
        status = str(node.get("status")).strip() or "Unknown Status"
        proposal_type = str(node.get("type")).strip() or "Unknown Type"
        pivot[proposal_type][status] += 1

    observed_types = set(pivot.keys())
    observed_statuses = {
        status
        for counts in pivot.values()
        for status in counts.keys()
    }
    ordered_types = _ordered_categories(observed_types, TYPE_ORDER)
    ordered_statuses = _ordered_categories(
        observed_statuses,
        resolve_rq2_status_order(snapshot_label),
    )
    total_bips = sum(sum(counts.values()) for counts in pivot.values())

    header_line = " & ".join(
        [r"\diagbox{\textbf{Type}}{\textbf{Status}}"]
        + [_latex_escape(status) for status in ordered_statuses]
    ) + r" \\"

    body_lines = []
    for proposal_type in ordered_types:
        row_cells = [_latex_escape(proposal_type)]
        for status in ordered_statuses:
            row_cells.append(
                _format_count_share(int(pivot[proposal_type].get(status, 0)), total_bips)
            )
        body_lines.append("        " + " & ".join(row_cells) + r" \\")

    alignment = "l|" + ("c" * len(ordered_statuses))
    latex_table = "\n".join(
        [
            "{",
            rf"    \setlength{{\tabcolsep}}{{{tabcolsep_pt}pt}}",
            rf"    \begin{{tabular}}{{{alignment}}}",
            r"    \toprule",
            f"    {header_line}",
            r"    \midrule",
            *body_lines,
            r"    \bottomrule",
            r"    \end{tabular}",
            "}",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex_table, encoding="utf-8")

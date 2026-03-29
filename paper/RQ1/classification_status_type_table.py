from collections import Counter, defaultdict
from pathlib import Path

from paper.RQ1.classification_type import TYPE_ORDER


LATEX_TABCOLSEP_PT = 5
FIRST_BODY_ROW_STRUT_EX = 2.8
TABLE_STATUS_ORDER = [
    "Draft",
    "Complete",
    "Deployed",
    "Closed",
]


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
    first_body_row_strut_ex: float = FIRST_BODY_ROW_STRUT_EX,
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
        TABLE_STATUS_ORDER,
    )
    total_bips = sum(sum(counts.values()) for counts in pivot.values())

    header_line = " & ".join(
        [r"\multicolumn{1}{|c}{\diagbox{\textbf{Type}}{\textbf{Status}}}"]
        + [_latex_escape(status) for status in ordered_statuses]
    ) + r" \\"
    header_cline = rf"    \cline{{2-{len(ordered_statuses) + 1}}}"

    body_lines = []
    for row_index, proposal_type in enumerate(ordered_types):
        first_cell = _latex_escape(proposal_type)
        if row_index == 0:
            first_cell = rf"\rule{{0pt}}{{{first_body_row_strut_ex}ex}}{first_cell}"
        row_cells = [first_cell]
        for status in ordered_statuses:
            row_cells.append(
                _format_count_share(int(pivot[proposal_type].get(status, 0)), total_bips)
            )
        body_lines.append("        " + " & ".join(row_cells) + r" \\")

    alignment = "|l|" + ("c" * len(ordered_statuses) + "|")
    latex_table = "\n".join(
        [
            "{",
            rf"    \setlength{{\tabcolsep}}{{{tabcolsep_pt}pt}}",
            rf"    \begin{{tabular}}{{{alignment}}}",
            r"    \hline",
            f"    {header_line}",
            header_cline,
            *body_lines,
            r"    \hline",
            r"    \end{tabular}",
            "}",
            "",
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(latex_table, encoding="utf-8")

from pathlib import Path
from typing import Any, Dict

from analysis.dependencies.metrics import _build_pairwise_comparisons


LATEX_TABCOLSEP_PT = 4
APPROACH_ORDER = [
    "explicit_dependencies",
    "explicit_references",
    "implicit_dependencies",
]
SHORT_LABELS = {
    "explicit_dependencies": "Preamble",
    "explicit_references": "Regex",
    "implicit_dependencies": "LLM",
}


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


def _format_count_share(count: int, share: float) -> str:
    return f"{count} ({share * 100:.1f}\\%)"


def _get_approach_only_rate(summary: Dict[str, Any]) -> float:
    approach_total = int(summary.get("approach_total", 0) or 0)
    if approach_total <= 0:
        return 0.0
    return float(summary.get("approach_only", 0) or 0) / approach_total


def _build_cell(comparison: Dict[str, Any]) -> Dict[str, str]:
    summary = comparison.get("summary", {})
    return {
        r"$A \cap B$": _format_count_share(
            int(summary.get("overlap", 0) or 0),
            float(summary.get("hit_rate", 0.0) or 0.0),
        ),
        r"$A \cap B'$": _format_count_share(
            int(summary.get("approach_only", 0) or 0),
            _get_approach_only_rate(summary),
        ),
        r"$A' \cap B$": _format_count_share(
            int(summary.get("baseline_only", 0) or 0),
            float(summary.get("missed_rate", 0.0) or 0.0),
        ),
    }


def export_dependency_comparison_latex_table(
    network_data: Dict[str, Any],
    output_path: Path,
    *,
    tabcolsep_pt: int = LATEX_TABCOLSEP_PT,
) -> None:
    pairwise_comparisons = _build_pairwise_comparisons(network_data)

    header_line = " & ".join(
        [r"\diagbox{\textbf{$A$}}{\textbf{$B$}}", r"\textbf{Metric}"]
        + [rf"\textbf{{{_latex_escape(SHORT_LABELS[key])}}}" for key in APPROACH_ORDER]
    ) + r" \\"

    body_lines = []
    metric_order = [r"$A \cap B$", r"$A' \cap B$", r"$A \cap B'$"]
    for approach in APPROACH_ORDER:
        metric_values_by_baseline = []
        for baseline in APPROACH_ORDER:
            comparison_key = f"{approach}__vs__{baseline}"
            comparison = pairwise_comparisons.get(comparison_key, {})
            metric_values_by_baseline.append(_build_cell(comparison))

        for metric_index, metric_label in enumerate(metric_order):
            row_cells = []
            if metric_index == 0:
                row_cells.append(rf"\multirow{{3}}{{*}}{{\textbf{{{_latex_escape(SHORT_LABELS[approach])}}}}}")
            else:
                row_cells.append("")
            row_cells.append(metric_label)
            for metric_values in metric_values_by_baseline:
                row_cells.append(metric_values[metric_label])
            line_prefix = "        "
            line_suffix = r" \\"
            if metric_index == len(metric_order) - 1 and approach != APPROACH_ORDER[-1]:
                line_suffix = r" \\" + "\n        " + r"\midrule"
            body_lines.append(line_prefix + " & ".join(row_cells) + line_suffix)

    latex_table = "\n".join(
        [
            "{",
            rf"    \setlength{{\tabcolsep}}{{{tabcolsep_pt}pt}}",
            r"    \renewcommand{\arraystretch}{1.15}",
            r"    \begin{tabular}{lc|ccc}",
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

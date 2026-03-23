from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator, MultipleLocator

from paper.RQ1._plotting import (
    BAR_EDGE_COLOR,
    BAR_EDGE_WIDTH,
    bar_style,
    despine,
    match_axis_label_fontsize,
)


REACT_CLASSIFICATION_PALETTE = [
    "#4e79a7",
    "#f28e2b",
    "#e15759",
    "#76b7b2",
    "#59a14f",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ab",
    "#66c2a5",
    "#fc8d62",
    "#8da0cb",
    "#e78ac3",
    "#a6d854",
    "#ffd92f",
    "#e5c494",
    "#b3b3b3",
    "#8dd3c7",
    "#ffffb3",
    "#bebada",
    "#fb8072",
    "#80b1d3",
    "#fdb462",
    "#b3de69",
    "#fccde5",
    "#d9d9d9",
    "#bc80bd",
    "#ccebc5",
    "#ffed6f",
]

HATCH_BIP3 = "////"
BIP3_ALLOWED_STATUSES = {"Draft", "Complete", "Deployed", "Closed"}
BIP3_DRAFT_START_PERIOD = "2025-Q2"


def _react_color_map(categories: list[str]) -> dict[str, str]:
    return {
        category: REACT_CLASSIFICATION_PALETTE[index % len(REACT_CLASSIFICATION_PALETTE)]
        for index, category in enumerate(categories)
    }


def _normalize_evolution_series(
    status_evolution: dict[str, Any],
) -> tuple[list[str], list[str], dict[str, list[int]]]:
    rows = [
        {
            "period": str(row.get("period") or row.get("year") or "").strip(),
            "values": row.get("values") or {},
        }
        for row in (status_evolution.get("rows") or [])
        if str(row.get("period") or row.get("year") or "").strip()
    ]
    if not rows:
        raise ValueError("Status evolution plot requires non-empty quarterly rows.")

    rows.sort(key=lambda row: row["period"])

    preferred_categories = [
        str(category).strip()
        for category in (status_evolution.get("categories") or [])
        if str(category).strip()
    ]
    observed_categories = list(
        dict.fromkeys(
            status
            for row in rows
            for status, value in row["values"].items()
            if int(value) > 0
        )
    )
    ordered_categories = [
        category
        for category in preferred_categories
        if category in observed_categories
    ]
    ordered_categories.extend(
        category
        for category in observed_categories
        if category not in ordered_categories
    )
    if not ordered_categories:
        raise ValueError("Status evolution plot requires at least one positive status count.")

    periods = [row["period"] for row in rows]
    series = {
        category: [
            int(row["values"].get(category, 0))
            for row in rows
        ]
        for category in ordered_categories
    }
    return periods, ordered_categories, series


def _normalize_standard_rows(
    status_evolution_by_standard: dict[str, Any] | None,
) -> dict[str, dict[str, dict[str, int]]]:
    normalized: dict[str, dict[str, dict[str, int]]] = {}
    for standard in ("bip2", "bip3"):
        standard_data = (status_evolution_by_standard or {}).get(standard) or {}
        rows = standard_data.get("rows") or []
        normalized[standard] = {
            str(row.get("period") or row.get("year") or "").strip(): {
                str(status).strip(): int(value)
                for status, value in (row.get("values") or {}).items()
                if str(status).strip()
            }
            for row in rows
            if str(row.get("period") or row.get("year") or "").strip()
        }
    return normalized


def _can_render_as_bip3(status: str, period: str) -> bool:
    if status not in BIP3_ALLOWED_STATUSES:
        return False
    if status == "Draft" and period < BIP3_DRAFT_START_PERIOD:
        return False
    return True


def _build_segment_definitions(
    periods: list[str],
    ordered_statuses: list[str],
    series: dict[str, list[int]],
    status_evolution_by_standard: dict[str, Any] | None,
) -> tuple[list[tuple[str, str]], dict[str, list[int]], dict[str, list[str]]]:
    standard_rows = _normalize_standard_rows(status_evolution_by_standard)
    segment_order: list[tuple[str, str]] = []
    segment_series: dict[str, list[int]] = {}
    legend_statuses = {"bip2": [], "bip3": []}

    for status in ordered_statuses:
        total_counts = series[status]
        bip3_counts = []
        bip2_counts = []

        for index, period in enumerate(periods):
            total_count = int(total_counts[index])
            raw_bip3_count = int(standard_rows["bip3"].get(period, {}).get(status, 0))
            bip3_count = raw_bip3_count if _can_render_as_bip3(status, period) else 0
            bip3_count = max(0, min(total_count, bip3_count))
            bip2_count = total_count - bip3_count
            bip3_counts.append(bip3_count)
            bip2_counts.append(bip2_count)

        if any(count > 0 for count in bip2_counts):
            segment_order.append((status, "bip2"))
            segment_series[f"{status}|||bip2"] = bip2_counts
            legend_statuses["bip2"].append(status)

        if any(count > 0 for count in bip3_counts):
            segment_order.append((status, "bip3"))
            segment_series[f"{status}|||bip3"] = bip3_counts
            legend_statuses["bip3"].append(status)

    return segment_order, segment_series, legend_statuses


def _select_year_tick_indices(periods: list[str]) -> list[int]:
    indices_by_year: dict[str, int] = {}
    for index, period in enumerate(periods):
        year = period.split("-", 1)[0]
        if period.endswith("Q1"):
            indices_by_year[year] = index
    return [indices_by_year[year] for year in sorted(indices_by_year)]


def plot_evolution_status(
    status_evolution: dict[str, Any],
    output_path: Path,
    snapshot_label: str,
    *,
    status_evolution_by_standard: dict[str, Any] | None = None,
    category_title: str = "Status Evolution",
    y_axis_title: str = "Number of BIPs",
) -> None:
    periods, ordered_statuses, series = _normalize_evolution_series(status_evolution)
    color_map = _react_color_map(ordered_statuses)
    segment_order, segment_series, legend_statuses = _build_segment_definitions(
        periods,
        ordered_statuses,
        series,
        status_evolution_by_standard,
    )
    if not segment_order:
        segment_order = [(status, "bip2") for status in ordered_statuses]
        segment_series = {
            f"{status}|||bip2": counts
            for status, counts in series.items()
        }
        legend_statuses = {
            "bip2": list(ordered_statuses),
            "bip3": [],
        }

    bip2_handles = [
        Patch(
            facecolor=bar_style(color_map[status])["color"],
            edgecolor=BAR_EDGE_COLOR,
            linewidth=BAR_EDGE_WIDTH,
            label=status,
        )
        for status in legend_statuses["bip2"]
    ]
    bip3_handles = [
        Patch(
            facecolor=bar_style(color_map[status])["color"],
            edgecolor=BAR_EDGE_COLOR,
            linewidth=BAR_EDGE_WIDTH,
            hatch=HATCH_BIP3,
            label=status,
        )
        for status in legend_statuses["bip3"]
    ]
    x_positions = np.arange(len(periods))
    bar_bottom = np.zeros(len(periods), dtype=int)

    figure, axis = plt.subplots(figsize=(10.5, 4.5))

    for status, standard in segment_order:
        counts = np.array(segment_series[f"{status}|||{standard}"], dtype=int)
        axis.bar(
            x_positions,
            counts,
            bottom=bar_bottom,
            width=0.82,
            zorder=3,
            hatch=HATCH_BIP3 if standard == "bip3" else None,
            **bar_style(color_map[status]),
        )
        bar_bottom = bar_bottom + counts

    major_tick_indices = _select_year_tick_indices(periods)
    axis.set_xticks(x_positions[major_tick_indices])
    axis.set_xticklabels([periods[index].split("-", 1)[0] for index in major_tick_indices])
    axis.set_xticks(x_positions, minor=True)
    axis.tick_params(axis="x", which="major", length=6)
    axis.tick_params(axis="x", which="minor", length=3, labelbottom=False)
    axis.set_xlim(-0.6, len(periods) - 0.4)
    axis.set_ylabel(y_axis_title)
    axis.set_title(f"{category_title} ({snapshot_label})")
    axis.set_ylim(0, max(200, int(bar_bottom.max())))
    axis.yaxis.set_major_locator(MaxNLocator(integer=True))
    axis.yaxis.set_minor_locator(MultipleLocator(10))
    axis.tick_params(axis="y", which="minor", length=3)
    axis.grid(axis="y", alpha=0.35)
    axis.grid(axis="x", visible=False)
    axis.set_axisbelow(True)
    match_axis_label_fontsize(axis)
    despine(axis)

    if bip2_handles:
        bip2_legend = axis.legend(
            handles=bip2_handles,
            loc="upper left",
            bbox_to_anchor=(1.02, 1.0),
            frameon=False,
            title="BIP2",
            borderaxespad=0,
            fontsize=9,
            title_fontsize=9.5,
        )
        axis.add_artist(bip2_legend)

    if bip3_handles:
        axis.legend(
            handles=bip3_handles,
            loc="upper left",
            bbox_to_anchor=(1.02, 0.30),
            frameon=False,
            title="BIP3",
            borderaxespad=0,
            fontsize=9,
            title_fontsize=9.5,
        )

    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf", bbox_inches="tight", pad_inches=0.08)
    plt.close(figure)

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from paper.RQ3._plotting import (
    bar_style,
    despine,
    match_axis_label_fontsize,
    save_figure,
    style_ellipsis_ticklabels,
)


TOP_AUTHORS_COLOR = "#d94841"
HISTOGRAM_COLOR = "#2f9e44"
MIN_HISTOGRAM_GAP_LENGTH = 3
HISTOGRAM_GAP_LABEL = "..."


def _prepare_top_ten(top_authors: list[dict[str, int | str]]) -> list[dict[str, int | str]]:
    if not top_authors:
        raise ValueError("Authorship overview requires non-empty top_authors data.")

    return sorted(
        (
            {
                "author": str(entry["author"]),
                "count": int(entry["count"]),
            }
            for entry in top_authors
        ),
        key=lambda entry: entry["count"],
        reverse=True,
    )[:10]


def _prepare_histogram_series(
    contribution_histogram: list[dict[str, int]],
) -> list[dict[str, int]]:
    if not contribution_histogram:
        raise ValueError("Authorship overview requires non-empty contribution_histogram data.")

    histogram_points = sorted(
        (
            {
                "bips_written": int(entry["bips_written"]),
                "authors": int(entry["authors"]),
            }
            for entry in contribution_histogram
            if int(entry["bips_written"]) > 0
        ),
        key=lambda entry: entry["bips_written"],
    )
    if not histogram_points:
        raise ValueError("Authorship overview requires positive histogram buckets.")

    min_bips_written = histogram_points[0]["bips_written"]
    max_bips_written = histogram_points[-1]["bips_written"]
    authors_by_bucket = {
        entry["bips_written"]: entry["authors"]
        for entry in histogram_points
    }
    histogram_series = [
        {
            "bips_written": bips_written,
            "authors": authors_by_bucket.get(bips_written, 0),
        }
        for bips_written in range(min_bips_written, max_bips_written + 1)
    ]

    return histogram_series


def _compress_histogram_zero_gaps(
    histogram_series: list[dict[str, int]],
    *,
    min_gap_length: int = MIN_HISTOGRAM_GAP_LENGTH,
) -> list[dict[str, int | str | bool]]:
    if not histogram_series:
        return []

    zero_runs: list[tuple[int, int]] = []
    run_start: int | None = None

    for index, entry in enumerate(histogram_series):
        if int(entry["authors"]) == 0:
            if run_start is None:
                run_start = index
            continue

        if run_start is not None:
            zero_runs.append((run_start, index - 1))
            run_start = None

    if run_start is not None:
        zero_runs.append((run_start, len(histogram_series) - 1))

    eligible_runs = [
        (start, end)
        for start, end in zero_runs
        if (end - start + 1) >= min_gap_length
    ]
    if not eligible_runs:
        return [
            {
                **entry,
                "axis_label": str(int(entry["bips_written"])),
                "is_gap": False,
            }
            for entry in histogram_series
        ]

    compressed: list[dict[str, int | str | bool]] = []
    for index, entry in enumerate(histogram_series):
        matching_run = next(
            (
                (start, end)
                for start, end in eligible_runs
                if start <= index <= end
            ),
            None,
        )
        if matching_run is None:
            compressed.append(
                {
                    **entry,
                    "axis_label": str(int(entry["bips_written"])),
                    "is_gap": False,
                }
            )
            continue

        gap_start, _gap_end = matching_run
        if index == gap_start:
            compressed.append(
                {
                    "bips_written": -1,
                    "authors": 0,
                    "axis_label": HISTOGRAM_GAP_LABEL,
                    "is_gap": True,
                }
            )

    return compressed


def _draw_top_authors_axis(axis, top_ten: list[dict[str, int | str]], *, title: str | None) -> None:
    author_names = [entry["author"] for entry in top_ten]
    author_counts = [entry["count"] for entry in top_ten]

    axis.barh(author_names, author_counts, zorder=2, **bar_style(TOP_AUTHORS_COLOR))
    if title:
        axis.set_title(title)
    axis.set_xlabel("Proposals authored")
    axis.set_ylabel("")
    axis.invert_yaxis()
    for index, count in enumerate(author_counts):
        axis.text(count + 0.35, index, str(count), va="center", ha="left")
    axis.grid(axis="x", alpha=0.35)
    axis.grid(axis="y", visible=False)
    match_axis_label_fontsize(axis)
    despine(axis)


def _draw_authorship_distribution_axis(
    axis,
    histogram_series: list[dict[str, int]],
    *,
    title: str | None,
) -> None:
    displayed_histogram_series = _compress_histogram_zero_gaps(histogram_series)
    histogram_x = [entry["bips_written"] for entry in displayed_histogram_series]
    histogram_y = [entry["authors"] for entry in displayed_histogram_series]
    histogram_labels = [str(entry["axis_label"]) for entry in displayed_histogram_series]
    histogram_positions = np.arange(len(histogram_x))
    labeled_histogram_positions = [
        position
        for position, authors, label in zip(histogram_positions, histogram_y, histogram_labels)
        if authors > 0 or label == HISTOGRAM_GAP_LABEL
    ]
    labeled_histogram_values = [
        label
        for label, authors in zip(histogram_labels, histogram_y)
        if authors > 0 or label == HISTOGRAM_GAP_LABEL
    ]

    axis.bar(histogram_positions, histogram_y, width=0.8, zorder=2, **bar_style(HISTOGRAM_COLOR))
    if title:
        axis.set_title(title)
    axis.set_xlabel("BIPs written per author")
    axis.set_ylabel("Number of authors")
    axis.set_xticks(labeled_histogram_positions)
    axis.set_xticklabels(labeled_histogram_values)
    axis.grid(axis="y", alpha=0.35)
    axis.grid(axis="x", visible=False)
    match_axis_label_fontsize(axis)
    for index, authors, entry in zip(histogram_positions, histogram_y, displayed_histogram_series):
        if bool(entry.get("is_gap")):
            continue
        if authors <= 0:
            continue
        axis.text(index, authors + max(histogram_y) * 0.015, str(authors), ha="center", va="bottom")
    style_ellipsis_ticklabels(
        axis,
        labeled_histogram_values,
        ellipsis_label=HISTOGRAM_GAP_LABEL,
    )
    despine(axis)


def plot_top_authors(
    top_authors: list[dict[str, int | str]],
    output_path: Path,
) -> None:
    top_ten = _prepare_top_ten(top_authors)
    figure, axis = plt.subplots(figsize=(4.3, 2.8))
    _draw_top_authors_axis(axis, top_ten, title=None)
    figure.tight_layout()
    save_figure(figure, output_path)


def plot_authorship_distribution(
    contribution_histogram: list[dict[str, int]],
    output_path: Path,
) -> None:
    histogram_series = _prepare_histogram_series(contribution_histogram)
    figure, axis = plt.subplots(figsize=(5, 2.8))
    _draw_authorship_distribution_axis(axis, histogram_series, title=None)
    figure.tight_layout()
    save_figure(figure, output_path)


def plot_authorship_overview(
    top_authors: list[dict[str, int | str]],
    contribution_histogram: list[dict[str, int]],
    output_path: Path,
    snapshot_label: str,
) -> None:
    top_ten = _prepare_top_ten(top_authors)
    histogram_series = _prepare_histogram_series(contribution_histogram)

    figure, (axis_left, axis_right) = plt.subplots(
        1,
        2,
        figsize=(9, 2.8),
        gridspec_kw={"width_ratios": [0.18, 0.82]},
    )

    _draw_top_authors_axis(axis_left, top_ten, title="(a) Top 10 Authors")
    _draw_authorship_distribution_axis(
        axis_right,
        histogram_series,
        title="(b) Authorship Distribution",
    )

    figure.suptitle(f"Authorship Overview ({snapshot_label})", y=1.02)
    figure.tight_layout()
    save_figure(figure, output_path)

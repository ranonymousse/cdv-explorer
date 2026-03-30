from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from paper.RQ3._plotting import bar_style, despine, match_axis_label_fontsize, save_figure


TOP_AUTHORS_COLOR = "#d94841"
HISTOGRAM_COLOR = "#2f9e44"


def plot_authorship_overview(
    top_authors: list[dict[str, int | str]],
    contribution_histogram: list[dict[str, int]],
    output_path: Path,
    snapshot_label: str,
) -> None:
    if not top_authors:
        raise ValueError("Authorship overview requires non-empty top_authors data.")
    if not contribution_histogram:
        raise ValueError("Authorship overview requires non-empty contribution_histogram data.")

    top_ten = sorted(
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

    author_names = [entry["author"] for entry in top_ten]
    author_counts = [entry["count"] for entry in top_ten]
    histogram_x = [entry["bips_written"] for entry in histogram_series]
    histogram_y = [entry["authors"] for entry in histogram_series]
    histogram_positions = np.arange(len(histogram_x))
    labeled_histogram_positions = [
        position
        for position, authors in zip(histogram_positions, histogram_y)
        if authors > 0
    ]
    labeled_histogram_values = [
        bips_written
        for bips_written, authors in zip(histogram_x, histogram_y)
        if authors > 0
    ]

    figure, (axis_left, axis_right) = plt.subplots(
        1,
        2,
        figsize=(9, 2.8),
        gridspec_kw={"width_ratios": [0.18, 0.82]},
    )

    axis_left.barh(author_names, author_counts, zorder=2, **bar_style(TOP_AUTHORS_COLOR))
    axis_right.bar(histogram_positions, histogram_y, width=0.8, zorder=2, **bar_style(HISTOGRAM_COLOR))

    axis_left.set_title("(a) Top 10 Authors")
    axis_left.set_xlabel("Proposals authored")
    axis_left.set_ylabel("")
    axis_left.invert_yaxis()
    for index, count in enumerate(author_counts):
        axis_left.text(count + 0.35, index, str(count), va="center", ha="left")
    axis_left.grid(axis="x", alpha=0.35)
    axis_left.grid(axis="y", visible=False)
    match_axis_label_fontsize(axis_left)
    despine(axis_left)

    axis_right.set_title("(b) Authorship Distribution")
    axis_right.set_xlabel("BIPs written per author")
    axis_right.set_ylabel("Number of authors")
    axis_right.set_xticks(labeled_histogram_positions)
    axis_right.set_xticklabels(labeled_histogram_values)
    axis_right.grid(axis="y", alpha=0.35)
    axis_right.grid(axis="x", visible=False)
    match_axis_label_fontsize(axis_right)
    for index, authors in enumerate(histogram_y):
        if authors <= 0:
            continue
        axis_right.text(index, authors + max(histogram_y) * 0.015, str(authors), ha="center", va="bottom")
    despine(axis_right)

    figure.suptitle(f"Authorship Overview ({snapshot_label})", y=1.02)
    figure.tight_layout()
    save_figure(figure, output_path)

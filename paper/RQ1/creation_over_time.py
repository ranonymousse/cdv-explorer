from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from paper.RQ1._plotting import despine, save_figure


TIMELINE_BAR_COLOR = "#4c78a8"
TIMELINE_LINE_COLOR = "#e45756"


def plot_creation_over_time(
    proposals_per_year: list[dict[str, int]],
    output_path: Path,
    snapshot_label: str,
) -> None:
    if not proposals_per_year:
        raise ValueError("Creation-over-time plot requires non-empty proposals_per_year data.")

    years = [int(entry["year"]) for entry in proposals_per_year]
    yearly_counts = [int(entry["count"]) for entry in proposals_per_year]
    cumulative_counts = np.cumsum(yearly_counts)
    x_positions = np.arange(len(years))

    figure, axis_left = plt.subplots(figsize=(10.5, 5.6))
    axis_right = axis_left.twinx()

    axis_left.bar(
        x_positions,
        yearly_counts,
        width=0.72,
        color=TIMELINE_BAR_COLOR,
        zorder=2,
    )
    axis_right.plot(
        x_positions,
        cumulative_counts,
        color=TIMELINE_LINE_COLOR,
        linewidth=2.2,
        marker="o",
        zorder=3,
    )

    axis_left.set_xticks(x_positions)
    axis_left.set_xticklabels(years, rotation=45, ha="right")
    axis_left.set_ylabel("New proposals")
    axis_right.set_ylabel("Cumulative total")
    axis_left.set_xlabel("Year")
    axis_left.set_title(f"Creation Over Time ({snapshot_label})")
    axis_left.set_xlim(-0.6, len(years) - 0.4)
    axis_left.grid(axis="y", alpha=0.35)
    axis_right.grid(False)
    despine(axis_left)
    axis_right.spines["top"].set_visible(False)
    axis_right.spines["left"].set_visible(False)

    figure.tight_layout()
    save_figure(figure, output_path)

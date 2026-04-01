from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from paper.RQ3._plotting import save_figure
from paper.RQ3.authorship_overview import (
    _compress_histogram_zero_gaps,
    _draw_authorship_distribution_axis,
    _draw_authors_per_bip_axis,
    _prepare_bip_author_count_series,
    _prepare_histogram_series,
)
from paper.RQ3.collaboration_structure_overview import (
    _draw_component_distribution_axis,
    _prepare_component_and_degree_series,
)


def _add_bar_label_headroom(axis, *, ratio: float = 0.08, min_extra: float = 0.6) -> None:
    bar_heights = [patch.get_height() for patch in axis.patches]
    if not bar_heights:
        return

    ymax = max(bar_heights)
    extra = max(ymax * ratio, min_extra)
    lower, upper = axis.get_ylim()
    axis.set_ylim(lower, max(upper, ymax + extra))


def plot_authorship_collaboration_triptych(
    contribution_histogram: list[dict[str, int]],
    bip_author_count_histogram: list[dict[str, int]],
    collaboration_network: dict,
    output_path: Path,
) -> None:
    histogram_series = _prepare_histogram_series(contribution_histogram)
    displayed_histogram_series = _compress_histogram_zero_gaps(histogram_series)
    display_series = _prepare_bip_author_count_series(bip_author_count_histogram)
    displayed_component_series, _ = _prepare_component_and_degree_series(collaboration_network)
    width_ratios = [
        len(displayed_histogram_series),
        len(displayed_component_series),
        len(display_series),
    ]

    figure, axes = plt.subplots(
        1,
        3,
        figsize=(9.2, 2.8),
        gridspec_kw={"width_ratios": width_ratios},
    )

    _draw_authorship_distribution_axis(
        axes[0],
        histogram_series,
        title="(a) Authorship Distribution",
    )
    _add_bar_label_headroom(axes[0])
    axes[0].set_ylabel("# Authors")

    _draw_component_distribution_axis(
        axes[1],
        displayed_component_series,
        title="(b) Component Size Distribution",
    )
    _add_bar_label_headroom(axes[1])
    axes[1].set_ylabel("# Connected components")

    _draw_authors_per_bip_axis(
        axes[2],
        display_series,
        title="(c) Authors per BIP",
    )
    _add_bar_label_headroom(axes[2])
    axes[2].set_ylabel("#BIPs")
    axes[2].set_xlabel("# Authors per BIP")

    figure.tight_layout(pad=0.45, w_pad=0.7)
    save_figure(figure, output_path)

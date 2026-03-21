from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba


BAR_FILL_ALPHA = 0.85
BAR_EDGE_WIDTH = 1.0


def despine(axis, *, right: bool = True) -> None:
    axis.spines["top"].set_visible(False)
    if right:
        axis.spines["right"].set_visible(False)


def bar_style(color: str, *, edgecolor: str | None = None) -> dict[str, object]:
    return {
        "color": to_rgba(color, BAR_FILL_ALPHA),
        "edgecolor": edgecolor or color,
        "linewidth": BAR_EDGE_WIDTH,
    }


def match_axis_label_fontsize(axis) -> None:
    ticklabels = [
        *axis.get_xticklabels(),
        *axis.get_yticklabels(),
    ]

    tick_fontsize = None
    for ticklabel in ticklabels:
        size = ticklabel.get_fontsize()
        if size:
            tick_fontsize = float(size)
            break

    if tick_fontsize is None:
        tick_fontsize = float(plt.rcParams.get("font.size", 10))

    axis.xaxis.label.set_size(tick_fontsize)
    axis.yaxis.label.set_size(tick_fontsize)


def save_figure(figure, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf")
    plt.close(figure)

from pathlib import Path

import matplotlib.pyplot as plt

def despine(axis, *, right: bool = True) -> None:
    axis.spines["top"].set_visible(False)
    if right:
        axis.spines["right"].set_visible(False)


def save_figure(figure, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, format="pdf")
    plt.close(figure)

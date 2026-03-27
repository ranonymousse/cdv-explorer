from pathlib import Path

from analysis.classification.metrics import build_type_over_time
from paper.RQ1.classification_status import plot_classification_status


TYPE_ORDER = [
    "Specification",
    "Informational",
    "Process",
    "Unknown Type",
]

TYPE_COLORS = {
    "Specification": "#9467bd",
    "Informational": "#bcbd22",
    "Process": "#17becf",
    "Unknown Type": "#7f7f7f",
}


def plot_classification_type(
    network_data: dict,
    output_path: Path,
    snapshot_label: str,
) -> None:
    nodes = network_data.get("nodes", [])
    type_over_time = build_type_over_time(nodes)
    plot_classification_status(
        status_over_time=type_over_time,
        output_path=output_path,
        snapshot_label=snapshot_label,
        category_title="Classification Type",
        center_label="BIPs",
        order=TYPE_ORDER,
        colors=TYPE_COLORS,
        left_axis_title="Type",
        right_axis_title="Number of BIPs",
        right_secondary_axis_title="Cumulative number of BIPs",
    )

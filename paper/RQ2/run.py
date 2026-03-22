import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paper.config import SNAPSHOT
from paper._utils.io import resolve_output_dir, snapshot_prefix

OUTPUT_DIR = None
GENERATE_CLASSIFICATION_STATUS_PLOT = True
GENERATE_CLASSIFICATION_TYPE_PLOT = True
GENERATE_CLASSIFICATION_STATUS_TYPE_TABLE = True
GENERATE_CLASSIFICATION_SANKEY_PLOT = True

RQ2_STATUS_PLOT_ORDER = ["Draft", "Complete", "Deployed", "Closed"]


def main() -> None:
    from analysis.artifact_io import (
        load_classification_payload,
        load_network_data,
        resolve_latest_snapshot_label,
    )
    from paper.RQ2.classification_sankey import plot_classification_sankey
    from paper.RQ2.classification_status import plot_classification_status
    from paper.RQ2.classification_status_type_table import (
        export_classification_status_type_latex_table,
    )
    from paper.RQ2.classification_type import plot_classification_type

    if (
        not GENERATE_CLASSIFICATION_STATUS_PLOT
        and not GENERATE_CLASSIFICATION_TYPE_PLOT
        and not GENERATE_CLASSIFICATION_STATUS_TYPE_TABLE
        and not GENERATE_CLASSIFICATION_SANKEY_PLOT
    ):
        return

    snapshot_label = SNAPSHOT or resolve_latest_snapshot_label() or "latest"
    output_dir = resolve_output_dir(OUTPUT_DIR, Path("paper") / "RQ2" / "outputs")
    filename_prefix = snapshot_prefix(snapshot_label)
    classification_payload = None
    network_data = None

    if GENERATE_CLASSIFICATION_STATUS_PLOT:
        classification_payload = load_classification_payload(snapshot=SNAPSHOT)
        plot_classification_status(
            status_over_time=classification_payload.get("status_over_time", {}),
            output_path=output_dir / f"{filename_prefix}_classification_status.pdf",
            snapshot_label=snapshot_label,
            order=RQ2_STATUS_PLOT_ORDER,
        )

    if GENERATE_CLASSIFICATION_TYPE_PLOT:
        network_data = load_network_data(snapshot=SNAPSHOT)
        plot_classification_type(
            network_data=network_data,
            output_path=output_dir / f"{filename_prefix}_classification_type.pdf",
            snapshot_label=snapshot_label,
        )

    if GENERATE_CLASSIFICATION_SANKEY_PLOT:
        if network_data is None:
            network_data = load_network_data(snapshot=SNAPSHOT)
        plot_classification_sankey(
            network_data=network_data,
            output_path=output_dir / f"{filename_prefix}_classification_sankey.pdf",
            snapshot_label=snapshot_label,
            status_order=RQ2_STATUS_PLOT_ORDER,
        )

    if GENERATE_CLASSIFICATION_STATUS_TYPE_TABLE:
        if network_data is None:
            network_data = load_network_data(snapshot=SNAPSHOT)
        export_classification_status_type_latex_table(
            network_data=network_data,
            output_path=output_dir / f"{filename_prefix}_classification_status_type.tex",
        )


if __name__ == "__main__":
    main()

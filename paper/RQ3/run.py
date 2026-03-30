import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paper.config import SNAPSHOT
from paper._utils.io import resolve_output_dir, snapshot_prefix

# Set this directly only when RQ3 needs a custom output location.
OUTPUT_DIR = None
GENERATE_AUTHORSHIP_PLOTS = True
GENERATE_COLLABORATION_NETWORK_PLOT = True
GENERATE_COLLABORATION_NETWORK_EXPORTED_PLOT = True
GENERATE_COLLABORATION_METRICS_TABLE = True
COLLABORATION_NETWORK_EXPORTED_LAYOUT = None


def main() -> None:
    from analysis.artifact_io import (
        load_authorship_payload,
        load_authorship_metrics,
        load_network_data,
        resolve_latest_snapshot_label,
    )
    from paper.RQ3.authorship_overview import plot_authorship_overview
    from paper.RQ3.collaboration_metrics_table import (
        export_collaboration_metrics_latex_table,
        export_collaboration_metrics_table,
    )
    from paper.RQ3.collaboration_network import render_collaboration_network_layout_suite
    from paper.RQ3.collaboration_network_exported_layout import (
        plot_collaboration_network_from_exported_layout,
        resolve_default_output_path as resolve_exported_network_output_path,
        resolve_layout_export_path,
    )
    from paper.RQ3.creation_over_time import plot_creation_over_time

    snapshot_label = SNAPSHOT or resolve_latest_snapshot_label() or "latest"
    output_dir = resolve_output_dir(OUTPUT_DIR, Path("paper") / "RQ3" / "outputs")
    filename_prefix = snapshot_prefix(snapshot_label)
    authorship_payload: dict | None = None
    network_data: dict | None = None

    if GENERATE_AUTHORSHIP_PLOTS:
        authorship_metrics = load_authorship_metrics(snapshot=SNAPSHOT)
        plot_creation_over_time(
            proposals_per_year=authorship_metrics.get("proposals_per_year", []),
            output_path=output_dir / f"{filename_prefix}_creation_over_time.pdf",
            snapshot_label=snapshot_label,
        )
        plot_authorship_overview(
            top_authors=authorship_metrics.get("top_authors", []),
            contribution_histogram=authorship_metrics.get("author_contribution_histogram", []),
            output_path=output_dir / f"{filename_prefix}_authorship_overview.pdf",
            snapshot_label=snapshot_label,
        )

    if GENERATE_COLLABORATION_NETWORK_EXPORTED_PLOT:
        if authorship_payload is None:
            authorship_payload = load_authorship_payload(snapshot=SNAPSHOT)
        if network_data is None:
            network_data = load_network_data(snapshot=SNAPSHOT)

        layout_export_path = resolve_layout_export_path(COLLABORATION_NETWORK_EXPORTED_LAYOUT)
        if layout_export_path.exists():
            layout_payload = json.loads(layout_export_path.read_text(encoding="utf8"))
            plot_collaboration_network_from_exported_layout(
                network_data=network_data,
                authorship_payload=authorship_payload,
                layout_export_path=layout_export_path,
                output_path=resolve_exported_network_output_path(
                    snapshot_label=snapshot_label,
                    layout_payload=layout_payload,
                    output_dir=output_dir,
                ),
                snapshot_label=snapshot_label,
            )
        else:
            print(
                "Skipping exported collaboration network plot; layout export not found: "
                f"{layout_export_path}"
            )

    if GENERATE_COLLABORATION_NETWORK_PLOT:
        if authorship_payload is None:
            authorship_payload = load_authorship_payload(snapshot=SNAPSHOT)
        if network_data is None:
            network_data = load_network_data(snapshot=SNAPSHOT)
        render_collaboration_network_layout_suite(
            network_data=network_data,
            authorship_payload=authorship_payload,
            output_dir=output_dir,
            filename_prefix=filename_prefix,
            snapshot_label=snapshot_label,
        )

    if GENERATE_COLLABORATION_METRICS_TABLE:
        if authorship_payload is None:
            authorship_payload = load_authorship_payload(snapshot=SNAPSHOT)
        if network_data is None:
            network_data = load_network_data(snapshot=SNAPSHOT)
        export_collaboration_metrics_table(
            authorship_payload=authorship_payload,
            network_data=network_data,
            output_path=output_dir / f"{filename_prefix}_collaboration_metrics.xlsx",
        )
        export_collaboration_metrics_latex_table(
            authorship_payload=authorship_payload,
            network_data=network_data,
            output_path=output_dir / f"{filename_prefix}_collaboration_metrics_top_weighted_degree.tex",
        )


if __name__ == "__main__":
    main()

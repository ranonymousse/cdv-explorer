import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paper.config import SNAPSHOT
from paper._utils.io import resolve_output_dir, snapshot_prefix

# Set these directly only when RQ1 needs custom output locations.
FIGURES_DIR = None
TABLES_DIR = None
GENERATE_AUTHORSHIP_PLOTS = True
GENERATE_COLLABORATION_NETWORK_PLOT = True
GENERATE_COLLABORATION_METRICS_TABLE = True


def main() -> None:
    from analysis.artifact_io import (
        load_authorship_payload,
        load_authorship_metrics,
        load_network_data,
        resolve_latest_snapshot_label,
    )
    from paper.RQ1.authorship_overview import plot_authorship_overview
    from paper.RQ1.collaboration_metrics_table import export_collaboration_metrics_table
    from paper.RQ1.collaboration_network import plot_collaboration_network
    from paper.RQ1.creation_over_time import plot_creation_over_time

    snapshot_label = SNAPSHOT or resolve_latest_snapshot_label() or "latest"
    figures_dir = resolve_output_dir(FIGURES_DIR, Path("paper") / "RQ1" / "figures")
    tables_dir = resolve_output_dir(TABLES_DIR, Path("paper") / "RQ1" / "tables")
    filename_prefix = snapshot_prefix(snapshot_label)

    if GENERATE_AUTHORSHIP_PLOTS:
        authorship_metrics = load_authorship_metrics(snapshot=SNAPSHOT)
        plot_creation_over_time(
            proposals_per_year=authorship_metrics.get("proposals_per_year", []),
            output_path=figures_dir / f"{filename_prefix}_creation_over_time.pdf",
            snapshot_label=snapshot_label,
        )
        plot_authorship_overview(
            top_authors=authorship_metrics.get("top_authors", []),
            contribution_histogram=authorship_metrics.get("author_contribution_histogram", []),
            output_path=figures_dir / f"{filename_prefix}_authorship_overview.pdf",
            snapshot_label=snapshot_label,
        )

    if GENERATE_COLLABORATION_NETWORK_PLOT or GENERATE_COLLABORATION_METRICS_TABLE:
        authorship_payload = load_authorship_payload(snapshot=SNAPSHOT)

    if GENERATE_COLLABORATION_NETWORK_PLOT:
        network_data = load_network_data(snapshot=SNAPSHOT)
        plot_collaboration_network(
            network_data=network_data,
            authorship_payload=authorship_payload,
            output_path=figures_dir / f"{filename_prefix}_collaboration_network.pdf",
            snapshot_label=snapshot_label,
        )

    if GENERATE_COLLABORATION_METRICS_TABLE:
        export_collaboration_metrics_table(
            authorship_payload=authorship_payload,
            output_path=tables_dir / f"{filename_prefix}_collaboration_metrics.xlsx",
        )


if __name__ == "__main__":
    main()

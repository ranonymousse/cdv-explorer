import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paper.config import SNAPSHOT
from paper._utils.io import resolve_output_dir, snapshot_prefix

# Set this directly only when RQ1 needs a custom output location.
OUTPUT_DIR = None
GENERATE_AUTHORSHIP_PLOTS = True


def main() -> None:
    from analysis.artifact_io import (
        load_authorship_metrics,
        resolve_latest_snapshot_label,
    )
    from paper.RQ1.authorship_overview import plot_authorship_overview
    from paper.RQ1.creation_over_time import plot_creation_over_time

    snapshot_label = SNAPSHOT or resolve_latest_snapshot_label() or "latest"
    default_relative_path = Path("paper") / "RQ1" / "figures"
    output_dir = resolve_output_dir(OUTPUT_DIR, default_relative_path)
    filename_prefix = snapshot_prefix(snapshot_label)

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


if __name__ == "__main__":
    main()

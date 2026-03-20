import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from paper.config import SNAPSHOT
from paper._utils.io import resolve_output_dir, snapshot_prefix

# Set this directly only when RQ3 needs a custom output location.
OUTPUT_DIR = None


def main() -> None:
    from analysis.artifact_io import load_network_data, resolve_latest_snapshot_label
    from paper.RQ3.dependency_plots import render_default_dependency_plot_suite

    snapshot_label = SNAPSHOT or resolve_latest_snapshot_label() or "latest"
    default_relative_path = Path("paper") / "RQ3" / "figures"
    output_dir = resolve_output_dir(OUTPUT_DIR, default_relative_path)
    filename_prefix = snapshot_prefix(snapshot_label)

    network_data = load_network_data(snapshot=SNAPSHOT)
    render_default_dependency_plot_suite(
        network_data,
        output_dir=output_dir,
        filename_prefix=filename_prefix,
    )


if __name__ == "__main__":
    main()

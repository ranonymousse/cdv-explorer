import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

from analysis.proposal_schema import normalize_proposal_document


def get_git_history(repo_dir: Path, file_path: Path) -> List[Tuple[str, str, str]]:
    """Retrieve commit history for a file using local Git."""
    try:
        relative_file_path = file_path.relative_to(repo_dir)
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "log", "--pretty=format:%H|%ad|%an", "--", str(relative_file_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        commits = [line.split("|") for line in result.stdout.strip().split("\n") if line]
        return [(commit[0], commit[1], commit[2]) for commit in commits]
    except subprocess.CalledProcessError:
        return []


def update_metadata_from_git(
    json_data: Dict[str, Any],
    proposal_file_path: Path,
    repo_dir: Path,
) -> Dict[str, Any]:
    """Populate metadata from Git history in-place and return payload."""
    json_data = normalize_proposal_document(json_data)

    commit_info = get_git_history(repo_dir, proposal_file_path)
    if commit_info:
        last_commit_date = commit_info[0][1]
    else:
        last_commit_date = None

    json_data["meta"].update(
        {
            "last_commit": last_commit_date,
            "total_commits": len(commit_info),
            "git_history": commit_info,
        }
    )
    return json_data

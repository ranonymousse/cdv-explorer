import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis.evolution.metrics import prepare_evolution_payload
from analysis.evolution.mining import extract_status_timeline


class EvolutionStatusTests(unittest.TestCase):
    def test_extract_status_timeline_uses_committer_dates_and_keeps_standard_transitions(self) -> None:
        log_stdout = "\n".join(
            [
                "__COMMIT__newcommit|2026-01-12T14:22:25-08:00|Murch",
                "M\tbip-0001.mediawiki",
                "__COMMIT__oldcommit|2025-10-01T10:00:00+00:00|Alice",
                "M\tbip-0001.mediawiki",
            ]
        )
        show_stdout = "<pre>\nStatus: Draft\n</pre>\n"

        def fake_run(args, **kwargs):
            if "log" in args:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=log_stdout)
            if "show" in args:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=show_stdout)
            raise AssertionError(f"Unexpected subprocess invocation: {args}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir)
            file_path = repo_dir / "bip-0001.mediawiki"
            file_path.write_text(show_stdout, encoding="utf-8")

            with patch("analysis.evolution.mining.subprocess.run", side_effect=fake_run):
                timeline = extract_status_timeline(
                    repo_dir=repo_dir,
                    file_path=file_path,
                )

        self.assertEqual(
            timeline,
            [
                {
                    "commit": "oldcommit",
                    "timestamp": "2025-10-01T10:00:00+00:00",
                    "date": "2025-10-01",
                    "author": "Alice",
                    "status": "Draft",
                    "standard": "bip2",
                },
                {
                    "commit": "newcommit",
                    "timestamp": "2026-01-12T14:22:25-08:00",
                    "date": "2026-01-12",
                    "author": "Murch",
                    "status": "Draft",
                    "standard": "bip3",
                },
            ],
        )

    def test_prepare_evolution_payload_splits_bip3_cutover_period(self) -> None:
        proposal_data = [
            {
                "raw": {"preamble": {"bip": "1"}},
                "insights": {
                    "changes_in_status": [
                        {"date": "2025-10-01", "status": "Draft", "standard": "bip2"},
                        {"date": "2026-01-12", "status": "Draft", "standard": "bip3"},
                    ]
                },
            },
            {
                "raw": {"preamble": {"bip": "2"}},
                "insights": {
                    "changes_in_status": [
                        {"date": "2025-10-01", "status": "Final", "standard": "bip2"},
                        {"date": "2026-01-12", "status": "Deployed", "standard": "bip3"},
                    ]
                },
            },
            {
                "raw": {"preamble": {"bip": "3"}},
                "insights": {
                    "changes_in_status": [
                        {"date": "2025-10-01", "status": "Proposed", "standard": "bip2"},
                        {"date": "2026-01-12", "status": "Complete", "standard": "bip3"},
                    ]
                },
            },
        ]

        payload = prepare_evolution_payload(
            proposal_data=proposal_data,
            snapshot_label="2026-03-16",
            id_field="bip",
        )

        self.assertEqual(
            [row["period"] for row in payload["status_evolution"]["rows"]],
            ["2025-Q4", "2026-Q1", "2026-Q1"],
        )
        self.assertEqual(
            [row["period_key"] for row in payload["status_evolution"]["rows"]],
            ["2025-Q4", "2026-Q1-pre-bip3", "2026-Q1-post-bip3"],
        )
        self.assertEqual(payload["meta"]["first_period"], "2025-Q4")
        self.assertEqual(payload["meta"]["last_period"], "2026-Q1")
        self.assertEqual(payload["meta"]["milestones"], [{"date": "2026-01-12", "label": "BIP3 Activation"}])

        segmented_rows = {
            row["period_key"]: row for row in payload["status_evolution_segmented"]["rows"]
        }

        self.assertEqual(segmented_rows["2025-Q4"]["values"]["bip2:Draft"], 1)
        self.assertEqual(segmented_rows["2025-Q4"]["values"]["bip2:Final"], 1)
        self.assertEqual(segmented_rows["2025-Q4"]["values"]["bip2:Proposed"], 1)
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["period_end"], "2026-01-11")
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["values"]["bip2:Draft"], 1)
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["values"]["bip2:Final"], 1)
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["values"]["bip2:Proposed"], 1)
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["values"]["bip3:Draft"], 0)
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["values"]["bip3:Deployed"], 0)
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["values"]["bip3:Complete"], 0)
        self.assertEqual(segmented_rows["2026-Q1-post-bip3"]["period_start"], "2026-01-12")
        self.assertEqual(segmented_rows["2026-Q1-post-bip3"]["values"]["bip3:Draft"], 1)
        self.assertEqual(segmented_rows["2026-Q1-post-bip3"]["values"]["bip3:Deployed"], 1)
        self.assertEqual(segmented_rows["2026-Q1-post-bip3"]["values"]["bip3:Complete"], 1)

    def test_prepare_evolution_payload_does_not_project_bip3_before_harvested_transition(self) -> None:
        proposal_data = [
            {
                "raw": {"preamble": {"bip": "1"}},
                "insights": {
                    "changes_in_status": [
                        {"date": "2025-10-01", "status": "Draft", "standard": "bip2"},
                        {"date": "2026-01-15", "status": "Draft", "standard": "bip3"},
                    ]
                },
            }
        ]

        payload = prepare_evolution_payload(
            proposal_data=proposal_data,
            snapshot_label="2026-03-16",
            id_field="bip",
        )

        segmented_rows = {
            row["period_key"]: row for row in payload["status_evolution_segmented"]["rows"]
        }

        self.assertEqual(segmented_rows["2025-Q4"]["values"]["bip2:Draft"], 1)
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["values"]["bip2:Draft"], 1)
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["values"]["bip3:Draft"], 0)
        self.assertEqual(segmented_rows["2026-Q1-post-bip3"]["values"]["bip3:Draft"], 1)

    def test_prepare_evolution_payload_resolves_ambiguous_draft_by_event_date_when_standard_is_missing(self) -> None:
        proposal_data = [
            {
                "raw": {"preamble": {"bip": "1"}},
                "insights": {
                    "changes_in_status": [
                        {"date": "2025-10-01", "status": "Draft"},
                        {"date": "2026-01-15", "status": "Draft"},
                    ]
                },
            }
        ]

        payload = prepare_evolution_payload(
            proposal_data=proposal_data,
            snapshot_label="2026-03-16",
            id_field="bip",
        )

        segmented_rows = {
            row["period_key"]: row for row in payload["status_evolution_segmented"]["rows"]
        }

        self.assertEqual(segmented_rows["2025-Q4"]["values"]["bip2:Draft"], 1)
        self.assertEqual(segmented_rows["2026-Q1-pre-bip3"]["values"]["bip2:Draft"], 1)
        self.assertEqual(segmented_rows["2026-Q1-post-bip3"]["values"]["bip3:Draft"], 1)

    def test_extract_status_timeline_ignores_reused_placeholder_history_from_other_proposals(self) -> None:
        log_stdout = "\n".join(
            [
                "__COMMIT__finalcommit|2025-09-01T09:08:50-06:00|Jon Atack",
                "M\tbip-0155.mediawiki",
                "__COMMIT__renamecommit|2019-07-18T00:17:55+02:00|Wladimir J. van der Laan",
                "R099\tbip-XXXX.mediawiki\tbip-0155.mediawiki",
                "__COMMIT__wrongplaceholder|2019-03-02T14:50:23-08:00|cgilliard",
                "M\tbip-XXXX.mediawiki",
                "__COMMIT__rightplaceholder|2019-02-27T10:28:34+01:00|Wladimir J. van der Laan",
                "M\tbip-XXXX.mediawiki",
            ]
        )

        current_content = """<pre>
  BIP: 155
  Title: addrv2 message
  Author: Wladimir J. van der Laan <laanwj@gmail.com>
  Status: Deployed
  Created: 2019-02-27
</pre>
"""
        right_placeholder_content = """<pre>
  BIP: ???
  Title: addrv2 message
  Author: Wladimir J. van der Laan <laanwj@gmail.com>
  Status: Draft
  Created: 2019-02-27
</pre>
"""
        wrong_placeholder_content = """<pre>
  BIP: ???
  Title: Signatures of Messages using Bitcoin Private Keys
  Author: Christopher Gilliard <christopher.gilliard@gmail.com>
  Status: Proposal
  Created: 2019-02-16
</pre>
"""
        final_content = """<pre>
  BIP: 155
  Title: addrv2 message
  Author: Wladimir J. van der Laan <laanwj@gmail.com>
  Status: Final
  Created: 2019-02-27
</pre>
"""

        show_stdout_by_spec = {
            "finalcommit:bip-0155.mediawiki": final_content,
            "renamecommit:bip-0155.mediawiki": right_placeholder_content,
            "wrongplaceholder:bip-XXXX.mediawiki": wrong_placeholder_content,
            "rightplaceholder:bip-XXXX.mediawiki": right_placeholder_content,
        }

        def fake_run(args, **kwargs):
            if "log" in args:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=log_stdout)
            if "show" in args:
                spec = args[-1]
                stdout = show_stdout_by_spec.get(spec)
                if stdout is None:
                    raise AssertionError(f"Unexpected git show spec: {spec}")
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout)
            raise AssertionError(f"Unexpected subprocess invocation: {args}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir)
            file_path = repo_dir / "bip-0155.mediawiki"
            file_path.write_text(current_content, encoding="utf-8")

            with patch("analysis.evolution.mining.subprocess.run", side_effect=fake_run):
                timeline = extract_status_timeline(
                    repo_dir=repo_dir,
                    file_path=file_path,
                )

        self.assertEqual(
            timeline,
            [
                {
                    "commit": "rightplaceholder",
                    "timestamp": "2019-02-27T10:28:34+01:00",
                    "date": "2019-02-27",
                    "author": "Wladimir J. van der Laan",
                    "status": "Draft",
                    "standard": "bip2",
                },
                {
                    "commit": "finalcommit",
                    "timestamp": "2025-09-01T09:08:50-06:00",
                    "date": "2025-09-01",
                    "author": "Jon Atack",
                    "status": "Final",
                    "standard": "bip2",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()

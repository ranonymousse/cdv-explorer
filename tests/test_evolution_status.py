import subprocess
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

        with patch("analysis.evolution.mining.subprocess.run", side_effect=fake_run):
            timeline = extract_status_timeline(
                repo_dir=Path("/tmp/repo"),
                file_path=Path("/tmp/repo/bip-0001.mediawiki"),
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


if __name__ == "__main__":
    unittest.main()

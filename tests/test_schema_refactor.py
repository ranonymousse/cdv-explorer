import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

if "tqdm" not in sys.modules:
    fake_tqdm = types.ModuleType("tqdm")

    class _FakeTqdm:
        def __init__(self, iterable=None, total=None, **_kwargs):
            self._iterable = list(iterable) if iterable is not None else []
            self.total = total if total is not None else len(self._iterable)
            self.n = 0

        def __iter__(self):
            for item in self._iterable:
                yield item
                self.n += 1

        def set_postfix_str(self, *_args, **_kwargs):
            return None

        def update(self, value=1):
            self.n += value

        def close(self):
            return None

    fake_tqdm.tqdm = _FakeTqdm
    sys.modules["tqdm"] = fake_tqdm

if "openai" not in sys.modules:
    fake_openai = types.ModuleType("openai")

    class _FakeOpenAI:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    fake_openai.OpenAI = _FakeOpenAI
    sys.modules["openai"] = fake_openai

from analysis.conformity.metrics import extract_conformity_metrics
from analysis.dependencies.network import build_network_data
from analysis.evolution.metrics import prepare_evolution_payload
from analysis.proposal_schema import normalize_proposal_document
from ip_processing import process_ip_files
from preamble_extraction import save_preamble_to_json


def legacy_proposal(
    proposal_id: str,
    *,
    requires: str | None = None,
    superseded_by: str | None = None,
    explicit_references: list[str] | None = None,
    implicit_dependencies: list[str] | None = None,
) -> dict:
    return {
        "raw": {
            "preamble": {
                "bip": proposal_id,
                "title": f"Proposal {proposal_id}",
                "author": [f"Author {proposal_id}"],
                "status": "Draft",
                "type": "Standard",
                "created": "2020-01-01",
                "layer": "Consensus",
                "requires": requires,
                "replaces": None,
                "superseded_by": superseded_by,
            }
        },
        "metadata": {
            "last_commit": "2020-01-02",
            "total_commits": 1,
            "git_history": [["abc", "2020-01-02", "Author"]],
            "contributors": 1,
        },
        "compliance": {
            "score": 75.0,
            "bip2": {
                "score": 70.0,
                "checks": [
                    {
                        "id": "bip2.required_field.bip",
                        "label": "Required field 'bip' is present",
                        "category": "required_field",
                        "standard": "bip2",
                        "passed": True,
                    }
                ],
            },
            "bip3": {
                "score": 80.0,
                "checks": [],
            },
        },
        "history": {
            "status_timeline": [
                {
                    "proposal_id": proposal_id,
                    "date": "2020-01-01",
                    "status": "Draft",
                    "standard": "bip2",
                }
            ]
        },
        "insights": {
            "word_list": {"bitcoin": 3, "proposal": 2},
            "explicit_references": explicit_references or [],
            "explicit_dependencies": [f"BIP {requires}"] if requires else [],
            "implicit_dependencies": implicit_dependencies or [],
        },
    }


class SchemaRefactorTests(unittest.TestCase):
    def test_normalize_legacy_document_into_canonical_shape(self) -> None:
        normalized = normalize_proposal_document(
            legacy_proposal(
                "1",
                requires="2",
                explicit_references=["BIP 2"],
                implicit_dependencies=["BIP 3"],
            )
        )

        self.assertEqual(list(normalized.keys())[:3], ["raw", "meta", "insights"])
        self.assertNotIn("metadata", normalized)
        self.assertNotIn("history", normalized)
        self.assertNotIn("compliance", normalized)
        self.assertEqual(normalized["meta"]["last_commit"], "2020-01-02")
        self.assertEqual(normalized["insights"]["formal_compliance"]["score"], 75.0)
        self.assertEqual(normalized["insights"]["changes_in_status"][0]["status"], "Draft")
        self.assertNotIn("interrelations", normalized["raw"]["preamble"])
        self.assertEqual(normalized["insights"]["interrelations"]["preamble_extracted"], ["BIP 2"])
        self.assertEqual(normalized["insights"]["interrelations"]["body_extracted_regex"], ["BIP 2"])
        self.assertEqual(normalized["insights"]["interrelations"]["body_extracted_llm"], ["BIP 3"])

    def test_normalize_legacy_preamble_aliases_to_proposed_replacement(self) -> None:
        normalized = normalize_proposal_document(
            legacy_proposal("1", superseded_by="7")
        )

        self.assertEqual(normalized["raw"]["preamble"]["proposed_replacement"], "7")
        self.assertNotIn("superseded_by", normalized["raw"]["preamble"])
        self.assertNotIn("interrelations", normalized["raw"]["preamble"])

    def test_save_preamble_to_json_writes_only_canonical_top_level_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_preamble_to_json(
                preamble={
                    "bip": "1",
                    "title": "Proposal 1",
                    "author": ["Author 1"],
                    "status": "Draft",
                    "type": "Standard",
                    "created": "2020-01-01",
                },
                output_dir=tmp_dir,
                _file_name="bip-0001.md",
                compliance_payload={"score": 91.0},
            )

            output_path = Path(tmp_dir) / "bip-0001.json"
            with output_path.open(encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertEqual(list(payload.keys()), ["raw", "meta", "insights"])
            self.assertNotIn("metadata", payload)
            self.assertNotIn("history", payload)
            self.assertNotIn("compliance", payload)
            self.assertEqual(payload["insights"]["formal_compliance"]["score"], 91.0)
            self.assertNotIn("interrelations", payload["raw"]["preamble"])

    def test_analysis_builders_accept_old_and_new_shapes(self) -> None:
        legacy_documents = [
            legacy_proposal(
                "1",
                requires="2",
                superseded_by="2",
                explicit_references=["BIP 2"],
                implicit_dependencies=["BIP 2"],
            ),
            legacy_proposal("2"),
        ]
        canonical_documents = [normalize_proposal_document(document) for document in legacy_documents]

        self.assertEqual(
            build_network_data(legacy_documents, id_field="bip", proposal_label="BIP"),
            build_network_data(canonical_documents, id_field="bip", proposal_label="BIP"),
        )
        self.assertEqual(
            extract_conformity_metrics(legacy_documents, id_field="bip"),
            extract_conformity_metrics(canonical_documents, id_field="bip"),
        )
        self.assertEqual(
            prepare_evolution_payload(legacy_documents, snapshot_label="2020-12-31", id_field="bip"),
            prepare_evolution_payload(canonical_documents, snapshot_label="2020-12-31", id_field="bip"),
        )

    def test_process_ip_files_writes_canonical_meta_and_insights(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            preprocess_dir = root / "preprocess"
            repo_dir = root / "repo"
            preprocess_dir.mkdir()
            repo_dir.mkdir()

            source_json = normalize_proposal_document(
                {
                    "raw": {
                        "preamble": {
                            "bip": "1",
                            "title": "Proposal 1",
                            "author": ["Author 1"],
                            "status": "Draft",
                            "type": "Standard",
                            "created": "2020-01-01",
                            "requires": "2",
                            "replaces": None,
                            "proposed_replacement": None,
                        }
                    }
                }
            )
            with (preprocess_dir / "bip-0001.json").open("w", encoding="utf-8") as handle:
                json.dump(source_json, handle, ensure_ascii=False, indent=2)

            (repo_dir / "bip-0001.md").write_text(
                "BIP 2 is referenced here.\nBitcoin bitcoin proposal proposal.\n",
                encoding="utf-8",
            )

            def fake_update_metadata(document: dict, _proposal_file_path: Path, _repo_dir: Path) -> dict:
                document = normalize_proposal_document(document)
                document["meta"].update(
                    {
                        "last_commit": "2020-01-02",
                        "total_commits": 3,
                        "git_history": [["abc", "2020-01-02", "Author 1"]],
                    }
                )
                return document

            with patch("ip_processing.update_metadata_from_git", side_effect=fake_update_metadata), patch(
                "ip_processing.extract_status_timeline",
                return_value=[{"date": "2020-01-01", "status": "Draft", "standard": "bip2"}],
            ), patch(
                "ip_processing.create_reference_list",
                return_value=["BIP 2"],
            ), patch(
                "ip_processing.create_explicit_dependency_list",
                return_value=["BIP 2"],
            ):
                process_ip_files(
                    input_dir=preprocess_dir,
                    output_dir=preprocess_dir,
                    repo_dir=repo_dir,
                    file_prefix="bip",
                    proposal_label="BIP",
                    id_field="bip",
                    skip_llm=True,
                )

            with (preprocess_dir / "bip-0001.json").open(encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertEqual(list(payload.keys())[:3], ["raw", "meta", "insights"])
            self.assertNotIn("metadata", payload)
            self.assertNotIn("history", payload)
            self.assertNotIn("compliance", payload)
            self.assertEqual(payload["meta"]["total_commits"], 3)
            self.assertIsInstance(payload["insights"]["word_list"], dict)
            self.assertEqual(payload["insights"]["changes_in_status"][0]["status"], "Draft")
            self.assertNotIn("interrelations", payload["raw"]["preamble"])
            self.assertEqual(payload["insights"]["interrelations"]["preamble_extracted"], ["BIP 2"])
            self.assertEqual(payload["insights"]["interrelations"]["body_extracted_regex"], ["BIP 2"])
            self.assertEqual(payload["insights"]["interrelations"]["body_extracted_llm"], [])


if __name__ == "__main__":
    unittest.main()

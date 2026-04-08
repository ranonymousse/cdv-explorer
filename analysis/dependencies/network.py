import json
import csv
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from analysis.dependencies.constants import (
    BODY_EXTRACTED_LLM,
    BODY_EXTRACTED_REGEX,
    PREAMBLE_EXTRACTED,
)
from analysis.proposal_schema import (
    get_formal_compliance,
    get_interrelations,
    get_preamble_interrelations,
    normalize_proposal_document,
)
from pipeline.ecosystem_config import ACTIVE_ECOSYSTEM


CLASSIFICATION_CONFIG = ACTIVE_ECOSYSTEM.get("classification", {})
LAYER_ALIASES = CLASSIFICATION_CONFIG.get("layer_aliases", {})
STATUS_ALIASES = CLASSIFICATION_CONFIG.get("status_aliases", {})
TYPE_ALIASES = CLASSIFICATION_CONFIG.get("type_aliases", {})


def _aggregate_explicit_dependencies(explicit_dependencies: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    seen = set()
    aggregated: List[Dict[str, Any]] = []
    for subtype_links in explicit_dependencies.values():
        for link in subtype_links:
            key = (str(link.get("source")), str(link.get("target")))
            if key in seen:
                continue
            seen.add(key)
            aggregated.append(
                {
                    "source": str(link.get("source")),
                    "target": str(link.get("target")),
                    "value": link.get("value", 1),
                }
            )
    return aggregated


def normalize_proposal_ids(field: Any, proposal_label: str = "IP") -> List[str]:
    if not field:
        return []

    if isinstance(field, list):
        raw_items = field
    else:
        raw_items = str(field).split(",")

    result = []
    label = re.escape(proposal_label)
    id_pattern = re.compile(rf"^\s*(?:{label}[-\s]*)?\d+\s*$", re.IGNORECASE)

    for item in raw_items:
        text = str(item)
        if id_pattern.match(text):
            normalized = re.sub(rf"(?i)^\s*{label}[-\s]*", "", text).strip()
            result.append(normalized)
    return result


def _apply_alias(value: Any, aliases: Dict[str, str]) -> Any:
    if value is None:
        return None
    return aliases.get(value, value)


def load_proposal_json_documents(source_dir: Path) -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    for file_path in sorted(source_dir.glob("*.json")):
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                documents.append(normalize_proposal_document(json.load(handle)))
        except json.JSONDecodeError:
            continue
    return documents


def build_network_data(
    proposal_data: Iterable[Dict[str, Any]],
    id_field: str = "id",
    proposal_label: str = "IP",
) -> Dict[str, Any]:
    nodes = []
    explicit_reference_links = []
    implicit_dependency_links = []
    requires_links = []
    replaces_links = []
    proposed_replacement_links = []
    node_ids = set()

    for proposal in proposal_data:
        if not proposal:
            continue

        preamble = proposal.get("raw", {}).get("preamble", {})
        formal_compliance = get_formal_compliance(proposal)
        insights = proposal.get("insights", {})
        proposal_id = preamble.get(id_field)

        if not proposal_id:
            continue

        proposal_id = str(proposal_id)
        if proposal_id not in node_ids:
            nodes.append(
                {
                    "id": proposal_id,
                    "title": preamble.get("title"),
                    "layer": _apply_alias(preamble.get("layer"), LAYER_ALIASES),
                    "compliance_score": formal_compliance.get("score", preamble.get("compliance_score")),
                    "created": preamble.get("created"),
                    "author": preamble.get("author"),
                    "word_list": insights.get("word_list"),
                    "status": _apply_alias(preamble.get("status"), STATUS_ALIASES),
                    "type": _apply_alias(preamble.get("type"), TYPE_ALIASES),
                }
            )
            node_ids.add(proposal_id)

    for proposal in proposal_data:
        if not proposal:
            continue

        preamble = proposal.get("raw", {}).get("preamble", {})
        interrelations = get_interrelations(proposal)
        proposal_id = preamble.get(id_field)

        if not proposal_id:
            continue

        proposal_id = str(proposal_id)
        if proposal_id not in node_ids:
            continue

        references_field = interrelations.get(BODY_EXTRACTED_REGEX)

        for ref_id in normalize_proposal_ids(references_field, proposal_label=proposal_label):
            if ref_id in node_ids:
                explicit_reference_links.append({"source": proposal_id, "target": ref_id, "value": 1})

        for dep_id in normalize_proposal_ids(interrelations.get(BODY_EXTRACTED_LLM), proposal_label=proposal_label):
            if dep_id in node_ids:
                implicit_dependency_links.append({"source": proposal_id, "target": dep_id, "value": 1})

        preamble_interrelations = get_preamble_interrelations(preamble)

        for req_id in normalize_proposal_ids(preamble_interrelations.get("requires"), proposal_label=proposal_label):
            if req_id in node_ids:
                requires_links.append({"source": proposal_id, "target": req_id, "value": 1})

        for rep_id in normalize_proposal_ids(preamble_interrelations.get("replaces"), proposal_label=proposal_label):
            if rep_id in node_ids:
                replaces_links.append({"source": proposal_id, "target": rep_id, "value": 1})

        for sup_id in normalize_proposal_ids(
            preamble_interrelations.get("proposed_replacement"),
            proposal_label=proposal_label,
        ):
            if sup_id in node_ids:
                proposed_replacement_links.append({"source": proposal_id, "target": sup_id, "value": 1})

    explicit_dependency_links = {
        "requires": requires_links,
        "replaces": replaces_links,
        "proposed_replacement": proposed_replacement_links,
    }

    return {
        "nodes": nodes,
        "links": {
            BODY_EXTRACTED_REGEX: explicit_reference_links,
            PREAMBLE_EXTRACTED: explicit_dependency_links,
            BODY_EXTRACTED_LLM: implicit_dependency_links,
        },
    }


def save_network_data_artifacts(network_data: Dict[str, Any], output_stem: Path) -> None:
    output_stem.parent.mkdir(parents=True, exist_ok=True)

    json_path = output_stem.with_suffix(".json")

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(network_data, handle, ensure_ascii=False, indent=2)

    nodes_csv_path = output_stem.parent / f"{output_stem.name}_nodes.csv"
    with nodes_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["id", "title", "layer", "compliance_score", "created", "author", "status", "type"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for node in network_data.get("nodes", []):
            row = {k: node.get(k) for k in fieldnames}
            if isinstance(row.get("author"), list):
                row["author"] = " | ".join(str(a) for a in row["author"])
            writer.writerow(row)

    links_by_type = network_data.get("links", {})
    for link_type, links in links_by_type.items():
        if link_type == PREAMBLE_EXTRACTED and isinstance(links, dict):
            aggregate_links = _aggregate_explicit_dependencies(links)
            aggregate_path = output_stem.parent / f"{output_stem.name}_{link_type}_edges.csv"
            with aggregate_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["source", "target", "value"])
                writer.writeheader()
                for link in aggregate_links:
                    writer.writerow(link)

            for subtype, subtype_links in links.items():
                links_csv_path = output_stem.parent / f"{output_stem.name}_{link_type}_{subtype}_edges.csv"
                with links_csv_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=["source", "target", "value"])
                    writer.writeheader()
                    for link in subtype_links:
                        writer.writerow(
                            {
                                "source": link.get("source"),
                                "target": link.get("target"),
                                "value": link.get("value", 1),
                            }
                        )
            continue

        links_csv_path = output_stem.parent / f"{output_stem.name}_{link_type}_edges.csv"
        with links_csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["source", "target", "value"])
            writer.writeheader()
            for link in links:
                writer.writerow(
                    {
                        "source": link.get("source"),
                        "target": link.get("target"),
                        "value": link.get("value", 1),
                    }
                )

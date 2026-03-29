import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.artifact_io import load_network_data, resolve_latest_snapshot_label
from analysis.dependencies.constants import (
    BODY_EXTRACTED_LLM,
    BODY_EXTRACTED_REGEX,
    DEPENDENCY_APPROACH_SHORT_LABELS,
    PREAMBLE_EXTRACTED,
)
from analysis.external_links import get_bips_dev_base_url
from paper.RQ2.dependency_plots import compute_layout_positions, get_links_by_type, resolve_near_overlaps
from paper._utils.io import resolve_output_dir, snapshot_prefix
from paper.config import SNAPSHOT


BIPS_DEV_BASE_URL = get_bips_dev_base_url()

DEFAULT_FOCUS_BIPS = [1, 2, 3]
DEFAULT_LAYOUT_NAME = "kamada_kawai"
DEFAULT_OUTPUT_DIR = Path("paper") / "RQ2" / "outputs"
DIFF_LAYOUT_COMPACTION = 0.6
DIFF_LAYOUT_COMPACTION_BY_LAYOUT = {
    "spectral": 0.92,
    "circular": 0.9,
    "shell": 0.88,
    "bipartite": 0.95,
    "multipartite": 0.98,
}
DIFF_LAYOUT_OVERLAP_THRESHOLD = 0.085
DIFF_NODE_SIZE_MIN = 320
DIFF_NODE_SIZE_MAX = 980
DIFF_EDGE_WIDTH = 2.0
DIFF_LABEL_FONT_SIZE = 7.8
DIFF_LABEL_OFFSET = 0.035
LAYOUT_EDGE_TYPES = (PREAMBLE_EXTRACTED, BODY_EXTRACTED_REGEX, BODY_EXTRACTED_LLM)
TYPE_ORDER = ["Process", "Informational", "Specification"]
TYPE_COLORS = {
    "Process": "#4e79a7",
    "Informational": "#f28e2c",
    "Specification": "#e15759",
}
FALLBACK_TYPE_COLOR = "#9e9e9e"
COMPARISON_PLOTS = (
    {
        "filename_stem": "preamlbe_vs_reges",
        "approach": BODY_EXTRACTED_REGEX,
        "baseline": PREAMBLE_EXTRACTED,
        "title": "Selected proposals with differential dependencies (Regex vs. Preamble)",
    },
    {
        "filename_stem": "regex_vs_llm",
        "approach": BODY_EXTRACTED_LLM,
        "baseline": BODY_EXTRACTED_REGEX,
        "title": "Selected proposals with differential dependencies (LLM vs. Regex)",
    },
)


def _build_edge_key(source: Any, target: Any) -> tuple[str, str]:
    return str(source), str(target)


def _normalize_focus_ids(bips: Iterable[int | str] | None) -> set[str]:
    normalized = set()
    if bips is None:
        return normalized

    for value in bips:
        match = re.search(r"(\d+)", str(value))
        if match:
            normalized.add(str(int(match.group(1))))
    return normalized


def _type_color(value: Any) -> str:
    return TYPE_COLORS.get(str(value).strip(), FALLBACK_TYPE_COLOR)


def _edge_in_focus_neighborhood(source_id: str, target_id: str, focus_ids: set[str]) -> bool:
    if not focus_ids:
        return True
    return source_id in focus_ids or target_id in focus_ids


def _collect_display_node_ids(network_data: Dict[str, Any], focus_bips: Sequence[int | str] | None) -> tuple[set[str], set[str]]:
    node_ids = {str(node.get("id")) for node in network_data.get("nodes", []) if node.get("id") is not None}
    focus_ids = _normalize_focus_ids(focus_bips)
    if not focus_ids:
        return node_ids, focus_ids

    display_ids = {node_id for node_id in node_ids if node_id in focus_ids}
    for link_type in LAYOUT_EDGE_TYPES:
        for edge in get_links_by_type(network_data.get("links", {}), link_type):
            source_id = str(edge.get("source"))
            target_id = str(edge.get("target"))
            if _edge_in_focus_neighborhood(source_id, target_id, focus_ids):
                if source_id in node_ids:
                    display_ids.add(source_id)
                if target_id in node_ids:
                    display_ids.add(target_id)
    return display_ids, focus_ids


def _assign_multipartite_subsets(graph: nx.DiGraph, focus_ids: set[str]) -> None:
    if not focus_ids:
        for node_id in graph.nodes():
            graph.nodes[node_id]["subset"] = 0
        return

    ordered_focus_ids = sorted((node_id for node_id in graph.nodes() if node_id in focus_ids), key=int)
    focus_rank = {node_id: index for index, node_id in enumerate(ordered_focus_ids)}

    for focus_id, rank in focus_rank.items():
        graph.nodes[focus_id]["subset"] = 2 * rank
        graph.nodes[focus_id]["anchor_focus"] = focus_id

    for node_id in graph.nodes():
        if node_id in focus_rank:
            continue

        scored_focuses = []
        for focus_id in ordered_focus_ids:
            relation_score = int(graph.has_edge(node_id, focus_id)) + int(graph.has_edge(focus_id, node_id))
            if relation_score <= 0:
                continue
            scored_focuses.append((relation_score, -focus_rank[focus_id], focus_id))

        if scored_focuses:
            scored_focuses.sort(reverse=True)
            anchor_focus = scored_focuses[0][2]
        else:
            anchor_focus = ordered_focus_ids[0]

        graph.nodes[node_id]["anchor_focus"] = anchor_focus
        graph.nodes[node_id]["subset"] = 2 * focus_rank[anchor_focus] + 1


def _build_layout_graph(network_data: Dict[str, Any], display_ids: set[str], focus_ids: set[str]) -> nx.DiGraph:
    graph = nx.DiGraph()

    for node in network_data.get("nodes", []):
        node_id = str(node.get("id"))
        if node_id not in display_ids:
            continue
        proposal_type = str(node.get("type")).strip() or "Unknown Type"
        graph.add_node(node_id, group=proposal_type)

    seen_edges = set()
    for link_type in LAYOUT_EDGE_TYPES:
        for edge in get_links_by_type(network_data.get("links", {}), link_type):
            source_id = str(edge.get("source"))
            target_id = str(edge.get("target"))
            key = _build_edge_key(source_id, target_id)
            if (
                source_id not in display_ids
                or target_id not in display_ids
                or not _edge_in_focus_neighborhood(source_id, target_id, focus_ids)
                or key in seen_edges
            ):
                continue
            graph.add_edge(source_id, target_id)
            seen_edges.add(key)

    _assign_multipartite_subsets(graph, focus_ids)
    return graph


def _compute_base_positions(graph: nx.DiGraph, layout_name: str = DEFAULT_LAYOUT_NAME) -> dict[str, Any]:
    if graph.number_of_nodes() == 0:
        return {}
    try:
        return compute_layout_positions(graph, layout_name)
    except (ImportError, ModuleNotFoundError):
        if layout_name == "kamada_kawai":
            return compute_layout_positions(graph, "spring_default")
        raise


def _compact_positions(pos: dict[str, Any], compaction: float) -> dict[str, Any]:
    if len(pos) <= 1:
        return pos

    x_center = sum(coords[0] for coords in pos.values()) / len(pos)
    y_center = sum(coords[1] for coords in pos.values()) / len(pos)
    compacted = {
        node_id: (
            x_center + (coords[0] - x_center) * compaction,
            y_center + (coords[1] - y_center) * compaction,
        )
        for node_id, coords in pos.items()
    }
    resolve_near_overlaps(compacted, threshold=DIFF_LAYOUT_OVERLAP_THRESHOLD, max_iterations=20)
    return compacted


def _get_layout_compaction(layout_name: str) -> float:
    return DIFF_LAYOUT_COMPACTION_BY_LAYOUT.get(layout_name, DIFF_LAYOUT_COMPACTION)


def _compute_axis_limits(pos: dict[str, Any]) -> tuple[float, float, float, float]:
    if not pos:
        return (-1.0, 1.0, -1.0, 1.0)

    x_values = [coords[0] for coords in pos.values()]
    y_values = [coords[1] for coords in pos.values()]
    x_span = (max(x_values) - min(x_values)) or 1.0
    y_span = (max(y_values) - min(y_values)) or 1.0
    x_margin = 0.18 * x_span
    y_margin = 0.18 * y_span
    return (
        min(x_values) - x_margin,
        max(x_values) + x_margin,
        min(y_values) - y_margin,
        max(y_values) + y_margin,
    )


def _build_comparison_edges(
    network_links: Dict[str, Any],
    *,
    approach_type: str,
    baseline_type: str,
    display_ids: set[str],
    focus_ids: set[str],
) -> dict[str, list[tuple[str, str]]]:
    approach_edges = {
        _build_edge_key(edge.get("source"), edge.get("target"))
        for edge in get_links_by_type(network_links, approach_type)
        if (
            str(edge.get("source")) in display_ids
            and str(edge.get("target")) in display_ids
            and _edge_in_focus_neighborhood(str(edge.get("source")), str(edge.get("target")), focus_ids)
        )
    }
    baseline_edges = {
        _build_edge_key(edge.get("source"), edge.get("target"))
        for edge in get_links_by_type(network_links, baseline_type)
        if (
            str(edge.get("source")) in display_ids
            and str(edge.get("target")) in display_ids
            and _edge_in_focus_neighborhood(str(edge.get("source")), str(edge.get("target")), focus_ids)
        )
    }

    overlap = sorted(approach_edges & baseline_edges, key=lambda item: (int(item[0]), int(item[1])))
    approach_only = sorted(approach_edges - baseline_edges, key=lambda item: (int(item[0]), int(item[1])))
    baseline_only = sorted(baseline_edges - approach_edges, key=lambda item: (int(item[0]), int(item[1])))

    return {
        "approach_only": approach_only,
        "overlap": overlap,
        "baseline_only": baseline_only,
    }


def _build_type_legend_handles(graph: nx.DiGraph) -> list[Line2D]:
    group_attr = nx.get_node_attributes(graph, "group")
    group_counts = Counter(group_attr.values())
    handles = []

    for group in TYPE_ORDER:
        if group not in group_counts:
            continue
        handles.append(
            Line2D(
                [],
                [],
                marker="o",
                color="w",
                label=f"{group} $(n={group_counts[group]})$",
                markerfacecolor=_type_color(group),
                markeredgecolor="black",
                markeredgewidth=0.9,
                markersize=10,
            )
        )

    remaining_groups = sorted(set(group_counts) - set(TYPE_ORDER))
    for group in remaining_groups:
        handles.append(
            Line2D(
                [],
                [],
                marker="o",
                color="w",
                label=f"{group} $(n={group_counts[group]})$",
                markerfacecolor=_type_color(group),
                markeredgecolor="black",
                markeredgewidth=0.9,
                markersize=10,
            )
        )

    return handles


def _build_edge_legend_handles(
    *,
    approach_type: str,
    baseline_type: str,
    comparison_edges: dict[str, list[tuple[str, str]]],
) -> list[Line2D]:
    approach_label = DEPENDENCY_APPROACH_SHORT_LABELS[approach_type]
    baseline_label = DEPENDENCY_APPROACH_SHORT_LABELS[baseline_type]
    return [
        Line2D(
            [1],
            [0],
            color="gray",
            linestyle="solid",
            linewidth=DIFF_EDGE_WIDTH,
            label=f"{approach_label} only $(n={len(comparison_edges['approach_only'])})$",
        ),
        Line2D(
            [1],
            [0],
            color="green",
            linestyle="solid",
            linewidth=DIFF_EDGE_WIDTH,
            label=f"Also in {baseline_label} $(n={len(comparison_edges['overlap'])})$",
        ),
        Line2D(
            [1],
            [0],
            color="red",
            linestyle="dashed",
            linewidth=DIFF_EDGE_WIDTH,
            label=f"Missing from {approach_label} $(n={len(comparison_edges['baseline_only'])})$",
        ),
    ]


def _compute_node_sizes(graph: nx.DiGraph, ordered_nodes: Sequence[str]) -> list[float]:
    degrees = dict(graph.degree())
    degree_values = [degrees.get(node_id, 0) for node_id in ordered_nodes]
    if not degree_values:
        return []

    min_degree = min(degree_values)
    max_degree = max(degree_values)
    if max_degree == min_degree:
        return [0.5 * (DIFF_NODE_SIZE_MIN + DIFF_NODE_SIZE_MAX)] * len(ordered_nodes)

    sizes = []
    for degree in degree_values:
        normalized = (degree - min_degree) / (max_degree - min_degree)
        sizes.append(DIFF_NODE_SIZE_MIN + normalized * (DIFF_NODE_SIZE_MAX - DIFF_NODE_SIZE_MIN))
    return sizes


def _compute_label_positions(pos: dict[str, Any], ordered_nodes: Sequence[str], node_sizes: Sequence[float]) -> dict[str, tuple[float, float, str, str]]:
    if not pos:
        return {}

    x_values = [coords[0] for coords in pos.values()]
    y_values = [coords[1] for coords in pos.values()]
    x_center = sum(x_values) / len(x_values)
    y_center = sum(y_values) / len(y_values)
    x_span = (max(x_values) - min(x_values)) or 1.0
    y_span = (max(y_values) - min(y_values)) or 1.0
    diag = math.hypot(x_span, y_span) or 1.0

    label_positions: dict[str, tuple[float, float, str, str]] = {}
    for node_id, node_size in zip(ordered_nodes, node_sizes):
        x_coord, y_coord = pos[node_id]
        dx = x_coord - x_center
        dy = y_coord - y_center
        norm = math.hypot(dx, dy)
        if norm < 1e-9:
            dx, dy = 1.0, 1.0
            norm = math.hypot(dx, dy)
        unit_x = dx / norm
        unit_y = dy / norm
        radial_offset = DIFF_LABEL_OFFSET * diag + 0.00003 * node_size
        label_x = x_coord + unit_x * radial_offset
        label_y = y_coord + unit_y * radial_offset
        label_positions[node_id] = (
            label_x,
            label_y,
            "left" if unit_x >= 0 else "right",
            "bottom" if unit_y >= 0 else "top",
        )

    return label_positions


def _draw_comparison_plot(
    graph: nx.DiGraph,
    pos: dict[str, Any],
    axis_limits: tuple[float, float, float, float],
    *,
    comparison_edges: dict[str, list[tuple[str, str]]],
    approach_type: str,
    baseline_type: str,
    title: str,
    output_path: Path,
) -> None:
    if graph.number_of_nodes() == 0:
        return

    ordered_nodes = sorted(graph.nodes(), key=int)
    node_groups = nx.get_node_attributes(graph, "group")
    node_colors = [_type_color(node_groups.get(node_id, "Unknown Type")) for node_id in ordered_nodes]
    node_sizes = _compute_node_sizes(graph, ordered_nodes)
    label_positions = _compute_label_positions(pos, ordered_nodes, node_sizes)

    plt.figure(figsize=(10, 6))
    ax = plt.gca()

    nx.draw_networkx_nodes(
        graph,
        pos,
        nodelist=ordered_nodes,
        node_size=node_sizes,
        node_color=node_colors,
        alpha=0.85,
        edgecolors="black",
        linewidths=1.0,
    )

    edge_styles = {
        "approach_only": {"color": "gray", "style": "solid", "alpha": 0.7},
        "overlap": {"color": "green", "style": "solid", "alpha": 0.8},
        "baseline_only": {"color": "red", "style": "dashed", "alpha": 0.8},
    }
    for status, edgelist in comparison_edges.items():
        if not edgelist:
            continue
        style_info = edge_styles[status]
        nx.draw_networkx_edges(
            graph,
            pos,
            edgelist=edgelist,
            edge_color=style_info["color"],
            style=style_info["style"],
            width=DIFF_EDGE_WIDTH,
            alpha=style_info["alpha"],
            arrows=True,
            arrowstyle="-|>",
            arrowsize=16,
            node_size=node_sizes,
            nodelist=ordered_nodes,
            node_shape="o",
            connectionstyle="arc3,rad=0.2",
            min_source_margin=0,
            min_target_margin=0,
            ax=ax,
        )

    for node_id in ordered_nodes:
        x, y, ha, va = label_positions[node_id]
        url = f"{BIPS_DEV_BASE_URL}/{node_id}"
        plt.text(
            x,
            y,
            f"BIP {node_id}",
            fontsize=DIFF_LABEL_FONT_SIZE,
            fontweight="semibold",
            family="sans-serif",
            ha=ha,
            va=va,
            url=url,
            bbox={"boxstyle": "round,pad=0.14", "facecolor": "white", "edgecolor": "none", "alpha": 0.75},
        )

    plt.title(title, pad=25, y=1.0)

    legend_handles = _build_type_legend_handles(graph) + _build_edge_legend_handles(
        approach_type=approach_type,
        baseline_type=baseline_type,
        comparison_edges=comparison_edges,
    )
    if legend_handles:
        ncol = math.ceil(len(legend_handles) / 2)
        plt.legend(
            handles=legend_handles,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.95),
            ncol=ncol,
            fancybox=True,
            shadow=True,
            fontsize=8.5,
            columnspacing=1.0,
            handletextpad=0.2,
            labelspacing=0.6,
        )

    ax.set_xlim(axis_limits[0], axis_limits[1])
    ax.set_ylim(axis_limits[2], axis_limits[3])

    plt.axis("off")
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, format="pdf")
    plt.close()


def render_differential_dependency_plots(
    network_data: Dict[str, Any],
    output_dir: Path,
    *,
    filename_prefix: str | None = None,
    focus_bips: Sequence[int | str] = DEFAULT_FOCUS_BIPS,
    layout_name: str = DEFAULT_LAYOUT_NAME,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    display_ids, focus_ids = _collect_display_node_ids(network_data, focus_bips)
    layout_graph = _build_layout_graph(network_data, display_ids, focus_ids)

    # Keep one shared union-layout graph so both plots inherit identical node positions.
    base_pos = _compute_base_positions(layout_graph, layout_name=layout_name)
    pos = _compact_positions(base_pos, compaction=_get_layout_compaction(layout_name))
    axis_limits = _compute_axis_limits(base_pos)

    output_paths: list[Path] = []
    for plot_spec in COMPARISON_PLOTS:
        comparison_edges = _build_comparison_edges(
            network_data.get("links", {}),
            approach_type=plot_spec["approach"],
            baseline_type=plot_spec["baseline"],
            display_ids=display_ids,
            focus_ids=focus_ids,
        )
        prefix = f"{filename_prefix}_" if filename_prefix else ""
        output_path = output_dir / f"{prefix}diffdep_{layout_name}_{plot_spec['filename_stem']}.pdf"
        _draw_comparison_plot(
            layout_graph,
            pos,
            axis_limits,
            comparison_edges=comparison_edges,
            approach_type=plot_spec["approach"],
            baseline_type=plot_spec["baseline"],
            title=plot_spec["title"],
            output_path=output_path,
        )
        output_paths.append(output_path)

    return output_paths


def _parse_bips_argument(raw_value: str | None) -> list[int]:
    if not raw_value:
        return DEFAULT_FOCUS_BIPS
    return [int(match.group(0)) for match in re.finditer(r"\d+", raw_value)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Render differential dependency comparison plots for RQ2.")
    parser.add_argument("--snapshot", default=SNAPSHOT, help="Snapshot label to load, defaults to paper.config.SNAPSHOT.")
    parser.add_argument("--output-dir", default=None, help="Optional output directory override.")
    parser.add_argument(
        "--bips",
        default=",".join(str(bip) for bip in DEFAULT_FOCUS_BIPS),
        help="Comma-separated focus BIP ids used to define the local comparison neighborhood.",
    )
    parser.add_argument(
        "--layout",
        default=DEFAULT_LAYOUT_NAME,
        choices=["spring_default", "spring_spread", "spring_scaled", "planar", "spectral", "shell", "circular", "bipartite", "multipartite", "kamada_kawai"],
        help="Layout algorithm for the shared node positions.",
    )
    args = parser.parse_args()

    snapshot_label = args.snapshot or resolve_latest_snapshot_label() or "latest"
    output_dir = resolve_output_dir(args.output_dir, DEFAULT_OUTPUT_DIR)

    network_data = load_network_data(snapshot=args.snapshot)
    render_differential_dependency_plots(
        network_data,
        output_dir=output_dir,
        filename_prefix=snapshot_prefix(snapshot_label),
        focus_bips=_parse_bips_argument(args.bips),
        layout_name=args.layout,
    )


if __name__ == "__main__":
    main()

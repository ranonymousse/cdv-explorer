import math
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.colors import to_rgba

from paper.RQ1._plotting import save_figure
from paper.RQ1.collaboration_common import build_author_bip_map


CLUSTER_COLORS = [
    "#2a6f97",
    "#bc4749",
    "#6a994e",
    "#7b2cbf",
    "#f4a261",
    "#457b9d",
    "#e76f51",
    "#8d99ae",
    "#2b9348",
    "#ffb703",
    "#577590",
    "#c77dff",
]


def _build_global_layout(graph: nx.Graph) -> dict[str, tuple[float, float]]:
    if graph.number_of_nodes() == 0:
        return {}

    if graph.number_of_nodes() == 1:
        return {next(iter(graph.nodes())): (0.0, 0.0)}

    layout_graph = graph.copy()
    for _, _, data in layout_graph.edges(data=True):
        weight = float(data.get("weight", 1) or 1)
        data["layout_weight"] = 0.2 + math.sqrt(weight) * 0.16

    positions = nx.spring_layout(
        layout_graph,
        seed=42,
        weight="layout_weight",
        k=62 / math.sqrt(graph.number_of_nodes()),
        iterations=800,
        scale=12.5,
    )
    positions = {
        node_id: (x * 1.8, y * 1.18)
        for node_id, (x, y) in positions.items()
    }
    return positions


def _resolve_node_overlaps(
    positions: dict[str, tuple[float, float]],
    node_radius_by_author: dict[str, float],
    iterations: int = 180,
    padding: float = 0.08,
) -> dict[str, tuple[float, float]]:
    if not positions:
        return positions

    adjusted = {
        author: [coords[0], coords[1]]
        for author, coords in positions.items()
    }
    authors = list(adjusted.keys())

    for _ in range(iterations):
        moved = False

        for index, author_a in enumerate(authors):
            x_a, y_a = adjusted[author_a]
            radius_a = node_radius_by_author.get(author_a, 0.2)

            for author_b in authors[index + 1:]:
                x_b, y_b = adjusted[author_b]
                radius_b = node_radius_by_author.get(author_b, 0.2)

                dx = x_b - x_a
                dy = y_b - y_a
                distance = math.hypot(dx, dy)
                minimum_distance = radius_a + radius_b + padding

                if distance >= minimum_distance:
                    continue

                moved = True
                if distance == 0:
                    dx = 0.01
                    dy = 0.0
                    distance = 0.01

                overlap = minimum_distance - distance
                push_x = (dx / distance) * overlap * 0.5
                push_y = (dy / distance) * overlap * 0.5

                adjusted[author_a][0] -= push_x
                adjusted[author_a][1] -= push_y
                adjusted[author_b][0] += push_x
                adjusted[author_b][1] += push_y

        if not moved:
            break

    return {
        author: (coords[0], coords[1])
        for author, coords in adjusted.items()
    }


def _resolve_component_overlaps(
    positions: dict[str, tuple[float, float]],
    components: list[set[str]],
    node_radius_by_author: dict[str, float],
    iterations: int = 120,
    padding: float = 0.6,
) -> dict[str, tuple[float, float]]:
    if not positions or len(components) < 2:
        return positions

    adjusted = {
        author: [coords[0], coords[1]]
        for author, coords in positions.items()
    }

    def component_bounds(component: set[str]) -> tuple[float, float, float, float]:
        min_x = min(adjusted[author][0] - node_radius_by_author.get(author, 0.2) for author in component)
        max_x = max(adjusted[author][0] + node_radius_by_author.get(author, 0.2) for author in component)
        min_y = min(adjusted[author][1] - node_radius_by_author.get(author, 0.2) for author in component)
        max_y = max(adjusted[author][1] + node_radius_by_author.get(author, 0.2) for author in component)
        return (min_x, max_x, min_y, max_y)

    for _ in range(iterations):
        moved = False

        for index, component_a in enumerate(components):
            min_x_a, max_x_a, min_y_a, max_y_a = component_bounds(component_a)
            center_x_a = (min_x_a + max_x_a) / 2
            center_y_a = (min_y_a + max_y_a) / 2

            for component_b in components[index + 1:]:
                min_x_b, max_x_b, min_y_b, max_y_b = component_bounds(component_b)
                center_x_b = (min_x_b + max_x_b) / 2
                center_y_b = (min_y_b + max_y_b) / 2

                overlap_x = min(max_x_a, max_x_b) - max(min_x_a, min_x_b)
                overlap_y = min(max_y_a, max_y_b) - max(min_y_a, min_y_b)

                if overlap_x <= -padding or overlap_y <= -padding:
                    continue

                moved = True
                push_x = overlap_x + padding if overlap_x > 0 else padding * 0.5
                push_y = overlap_y + padding if overlap_y > 0 else padding * 0.5

                dx = center_x_b - center_x_a
                dy = center_y_b - center_y_a

                if abs(dx) >= abs(dy):
                    direction_x = 1 if dx >= 0 else -1
                    shift_a = (-direction_x * push_x * 0.5, 0.0)
                    shift_b = (direction_x * push_x * 0.5, 0.0)
                else:
                    direction_y = 1 if dy >= 0 else -1
                    shift_a = (0.0, -direction_y * push_y * 0.5)
                    shift_b = (0.0, direction_y * push_y * 0.5)

                for author in component_a:
                    adjusted[author][0] += shift_a[0]
                    adjusted[author][1] += shift_a[1]
                for author in component_b:
                    adjusted[author][0] += shift_b[0]
                    adjusted[author][1] += shift_b[1]

        if not moved:
            break

    return {
        author: (coords[0], coords[1])
        for author, coords in adjusted.items()
    }


def _expand_component(
    positions: dict[str, tuple[float, float]],
    component: set[str],
    scale_x: float = 1.8,
    scale_y: float = 1.8,
) -> dict[str, tuple[float, float]]:
    if not positions or not component:
        return positions

    component_positions = [positions[author] for author in component if author in positions]
    if not component_positions:
        return positions

    centroid_x = sum(x for x, _ in component_positions) / len(component_positions)
    centroid_y = sum(y for _, y in component_positions) / len(component_positions)

    adjusted = dict(positions)
    for author in component:
        if author not in adjusted:
            continue
        x, y = adjusted[author]
        adjusted[author] = (
            centroid_x + (x - centroid_x) * scale_x,
            centroid_y + (y - centroid_y) * scale_y,
        )

    return adjusted


def plot_collaboration_network(
    network_data: dict,
    authorship_payload: dict,
    output_path: Path,
    snapshot_label: str,
) -> None:
    collaboration_network = authorship_payload.get("collaboration_network", {})
    raw_nodes = collaboration_network.get("nodes", []) or []
    raw_edges = collaboration_network.get("edges", []) or []
    if not raw_nodes or not raw_edges:
        raise ValueError("Collaboration network plot requires non-empty collaboration network data.")

    author_bip_map = build_author_bip_map(network_data)

    graph = nx.Graph()
    for node in raw_nodes:
        author = str(node.get("id"))
        authored_bips = author_bip_map.get(author, [])
        graph.add_node(
            author,
            collaborator_degree=int(node.get("degree", 0) or 0),
            bip_count=len(authored_bips),
        )

    for edge in raw_edges:
        source = str(edge.get("source"))
        target = str(edge.get("target"))
        weight = int(edge.get("weight", 1) or 1)
        graph.add_edge(source, target, weight=weight)

    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    largest_component = components[0] if components else set()
    cluster_by_author = {}
    for cluster_index, members in enumerate(components):
        for author in members:
            cluster_by_author[author] = cluster_index

    positions = _build_global_layout(graph)
    top_authors = sorted(
        graph.nodes(),
        key=lambda author: (-graph.nodes[author].get("bip_count", 0), author),
    )[:10]
    top_author_set = set(top_authors)

    authored_counts = [max(1, int(graph.nodes[author].get("bip_count", 0))) for author in graph.nodes()]
    node_sizes = [90 + (count**0.95) * 58 for count in authored_counts]
    node_radius_by_author = {}
    for author, node_size in zip(graph.nodes(), node_sizes):
        radius = 0.2 + math.sqrt(node_size) / 18
        if author in top_author_set:
            radius += min(2.0, 0.018 * len(author) + 0.35)
        else:
            radius += 0.08
        if author in largest_component:
            radius *= 1.16
        node_radius_by_author[author] = radius

    positions = _resolve_node_overlaps(positions, node_radius_by_author)
    positions = _resolve_component_overlaps(positions, components, node_radius_by_author)
    positions = _expand_component(positions, largest_component, scale_x=2.0, scale_y=1.9)
    positions = _resolve_node_overlaps(positions, node_radius_by_author, iterations=320, padding=0.3)
    positions = _resolve_component_overlaps(positions, components, node_radius_by_author, iterations=80, padding=0.7)
    edge_widths = [0.65 + float(data.get("weight", 1)) * 0.65 for _, _, data in graph.edges(data=True)]
    cluster_colors = {
        author: CLUSTER_COLORS[cluster_by_author.get(author, 0) % len(CLUSTER_COLORS)]
        for author in graph.nodes()
    }
    node_facecolors = [to_rgba(cluster_colors[author], alpha=0.82) for author in graph.nodes()]
    node_edgecolors = [cluster_colors[author] for author in graph.nodes()]
    edge_colors = [cluster_colors[source] for source, _, _ in graph.edges(data=True)]

    figure, axis = plt.subplots(figsize=(13, 7))
    nx.draw_networkx_edges(
        graph,
        positions,
        ax=axis,
        width=edge_widths,
        edge_color=edge_colors,
        alpha=0.42,
        arrows=True,
        arrowstyle="-",
        connectionstyle="arc3,rad=0.11",
    )
    nx.draw_networkx_nodes(
        graph,
        positions,
        ax=axis,
        node_size=node_sizes,
        node_color=node_facecolors,
        edgecolors=node_edgecolors,
        linewidths=1.1,
    )

    for author, (x, y) in positions.items():
        bip_count = int(graph.nodes[author].get("bip_count", 0))
        if author in top_author_set:
            label = f"{author} ({bip_count})"
            font_size = 9.5
        else:
            label = str(bip_count)
            font_size = 5.8

        axis.text(
            x,
            y,
            label,
            ha="center",
            va="center",
            fontsize=font_size,
            color="#111111",
            zorder=5,
        )

    axis.set_title(f"Collaboration Network ({snapshot_label})")
    axis.axis("off")
    figure.tight_layout()
    save_figure(figure, output_path)

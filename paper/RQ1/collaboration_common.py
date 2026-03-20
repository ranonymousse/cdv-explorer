import math
from collections import defaultdict, deque


def clean_author_name(author) -> str:
    return str(author or "").split("<")[0].strip()


def build_author_bip_map(network_data: dict) -> dict[str, list[str]]:
    author_bips = defaultdict(set)

    for proposal in network_data.get("nodes", []):
        bip_id = proposal.get("id")
        if bip_id is None:
            continue

        authors = proposal.get("author")
        if isinstance(authors, list):
            author_values = authors
        elif authors:
            author_values = [authors]
        else:
            author_values = []

        for author in author_values:
            cleaned = clean_author_name(author)
            if cleaned:
                author_bips[cleaned].add(str(bip_id))

    return {
        author: sorted(bips, key=lambda value: int(value))
        for author, bips in author_bips.items()
    }


def _compute_weighted_eigenvector(node_ids, adjacency, max_iterations=1000, tolerance=1e-6):
    author_ids = [str(node_id) for node_id in node_ids]
    node_count = len(author_ids)

    if node_count == 0:
        return {}

    initial_value = 1 / math.sqrt(node_count)
    values = {author_id: initial_value for author_id in author_ids}

    for _ in range(max_iterations):
        next_values = {author_id: 0.0 for author_id in author_ids}

        for author_id in author_ids:
            for neighbor in adjacency.get(author_id, []):
                next_values[author_id] += float(neighbor["weight"]) * values.get(neighbor["id"], 0.0)

        norm = math.sqrt(sum(value**2 for value in next_values.values()))
        if norm == 0:
            return {author_id: 0.0 for author_id in author_ids}

        delta = 0.0
        for author_id in author_ids:
            normalized = next_values[author_id] / norm
            delta += abs(normalized - values.get(author_id, 0.0))
            values[author_id] = normalized

        if delta < node_count * tolerance:
            break

    return values


def build_collaboration_metrics_rows(collaboration_network: dict, collaboration_centrality: list[dict]) -> list[dict]:
    raw_nodes = collaboration_network.get("nodes", []) or []
    raw_edges = collaboration_network.get("edges", []) or []
    node_ids = [str(node.get("id")) for node in raw_nodes if node.get("id")]

    adjacency = {node_id: [] for node_id in node_ids}
    weighted_degree_by_author = {node_id: 0 for node_id in node_ids}

    for edge in raw_edges:
        source = str(edge.get("source"))
        target = str(edge.get("target"))
        weight = int(edge.get("weight", 1) or 1)

        adjacency.setdefault(source, [])
        adjacency.setdefault(target, [])
        weighted_degree_by_author.setdefault(source, 0)
        weighted_degree_by_author.setdefault(target, 0)

        adjacency[source].append({"id": target, "weight": weight})
        adjacency[target].append({"id": source, "weight": weight})
        weighted_degree_by_author[source] += weight
        weighted_degree_by_author[target] += weight

    visited = set()
    components = []
    for node_id in node_ids:
        if node_id in visited:
            continue

        queue = deque([node_id])
        members = []
        visited.add(node_id)

        while queue:
            current = queue.popleft()
            members.append(current)

            for neighbor in adjacency.get(current, []):
                neighbor_id = neighbor["id"]
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                queue.append(neighbor_id)

        components.append(members)

    components.sort(key=len, reverse=True)

    cluster_meta_by_author = {}
    for index, members in enumerate(components, start=1):
        for author in members:
            cluster_meta_by_author[author] = {
                "clusterId": index,
                "clusterSize": len(members),
            }

    centrality_by_author = {
        str(entry.get("author")): entry
        for entry in (collaboration_centrality or [])
    }
    weighted_eigenvector_by_author = _compute_weighted_eigenvector(node_ids, adjacency)

    degree_rows = [
        {
            "author": str(node.get("id")),
            "clusterId": cluster_meta_by_author.get(str(node.get("id")), {}).get("clusterId"),
            "clusterSize": cluster_meta_by_author.get(str(node.get("id")), {}).get("clusterSize", 1),
            "rawDegree": int(node.get("degree", 0) or 0),
            "weightedDegree": int(weighted_degree_by_author.get(str(node.get("id")), 0)),
            "normalizedDegree": float(centrality_by_author.get(str(node.get("id")), {}).get("degree", 0) or 0),
        }
        for node in raw_nodes
    ]
    degree_rows.sort(key=lambda row: (-row["rawDegree"], row["author"]))

    eigenvector_by_author = {
        str(author): {
            "eigenvector": float(centrality_by_author.get(str(author), {}).get("eigenvector", 0) or 0),
            "weightedEigenvector": float(weighted_eigenvector_by_author.get(str(author), 0) or 0),
        }
        for author in node_ids
    }

    metrics_rows = []
    for row in degree_rows:
        eigenvector_row = eigenvector_by_author.get(row["author"], {})
        metrics_rows.append(
            {
                **row,
                "eigenvector": float(eigenvector_row.get("eigenvector", 0) or 0),
                "weightedEigenvector": float(eigenvector_row.get("weightedEigenvector", 0) or 0),
            }
        )

    return metrics_rows

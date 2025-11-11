"""Visualization helpers for follower graphs."""
from __future__ import annotations

from typing import Dict, Iterable

import matplotlib.pyplot as plt
import networkx as nx


def visualize_graph(edges: Dict[str, Iterable[str]], *, title: str = "Follower Graph") -> None:
    graph = nx.DiGraph()
    for follower, followed in edges.items():
        for target in followed:
            graph.add_edge(follower, target)

    plt.figure(figsize=(12, 12))
    pos = nx.spring_layout(graph, k=0.5, iterations=50)
    nx.draw_networkx_nodes(graph, pos, node_size=300, node_color="lightblue")
    nx.draw_networkx_edges(graph, pos, arrowstyle="->", arrowsize=10, edge_color="gray")
    nx.draw_networkx_labels(graph, pos, font_size=8)
    plt.title(title)
    plt.axis("off")
    plt.show()

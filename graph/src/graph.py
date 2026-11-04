import json
import networkx as nx

with open("../../docs/contracts/camera_graph.json") as f:
    graph_data = json.load(f)

edges = graph_data.get("edges", [])

G = nx.DiGraph()

for edge in edges:
    G.add_edge(
        edge["from_camera"],
        edge["to_camera"],
        **edge
    )

if __name__ == "__main__":
    print(G.nodes())
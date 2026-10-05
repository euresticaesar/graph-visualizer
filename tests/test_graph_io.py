from pathlib import Path

import networkx as nx
import pytest

from dijkstra_visualizer.io.graph_io import load_graph
from dijkstra_visualizer.io.layout_io import load_layout, save_layout


def write_graph(tmp_path, nodes="id\n1\n2\n3\n", edges="source,target,weight\n1,2,2.5\n"):
    nodes_path, edges_path = tmp_path / "nodes.csv", tmp_path / "edges.csv"
    nodes_path.write_text(nodes)
    edges_path.write_text(edges)
    return nodes_path, edges_path


def test_load_graph(tmp_path):
    graph = load_graph(*write_graph(tmp_path))
    assert set(graph) == {1, 2, 3}
    assert graph[2][1]["weight"] == 2.5
    assert graph.degree[3] == 0
    assert not graph.is_directed()


@pytest.mark.parametrize("nodes", ["id\n1\n1\n", "id\n-1\n", "id\na\n", "wrong\n1\n", "id\n"])
def test_invalid_nodes(tmp_path, nodes):
    with pytest.raises(ValueError):
        load_graph(*write_graph(tmp_path, nodes=nodes, edges="source,target,weight\n"))


@pytest.mark.parametrize(
    "edge",
    ["1,4,2", "1,2,0", "1,2,-2", "1,2,nan", "1,2,inf", "1,2,a", "1,1,2", "1,2", "1,2,3,4"],
)
def test_invalid_edges(tmp_path, edge):
    with pytest.raises(ValueError):
        load_graph(*write_graph(tmp_path, edges=f"source,target,weight\n{edge}\n"))


def test_duplicate_undirected_edge(tmp_path):
    with pytest.raises(ValueError, match="duplicada"):
        load_graph(*write_graph(tmp_path, edges="source,target,weight\n1,2,1\n2,1,2\n"))


def test_missing_graph_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_graph(tmp_path / "nodes.csv", tmp_path / "edges.csv")


def test_sample_graph():
    data_dir = Path(__file__).parent / "fixtures" / "sample"
    graph = load_graph(data_dir / "nodes.csv", data_dir / "edges.csv")
    assert len(graph) == 12
    assert nx.is_connected(graph)
    assert set(load_layout(data_dir / "layout.json", graph)) == set(graph)


def test_layout_round_trip_and_missing_positions(tmp_path):
    path = tmp_path / "layout.json"
    graph = nx.path_graph([1, 2, 3])
    positions = {1: (123.0, -42.5)}
    save_layout(path, positions)
    loaded = load_layout(path, graph)
    assert loaded[1] == positions[1]
    assert set(loaded) == set(graph)
    save_layout(path, loaded)
    assert load_layout(path, graph) == loaded


def test_missing_layout(tmp_path):
    assert set(load_layout(tmp_path / "absent.json", nx.path_graph([1, 2]))) == {1, 2}


@pytest.mark.parametrize(
    "content", ["{", "[]", '{"1": {"x": 1}}', '{"1": {"x": NaN, "y": 2}}', '{"a": {}}']
)
def test_invalid_layout(tmp_path, content):
    path = tmp_path / "layout.json"
    path.write_text(content)
    with pytest.raises(ValueError, match="layout.json"):
        load_layout(path, nx.path_graph([1, 2]))


def test_load_zero_and_large_ids_with_layout(tmp_path):
    large_id = 10**30
    graph = load_graph(
        *write_graph(
            tmp_path,
            nodes=f"id\n0\n{large_id}\n",
            edges=f"source,target,weight\n0,{large_id},3\n",
        )
    )
    assert set(graph) == {0, large_id}
    positions = {0: (10, 20), large_id: (50, 100)}
    path = tmp_path / "layout.json"
    save_layout(path, positions)
    assert load_layout(path, graph) == positions


@pytest.mark.parametrize("node", ["-1", "0.5", "1.0"])
def test_reject_invalid_csv_id(tmp_path, node):
    with pytest.raises(ValueError, match="ID"):
        load_graph(*write_graph(tmp_path, nodes=f"id\n{node}\n", edges="source,target,weight\n"))

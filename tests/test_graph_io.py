import networkx as nx
import pytest

from dijkstra_visualizer.io.graph_io import load_graph
from dijkstra_visualizer.io.layout_io import load_layout, save_layout
from dijkstra_visualizer.paths import DATA_DIR


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


@pytest.mark.parametrize("nodes", ["id\n1\n1\n", "id\n0\n", "id\na\n", "wrong\n1\n", "id\n"])
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
    graph = load_graph(DATA_DIR / "nodes.csv", DATA_DIR / "edges.csv")
    assert len(graph) == 12
    assert nx.is_connected(graph)
    assert set(load_layout(DATA_DIR / "layout.json", graph)) == set(graph)


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

import math

import networkx as nx
import pytest

from graph_visualizer.core.graph import convert_graph, normalize_id, validate_graph
from graph_visualizer.io.graph_io import load_graph, save_graph_data
from graph_visualizer.io.layout_io import load_layout


def test_csv_escape_and_legacy_migration(tmp_path):
    (tmp_path / "nodes.csv").write_text("id\n10\n2\n")
    (tmp_path / "edges.csv").write_text("source,target,weight,id\n10,2,0,7\n")
    (tmp_path / "layout.json").write_text('{"10":{"x":1,"y":2},"2":{"x":3,"y":4}}')
    g = load_graph(tmp_path / "nodes.csv", tmp_path / "edges.csv")
    assert sorted(g) == ["10", "2"]
    pos = load_layout(tmp_path / "layout.json", g)
    g = nx.relabel_nodes(g, {"2": 'Una, "ciudad"'})
    pos['Una, "ciudad"'] = pos.pop("2")
    save_graph_data(tmp_path, g, pos)
    loaded = load_graph(tmp_path / "nodes.csv", tmp_path / "edges.csv")
    assert nx.utils.graphs_equal(g, loaded)
    assert load_layout(tmp_path / "layout.json", loaded) == pos


def test_directed_conversion_and_weights(tmp_path):
    g = nx.MultiGraph()
    g.add_edge("A", "B", key=5, weight=0)
    d = convert_graph(g, True)
    assert set(d.edges(keys=True)) == {("A", "B", 5), ("B", "A", 5)}
    assert convert_graph(d, False).number_of_edges() == 2
    d["A"]["B"][5]["weight"] = -1
    with pytest.raises(ValueError):
        convert_graph(d, False)
    save_graph_data(tmp_path, d, {"A": (0, 0), "B": (1, 1)})
    assert load_graph(tmp_path / "nodes.csv", tmp_path / "edges.csv").is_directed()
    for weight in [math.nan, math.inf, -math.inf]:
        d["A"]["B"][5]["weight"] = weight
        with pytest.raises(ValueError):
            validate_graph(d)
    assert normalize_id("  A  ") == "A"
    assert normalize_id(123) == "123"
    with pytest.raises(ValueError):
        normalize_id(" ")


@pytest.mark.parametrize("metadata", ["[]", '{"version":true,"directed":false}', "{}"])
def test_invalid_working_graph_metadata_is_rejected(tmp_path, metadata):
    (tmp_path / "nodes.csv").write_text("id\nA\n")
    (tmp_path / "edges.csv").write_text("source,target,weight\n")
    (tmp_path / "graph.json").write_text(metadata)
    with pytest.raises(ValueError):
        load_graph(tmp_path / "nodes.csv", tmp_path / "edges.csv")

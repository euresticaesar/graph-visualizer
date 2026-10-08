"""Reproducible exports from a preset, without opening the workspace."""

from graph_visualizer.core.astar import astar_steps
from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.dijkstra import dijkstra_steps
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps
from graph_visualizer.export.image_exporter import export_graph
from graph_visualizer.io.presets import read_preset


def export_preset(args):
    preset = read_preset(args.export_preset)
    settings = preset.settings.copy()
    nodes = sorted(preset.graph)
    start = settings.setdefault("start", nodes[0])
    target = settings.setdefault("target", nodes[-1])
    algorithm = settings.setdefault("algorithm", "Dijkstra")
    detailed = settings.setdefault("detail", True)
    if args.detail != "preset":
        detailed = settings["detail"] = args.detail == "detailed"
    if algorithm == "Floyd-Warshall":
        states = floyd_warshall_steps(preset.graph, detailed=detailed)
    elif algorithm == "Bellman-Ford":
        states = bellman_ford_steps(
            preset.graph, start, early_stop=settings.get("early_stop", False)
        )
    elif algorithm == "A*":
        states = astar_steps(preset.graph, start, target, detailed=detailed)
    else:
        states = dijkstra_steps(preset.graph, start, target, detailed=detailed)
    return export_graph(
        preset.graph,
        preset.positions,
        states,
        start,
        target,
        0,
        args.kind,
        args.output_dir,
        output_format=args.format,
        execution_settings=settings,
        theme=args.theme,
        resolution=args.resolution,
        layout=args.layout,
        font_scale=args.font_scale,
        simple=args.simple,
        title=preset.name,
    )

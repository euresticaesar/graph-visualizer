from PySide6.QtCore import QThread, Signal

from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.dijkstra import dijkstra_steps
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps


class AlgorithmWorker(QThread):
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, graph, algorithm, start, target, detailed, early_stop, parent=None):
        super().__init__(parent)
        self.args = graph, algorithm, start, target, detailed, early_stop

    def run(self):
        graph, algorithm, start, target, detailed, early_stop = self.args
        try:
            if algorithm == "Floyd-Warshall":
                result = floyd_warshall_steps(graph, detailed=detailed)
            elif algorithm == "Bellman-Ford":
                result = bellman_ford_steps(graph, start, early_stop=early_stop)
            else:
                result = dijkstra_steps(graph, start, target, detailed=detailed)
            self.ready.emit(result)
        except Exception as error:
            self.failed.emit(str(error))

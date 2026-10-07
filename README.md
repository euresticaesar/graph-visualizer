# Graph Visualizer

Aplicación de escritorio en español para crear y editar grafos y explorar paso a paso **Dijkstra, Bellman-Ford y Floyd-Warshall**. Desarrollada con Python, PySide6 y NetworkX.

![Resultado de Dijkstra en un grafo de 30 nodos, con la ruta mínima resaltada](demo_screenshot.png)

## Empezar

Requiere **Python 3.12+**, **uv** y un entorno gráfico. Desde la raíz del repositorio:

```bash
uv sync
uv run graph-visualizer
```

En **Editar** crea o modifica el grafo; en **Recorrido** elige el algoritmo, origen y destino y pulsa **Iniciar**. Usa **Presets** para guardar ejemplos y **Exportar** para generar PNG.

## Documentación

| Tema | Guía |
| --- | --- |
| Instalación | [Ejecución, directorios y configuración](docs/instalacion.md) |
| Edición | [Nodos, conexiones, gestos e historial](docs/edicion.md) |
| Recorridos | [Navegación, reproducción y consulta de rutas](docs/recorrido.md) |
| Algoritmos | [Dijkstra](docs/algoritmos/dijkstra.md) · [Bellman-Ford](docs/algoritmos/bellman-ford.md) · [Floyd-Warshall](docs/algoritmos/floyd-warshall.md) |
| Presets | [Biblioteca y formato JSON](docs/presets.md) |
| Datos | [Persistencia y compatibilidad](docs/datos.md) |
| Exportaciones | [Estilos, cantidad de imágenes y límites](docs/exportaciones.md) |
| Arquitectura | [Organización del código y rendimiento](docs/arquitectura.md) |
| Desarrollo | [Pruebas, estilo y construcción del paquete](docs/desarrollo.md) |

# Arquitectura y rendimiento

[← Inicio](../README.md) · [Validación del proyecto](desarrollo.md)

## Organización del código

| Directorio | Responsabilidad |
| --- | --- |
| [`core/`](../src/graph_visualizer/core/) | Modelo de grafo, validaciones y algoritmos |
| [`ui/`](../src/graph_visualizer/ui/) | Ventana, edición, navegación, tablas y controles de exportación |
| [`io/`](../src/graph_visualizer/io/) | Lectura y escritura del trabajo, layouts y presets |
| [`export/`](../src/graph_visualizer/export/) | Render compartido para vista previa, PNG y PDF |
| [`examples/`](../src/graph_visualizer/examples/) | Presets de referencia incluidos en la aplicación |
| [`tests/`](../tests/) | Pruebas con grafos y directorios temporales |

## Estados y rendimiento

Los algoritmos están implementados en el proyecto. NetworkX almacena los grafos, calcula los saltos de la heurística de A* mediante BFS y sirve como referencia independiente en las pruebas.

`core/` contiene el modelo, validaciones y algoritmos, sin Qt, persistencia ni exportación. Los eventos son inmutables; resumen y detalle son vistas de una misma ejecución. Floyd-Warshall comparte las matrices entre comparaciones sin cambio y solo sustituye una fila cuando mejora, con árboles persistentes para los recorridos. La cantidad de eventos detallados sigue siendo cúbica: la aplicación es una herramienta didáctica para grafos de escritorio, no un motor para millones de nodos.

Los cálculos de más de 5 000 comparaciones estimadas se realizan en un hilo de trabajo. La exportación cede al bucle de Qt entre imágenes; durante estas operaciones se bloquean acciones incompatibles. Una imagen individual muy grande puede tardar en renderizarse; se espera a terminar la operación antes de cerrar la ventana.

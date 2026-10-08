# Arquitectura y rendimiento

[← Inicio](../README.md) · [Validación del proyecto](desarrollo.md)

## Organización del código

| Directorio | Responsabilidad |
| --- | --- |
| [`core/`](../src/graph_visualizer/core/) | Modelo de grafo, validaciones y algoritmos |
| [`ui/`](../src/graph_visualizer/ui/) | Ventana, edición, navegación, tablas y controles de exportación |
| [`io/`](../src/graph_visualizer/io/) | Lectura y escritura del trabajo, layouts y presets |
| [`export/`](../src/graph_visualizer/export/) | Composición de diapositivas completas y render compartido para vista previa, PNG, PDF y SVG |
| [`examples/`](../src/graph_visualizer/examples/) | Presets de referencia incluidos en la aplicación |
| [`tests/`](../tests/) | Pruebas con grafos y directorios temporales |

## Estados y rendimiento

Los algoritmos están implementados en el proyecto. NetworkX almacena los grafos, calcula los saltos de la heurística de A* mediante BFS y sirve como referencia independiente en las pruebas.

`core/` contiene el modelo, validaciones y algoritmos, sin Qt, persistencia ni exportación. Los eventos son inmutables; resumen y detalle son vistas de una misma ejecución. Floyd-Warshall comparte las matrices entre comparaciones sin cambio y solo sustituye una fila cuando mejora, con árboles persistentes para los recorridos. La cantidad de eventos detallados sigue siendo cúbica: la aplicación es una herramienta didáctica para grafos de escritorio, no un motor para millones de nodos.

Los cálculos de más de 5 000 comparaciones estimadas se realizan en un hilo de trabajo. Los cálculos aceptan interrupción cooperativa. La exportación cede al bucle de Qt entre páginas; durante estas operaciones se bloquean acciones incompatibles. El worker trabaja sobre una copia del grafo y entrega resultados asociados a su revisión. Una página individual muy grande puede tardar en renderizarse; se espera a terminar la operación antes de cerrar la ventana.

`export/slide_renderer.py` mide las tablas, redistribuye las listas en columnas y ajusta su escala junto con el espacio del grafo. Cada estado tiene un único plan de diapositiva 16:9: las matrices permanecen completas y conservan todos sus índices. Los textos se ajustan dentro de sus rectángulos, manteniendo el contenido íntegro. `ui/themes.py` centraliza colores semánticos; `io/preferences.py` valida y persiste personalización separada del grafo. La exportación prepara una carpeta temporal y la renombra solo al completar imágenes/documentos y metadatos.

`SlideRenderer` es el renderer único de PNG, PDF, SVG, vista previa, portapapeles y `ui/presentation_view.py`. Sus planes incluyen composición adaptativa o manual, proporción del grafo y foco opcional, manteniendo tablas completas. El diagnóstico de legibilidad usa las mismas fuentes ajustadas y transformaciones del render. `image_exporter.py` conserva la orquestación de formatos, manifiestos y escrituras; sus antiguos helpers internos `measure_state`, `table_data`, `draw_table`, `legend` e `ImageLayout` se retiraron en 0.3.0 y los consumidores se migraron al compositor. No hay una segunda implementación de dimensiones o tablas exportadas.

El visor de presentación mantiene su propia navegación y temporizador sobre los estados inmutables y comparte las marcas por evento con la ventana. `ui/accessibility.py` centraliza los anuncios nativos. El tamaño de cada QLabel de vista previa coincide con el pixmap completo; el layout se recalcula al cambiar zoom. El escritorio activa layouts y refresca splitters después de cambiar densidad, respeta mínimos de los paneles y protege `refit_workspace` frente a reentrada.

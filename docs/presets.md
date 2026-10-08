# Presets y formato JSON

[← Inicio](../README.md) · [Persistencia del trabajo](datos.md)

La pestaña **Presets** agrupa la biblioteca, el guardado del trabajo, la organización y los archivos JSON. Permite **guardar como nuevo, cargar, actualizar explícitamente, renombrar, duplicar, eliminar, importar y exportar JSON**. Exportar JSON guarda el trabajo actual; importar valida y crea una copia personal. Los ejemplos incluidos son de solo lectura: duplícalos para personalizarlos.

Se incluyen los ejemplos de 12 y 30 nodos y los grafos de las referencias de Bellman-Ford (cinco vértices dirigidos, origen z) y Floyd-Warshall (ocho vértices no dirigidos).

El autoguardado del trabajo es independiente del preset. Editar un preset cargado **no** modifica su archivo: usa **Actualizar preset**. Al cargar otro con cambios pendientes puedes guardar y continuar, continuar sin guardar en preset o cancelar. El guardado actualiza el preset personal asociado; si no existe uno, solicita un nombre nuevo. Sin cambios no hay aviso. La carga se valida antes de sustituir el trabajo; los fallos conservan el grafo anterior. Cargar reinicia la ejecución y es deshacible, incluidos sus ajustes de algoritmo, detalle y parada temprana.

Los presets personales están en `data/presets/` (excluido de Git); los ejemplos versionados están en [`src/graph_visualizer/examples/`](../src/graph_visualizer/examples/). Se guardan nombre, tipo, nodos, conexiones con clave/peso, posiciones y opciones de algoritmo/origen/destino/detalle y parada temprana de Bellman-Ford (`early_stop`). No se guardan estados calculados, temporizadores ni historial.

## Formato JSON v1

```json
{
  "version": 1,
  "name": "Ejemplo dirigido",
  "directed": true,
  "nodes": ["A", "B"],
  "edges": [{"source": "A", "target": "B", "id": 0, "weight": -2}],
  "positions": {"A": [100, 100], "B": [350, 100]},
  "settings": {"algorithm": "Bellman-Ford", "start": "A", "target": "B", "detail": true, "early_stop": false}
}
```

Los archivos importados deben tener posiciones finitas para todos sus nodos. Se rechazan versiones desconocidas, duplicados, extremos inexistentes y pesos inválidos. Las escrituras se preparan en archivos temporales y se reemplazan atómicamente.

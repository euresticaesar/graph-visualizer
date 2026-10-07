# Graph Visualizer

Aplicación de escritorio en español para aprender **Dijkstra, Bellman-Ford y Floyd-Warshall** sobre grafos editables. Python 3.12+, uv, PySide6 y NetworkX. Los algoritmos están implementados en el proyecto; NetworkX almacena los grafos y sirve como referencia independiente en pruebas.

## Instalación y ejecución

Desde esta carpeta, sin necesidad de renombrarla:

```bash
uv sync
uv run graph-visualizer
```

También puedes usar `uv run python -m graph_visualizer`. El proyecto y comando se llaman `graph-visualizer`; el paquete importable es `graph_visualizer`. No hay alias del nombre anterior.

Para trabajar con datos aislados:

```bash
uv run graph-visualizer --data-dir /tmp/mi-grafo --output-dir /tmp/mis-imagenes
```

El primer arranque de un directorio vacío crea el ejemplo de 12 nodos. Desde un checkout se conserva `data/` como directorio predeterminado de trabajo y `output/` para PNG. Una instalación de la distribución usa `$XDG_DATA_HOME/graph-visualizer` o `~/.local/share/graph-visualizer`. Las variables `GRAPH_VISUALIZER_DATA_DIR` y `GRAPH_VISUALIZER_OUTPUT_DIR` también permiten elegir las rutas, independientemente del directorio desde el que se lance el comando.

PySide6 necesita un entorno gráfico. Para pruebas sin pantalla se utiliza `QT_QPA_PLATFORM=offscreen`.

## Edición del grafo

En **Editar grafo** puedes agregar, renombrar y eliminar nodos, cambiar pesos y crear conexiones paralelas. Cada grafo es dirigido o no dirigido; no se mezclan ambos tipos.

- **IDs:** strings no vacíos; se eliminan espacios exteriores y se distinguen mayúsculas (`A` y `a` son nodos diferentes). Letras, nombres, comas, comillas y números escritos como texto son válidos. No existe un atributo numérico adicional de “valor”. Se rechazan duplicados después de normalizar espacios.
- **Orden:** lexicográfico por ID; `"10"` precede a `"2"`. Se usa en selectores, matrices y desempates.
- **Pesos:** números finitos, incluido cero. Los negativos solo se permiten en grafos dirigidos. Se rechazan NaN, infinitos y conexiones de un nodo consigo mismo.
- **Identidad:** una conexión se identifica por sus extremos y su clave entera no negativa. En un grafo dirigido `(u,v,id)` es distinto de `(v,u,id)`. Las claves pueden repetirse en pares diferentes. Los dibujos muestran peso y `#id`; las curvas separan paralelas y sentidos opuestos.
- **Cambio de tipo:** no dirigido → dirigido crea dos arcos por conexión con la misma clave. Dirigido → no dirigido conserva cada arco como una conexión; si las claves del par chocan, asigna la siguiente clave libre. Rechaza la conversión si hay pesos negativos. Nunca fusiona conexiones silenciosamente. Puedes deshacer la conversión.

Gestos: doble clic en el fondo agrega un nodo; arrastrar su centro lo mueve; arrastrar el borde hasta otro nodo crea una conexión; clic en una conexión o su peso permite editarla. La rueda cambia el zoom, arrastrar el fondo desplaza la vista y **Ajustar vista** / `Ctrl+0` encuadra el grafo.

Los cambios se guardan automáticamente. **↶ / ↷**, `Ctrl+Z` y `Ctrl+Y` conservan hasta 100 acciones, incluidos movimientos, cambios de tipo y cargas de presets. Durante la ejecución se bloquea la edición; **Volver a editar** detiene la reproducción y conserva el historial.

## Ejecución y navegación

Elige el algoritmo y sus opciones, luego **Iniciar**. La explicación, la fase, la iteración y la posición aparecen encima del grafo. Puedes avanzar, retroceder, ir al inicio/final, escribir un número de paso o saltar a una fase/iteración. **Reproducir / Pausar** utiliza un solo temporizador; la velocidad se expresa en milisegundos por paso.

La reproducción se detiene al llegar al final, cambiar de algoritmo o detalle, cargar un preset, abrir otra pestaña, exportar o volver a editar. Cambiar de detalle navega sobre los mismos eventos ya calculados y elige una posición equivalente, sin recalcular ni volver obligatoriamente al inicio.

Los paneles de grafo y tablas se pueden redimensionar arrastrando su separador. Las tablas y matrices tienen desplazamiento y encabezados. Con grafos grandes, usa zoom, desplazamiento y el separador para revisar los detalles.

### Dijkstra

Calcula la ruta entre el origen y el destino y termina al seleccionar el destino. **Por comparación** está activado inicialmente: hay inicialización, selección del nodo y una comparación por conexión hacia un vecino no fijado, incluso si no mejora. Las conexiones paralelas se comparan individualmente. Desmarca la opción para ver el resumen por nodo.

Las comparaciones muestran distancia anterior, candidata, respuesta y distancia/predecesor resultantes. Solo una mejora estricta cambia distancia y recorrido. Los empates conservan la primera ruta encontrada en el orden determinista. El verde identifica nodos fijados; el naranja identifica la conexión comparada; el turquesa, la ruta final.

Si hay **cualquier peso negativo**, Dijkstra se bloquea y recomienda los otros algoritmos, aunque la conexión negativa no sea alcanzable desde el origen.

### Bellman-Ford

Calcula desde el origen hacia **todos** los nodos. El destino solo consulta una ruta; puedes cambiarlo durante la ejecución.

Se muestran el grafo, la lista de arcos ordenada por origen/destino/clave y la tabla **V / d / π** (nodo, distancia, predecesor). Cada arco produce un paso, también si su origen está a ∞ o no mejora. Las mejoras son inmediatas y las usa el arco siguiente de esa misma pasada. Los grafos no dirigidos generan dos arcos por conexión, conservando su identidad.

Por defecto completa las `|V|−1` pasadas. Puedes activar **Terminar tras una pasada sin cambios** antes de iniciar. Después aparece una fase separada de verificación, arco por arco. Esta pasada de sondeo permite encontrar un ciclo concreto.

Si hay un ciclo negativo alcanzable, se resalta en rojo y se marcan con **−∞** sus nodos y todos los alcanzables desde él. No tienen costo mínimo finito. Los demás resultados siguen siendo válidos. Un ciclo inaccesible desde el origen no invalida la ejecución. No se presentan cadenas de predecesores cíclicas como rutas mínimas.

### Floyd-Warshall

Calcula **todos los pares**, con independencia de los selectores de origen/destino. Estos solo consultan y resaltan una ruta del estado actual.

Inicialmente se muestra una **iteración completa de k** por paso. Activa **Por comparación** para ver todos los triples `(i,j,k)`, incluidos los que no mejoran o contienen ∞. Cada comparación y su actualización constituyen un único paso: distancia anterior, `D[i,k]`, `D[k,j]`, suma candidata, mejora/sin cambio y resultado.

Las dos matrices aparecen simultáneamente:

- **Distancias:** diagonal inicial 0; ∞ si no existe ruta. Entre conexiones paralelas se elige la de menor peso; los empates conservan la primera clave.
- **Recorridos:** inicialmente muestra el destino en rutas directas, el nodo propio en la diagonal y **—** si no hay ruta. Una mejora a través de k registra **k como intermedio**. No es una matriz de siguiente salto ni de predecesores. Internamente, composiciones inmutables de recorridos conservan las conexiones exactas y permiten reconstruir la ruta completa sin depender de entradas que cambien después.

Fila, columna y encabezados de **k**: verde. Mejoras acumuladas durante esa iteración: amarillo. Si coinciden, fondo amarillo y borde verde. La comparación actual tiene un borde violeta. Al comenzar otro k se limpian las mejoras; al retroceder se recuperan los colores del estado elegido.

La fase final identifica todos los pares que pueden atravesar un ciclo negativo, los marca **−∞** y retira su recorrido. Los pares no afectados siguen consultables. La reconstrucción tiene protecciones contra ciclos y recorridos inválidos.

## Presets

La pestaña **Presets** permite **guardar como nuevo, cargar, actualizar explícitamente, renombrar, duplicar, eliminar, importar y exportar JSON**. Exportar JSON guarda el trabajo actual; importar valida y crea una copia personal. Los ejemplos incluidos son de solo lectura: duplícalos para personalizarlos.

Se incluyen los ejemplos de 12 y 30 nodos y los grafos de las referencias de Bellman-Ford (cinco vértices dirigidos, origen z) y Floyd-Warshall (ocho vértices no dirigidos).

El autoguardado del trabajo es independiente del preset. Editar un preset cargado **no** modifica su archivo: usa **Actualizar preset**. Al cargar otro con cambios pendientes puedes guardar y continuar, continuar sin guardar en preset o cancelar. El guardado actualiza el preset personal asociado; si no existe uno, solicita un nombre nuevo. Sin cambios no hay aviso. La carga se valida antes de sustituir el trabajo; los fallos conservan el grafo anterior. Cargar reinicia la ejecución y es deshacible.

Los presets personales están en `data/presets/` (excluido de Git); los ejemplos versionados están en `src/graph_visualizer/examples/`. Se guardan nombre, tipo, nodos, conexiones con clave/peso, posiciones y opciones de algoritmo/origen/destino/detalle. No se guardan estados calculados, temporizadores ni historial.

### Formato JSON v1

```json
{
  "version": 1,
  "name": "Ejemplo dirigido",
  "directed": true,
  "nodes": ["A", "B"],
  "edges": [{"source": "A", "target": "B", "id": 0, "weight": -2}],
  "positions": {"A": [100, 100], "B": [350, 100]},
  "settings": {"algorithm": "Bellman-Ford", "start": "A", "target": "B", "detail": true}
}
```

Los archivos importados deben tener posiciones finitas para todos sus nodos. Se rechazan versiones desconocidas, duplicados, extremos inexistentes y pesos inválidos. Las escrituras se preparan en archivos temporales y se reemplazan atómicamente.

## Persistencia y compatibilidad

El trabajo sigue utilizando archivos UTF-8:

| Archivo | Contenido |
| --- | --- |
| `nodes.csv` | Encabezado `id`, una fila por nodo |
| `edges.csv` | `source,target,weight,id`; lectores aceptan también el formato antiguo sin `id` |
| `layout.json` | Objeto `{ "ID": { "x": número, "y": número } }` |
| `graph.json` | `{ "version": 1, "directed": false }` |

Sin `graph.json`, el grafo se interpreta como **no dirigido**. Los IDs numéricos antiguos se leen como strings sin pérdida; pesos, claves y coordenadas se conservan. No hace falta convertir manualmente los archivos: al editar se escribe el formato actual, con metadatos de tipo y escape CSV estándar para comas/comillas/saltos de línea. Las distancias se calculan con la precisión de los números Python; el formato visual usa hasta seis decimales sin ceros finales y no interviene en comparaciones. Se detecta desbordamiento de sumas finitas y se informa como error.

Las escrituras del conjunto de archivos preparan copias anteriores y restauran los originales si falla un reemplazo. Si también falla la recuperación, el error indica dónde quedó la copia anterior. No es una base de datos transaccional frente a una interrupción abrupta del sistema; para respaldos duraderos exporta un preset.

## Exportaciones PNG

Exporta el **paso actual**, **todos los pasos separados**, **imágenes conjuntas** o el **resultado final**. Por defecto se usa el detalle visible; para Dijkstra y Floyd-Warshall puedes elegir resumen o subpasos sin modificar la navegación en pantalla.

**Didáctico:** algoritmo, fase, numeración, grafo, explicación y leyenda. Bellman-Ford incluye lista completa de arcos y tabla; Floyd-Warshall incluye ambas matrices. Los resultados finales incluyen la ruta consultada y su costo cuando son válidos, o la explicación de ausencia de ruta/ciclo negativo.

**Simple:** únicamente el grafo, con IDs, pesos, claves, flechas y resaltados. No incluye títulos, etiquetas de distancia/predecesor, leyendas, tablas ni matrices. En Floyd-Warshall conserva la ruta consultada cuando existe; para compartir las matrices usa el estilo didáctico.

Cada operación crea una carpeta con fecha y hora. Las composiciones conservan el tamaño legible de sus imágenes, sin reducirlas a miniaturas: se dividen en archivos `conjunta_0001.png`, etc., con hasta cuatro pasos por página y un presupuesto de 24 megapíxeles/12 000 píxeles de alto. Una imagen individual más grande ocupa su propia página. El máximo individual es 100 megapíxeles; si un layout extremadamente extendido lo excede, se solicita reducirlo. El aviso de exportación permite abrir su carpeta.

## Arquitectura, rendimiento y pruebas

`core/` contiene el modelo, validaciones y algoritmos, sin Qt, persistencia ni exportación. Los eventos son inmutables; resumen y detalle son vistas de una misma ejecución. Floyd-Warshall comparte las matrices entre comparaciones sin cambio y solo sustituye una fila cuando mejora, con árboles persistentes para los recorridos. La cantidad de eventos detallados sigue siendo cúbica: la aplicación es una herramienta didáctica para grafos de escritorio, no un motor para millones de nodos.

Los cálculos de más de 5 000 comparaciones estimadas se realizan en un hilo de trabajo. La exportación cede al bucle de Qt entre imágenes; durante estas operaciones se bloquean acciones incompatibles. Una imagen individual muy grande puede tardar en renderizarse; se espera a terminar la operación antes de cerrar la ventana.

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

Las pruebas usan directorios temporales y cubren algoritmos frente a NetworkX, comparaciones, conexiones exactas, empates, estados inmutables, matrices, ciclos negativos, navegación, reproducción, edición, migración, recuperación de escrituras, presets, PNG y división de composiciones. La revisión visual debe complementar estas pruebas, especialmente al cambiar estilos o distribuciones de paneles.

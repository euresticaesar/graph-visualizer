# Visualizador de Dijkstra

Aplicación de escritorio para explorar el algoritmo de Dijkstra paso a paso sobre
un grafo no dirigido con pesos positivos. Permite editar el grafo, revisar las
distancias calculadas y exportar imágenes del recorrido.

Usa **Python 3.12+, uv, PySide6 / Qt 6 y NetworkX**. Las pruebas se ejecutan con
pytest; Ruff revisa el código y aplica el formato.

## Ejecución

Con uv instalado, ejecuta desde la carpeta del proyecto:

```sh
uv sync
uv run dijkstra-visualizer
```

También puedes usar `uv run python -m dijkstra_visualizer`. Para iniciar desde
otra carpeta:

```sh
uv run --project /ruta/al/dijkstra-visualizer dijkstra-visualizer
```

La aplicación necesita un entorno gráfico. Las rutas de datos y exportaciones
se resuelven desde el código del proyecto, no desde la carpeta de la terminal.
Conserva `data/` junto al proyecto; todavía no hay un instalador independiente.

## Uso

El selector **Recorrido / Editar grafo** tiene forma de píldora dividida. Los
controles están en un panel redondeado; no hay barra de menús.

1. En **MODO EDICIÓN**, arrastra los nodos para acomodarlos. Las conexiones y sus
   pesos se mueven al mismo tiempo. Las posiciones se guardan al soltar el mouse.
2. En **Recorrido**, selecciona **Nodo de inicio** y **Nodo de destino** y pulsa
   **Iniciar Dijkstra**. Usa **Siguiente** y **Anterior** para revisar los pasos.
3. **Volver a editar** termina la visualización y conserva el grafo, las posiciones
   y el historial de edición.
4. Los botones debajo del grafo exportan imágenes. **Abrir carpeta** muestra las
   exportaciones y **Salir** cierra la aplicación.

### Edición del grafo

En **Editar grafo** puedes:

- Escribir un **ID nuevo** y pulsar **Agregar nodo**.
- Seleccionar un nodo y pulsar **Cambiar ID** para renombrarlo. Enter en **ID nuevo**
  realiza esta misma acción; no agrega otro nodo.
- Usar **Eliminar nodo seleccionado** para borrar un nodo y sus conexiones.
  El grafo debe conservar al menos un nodo.
- Elegir **Desde**, **Hasta** y un **Peso**, y pulsar **Guardar conexión** para
  crear una conexión o modificar su peso. Enter en **Peso** también la guarda.
- Pulsar **Eliminar conexión** para quitar la conexión seleccionada.

Los ID son enteros desde **0**, sin un máximo definido por la aplicación.
No se permiten ID negativos, decimales ni duplicados. Los pesos deben ser números
positivos y finitos; pueden tener decimales, por ejemplo `2.5`.

Al hacer clic en un nodo del grafo, también se selecciona en el editor. Los cambios
se guardan automáticamente. Durante el recorrido se bloquea la edición.

### Deshacer, rehacer y navegación

Las flechas **↶ / ↷**, junto a **Ajustar vista**, permiten deshacer y rehacer
movimientos, cambios de ID, altas y bajas de nodos, cambios en conexiones y
selecciones de inicio o destino. Cada arrastre cuenta como una sola acción.

El historial conserva hasta 100 acciones durante la sesión. Una edición nueva
después de deshacer descarta las acciones pendientes de rehacer. Al deshacer o
rehacer un cambio del grafo también se actualizan los archivos guardados.

| Atajo o gesto | Acción |
| --- | --- |
| `Ctrl+Z` | Deshacer |
| `Ctrl+Y` o `Ctrl+Shift+Z` | Rehacer |
| `Ctrl+0` | Ajustar el grafo a la vista |
| `Ctrl+Q` | Salir |
| Arrastrar el fondo | Desplazar la vista |
| Rueda del mouse | Acercar o alejar |
| Enter en **ID nuevo** | Cambiar el ID del nodo seleccionado |
| Enter en **Peso** | Guardar la conexión |

### Etiquetas y colores

Cada nodo muestra `[distancia, predecesor]`. Se usa `∞` para una distancia todavía
no conocida y `null` cuando no hay predecesor.

| Apariencia | Significado |
| --- | --- |
| Gris | Nodo sin alcanzar |
| Amarillo | Distancia tentativa |
| Verde | Nodo visitado; su distancia ya es definitiva |
| Verde oscuro y aro discontinuo | Nodo actual |
| Borde rojo | Nodo de destino |
| Conexiones turquesa | Ruta mínima final |
| Etiqueta en negritas | Distancia mejorada en ese paso |

El inicio y el destino también tienen texto de identificación. La leyenda se
organiza en dos columnas.

## Funcionamiento de Dijkstra

El proyecto implementa Dijkstra en `core/dijkstra.py`. **No utiliza las funciones
de rutas mínimas de NetworkX para ejecutar el algoritmo**. NetworkX representa el
grafo y se usa como referencia independiente en las pruebas.

El paso 0 asigna distancia 0 al inicio e infinito al resto. Cada paso siguiente
selecciona el nodo con menor distancia tentativa, lo marca como visitado y revisa
si puede mejorar las distancias de sus vecinos no visitados. En caso de empate,
se elige el ID menor.

El recorrido termina cuando el destino queda visitado, antes de revisar sus
vecinos, o cuando ya no quedan nodos alcanzables. Por eso, algunas distancias de
nodos no visitados pueden seguir siendo tentativas al finalizar.

Los estados son inmutables: avanzar o retroceder no vuelve a ejecutar Dijkstra ni
modifica pasos anteriores. La ruta final se reconstruye con los predecesores.
Si no existe una ruta, se indica en pantalla. El inicio y el destino pueden ser
el mismo nodo; en ese caso, la distancia es 0.

## Archivos de datos

| Archivo | Contenido | Formato |
| --- | --- | --- |
| `data/nodes.csv` | Nodos, incluidos los aislados | Encabezado `id`; un entero desde 0 por fila |
| `data/edges.csv` | Conexiones no dirigidas y pesos | Encabezado `source,target,weight` |
| `data/layout.json` | Solo posiciones visuales | ID como texto y coordenadas `x`, `y` |

Ejemplo de `nodes.csv`:

```csv
id
0
1
2
```

Ejemplo de `edges.csv`:

```csv
source,target,weight
0,1,7
1,2,2.5
```

Ejemplo de una posición en `layout.json`:

```json
{
  "0": {"x": 220.0, "y": 160.0}
}
```

Una conexión se escribe una sola vez: `0,1,7` conecta ambos nodos en las dos
direcciones. Se rechazan duplicados, conexiones de un nodo consigo mismo,
referencias a nodos inexistentes, registros mal formados y pesos no válidos.

Si falta una posición, se genera una sin mover los nodos que ya tienen coordenadas.
Un JSON dañado se reporta como error. El guardado prepara archivos temporales antes
de reemplazar los originales. Si falla, intenta recuperar los archivos anteriores;
si también falla esa recuperación, conserva las copias e indica sus rutas.

Para editar los CSV manualmente, cierra la aplicación y vuelve a abrirla al
terminar. El inicio, el destino, los colores y los estados de Dijkstra no se
persisten en estos archivos. El historial de edición tampoco se conserva al salir.

## Exportaciones

Después de iniciar Dijkstra, están disponibles estas opciones:

| Botón | Resultado |
| --- | --- |
| **Paso actual** | `current_step_05.png`, por ejemplo |
| **Pasos separados** | `steps/step_00.png`, `step_01.png`, etc. |
| **Imagen conjunta** | `all_steps.png`, con hasta tres columnas |
| **Ruta final** | `final_path.png`, aunque estés viendo un paso anterior |

Cada exportación crea una carpeta con fecha, hora y microsegundos dentro de
`output/`. No se solicita un nombre ni una ubicación. Al terminar aparece un aviso
persistente con la cantidad de imágenes, la ruta y un botón para abrir esa carpeta.
También se muestra una confirmación en la barra de estado. Puedes cerrar el aviso
con **×**. El botón lateral **Abrir carpeta** abre la carpeta general `output/`.

Las imágenes se generan desde una escena de Qt independiente, con las mismas
posiciones y etiquetas. Incluyen información del paso, pero no botones ni otros
controles de la ventana. Exportar no cambia el paso que estás viendo.

Las imágenes individuales tienen 1600 × 1100 píxeles; la imagen conjunta usa celdas
de 1200 × 860. Su resolución no depende del tamaño de la ventana. Si una imagen
conjunta sería demasiado grande, se solicita exportar los pasos por separado.
La exportación puede pausar brevemente la interfaz en grafos grandes. Git ignora
los archivos generados en `output/`.

## Estructura del proyecto

```text
src/dijkstra_visualizer/
├── core/       # Validación, estados inmutables y Dijkstra
├── io/         # Lectura y guardado del grafo y las posiciones
├── ui/         # Ventana, editor, escena y elementos gráficos
├── export/     # Generación de imágenes individuales y conjuntas
└── paths.py    # Rutas de datos y exportaciones
data/           # Grafo y posiciones guardadas
tests/          # Pruebas y datos de ejemplo independientes
output/         # Imágenes generadas; no se incluyen en Git
```

El núcleo no depende de Qt. La interfaz recibe los estados calculados y la capa
de archivos no contiene lógica del algoritmo. El grafo se dibuja con
`QGraphicsScene` y `QGraphicsView`.

## Pruebas y revisión del código

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Para aplicar el formato: `uv run ruff format .`.

Las pruebas cubren el algoritmo, la validación de datos, los ID desde 0 y mayores
de 64 bits, la edición, Enter en los campos, deshacer y rehacer, errores de guardado,
arrastres y exportaciones. Las pruebas de interacción usan un grafo fijo en
`tests/fixtures/sample/` y carpetas temporales; no alteran tu grafo. Las pruebas de
Qt se ejecutan sin mostrar ventanas mediante la plataforma `offscreen`.

## Mensajes del escritorio en Linux

El mensaje `This plugin supports grabbing the mouse only for popup windows` se
origina en la [integración de Qt con Wayland](https://github.com/qt/qtbase/blob/dev/src/plugins/platforms/wayland/qwaylandwindow.cpp).
Si afecta la interacción y tienes XWayland instalado, puedes iniciar así:

```sh
QT_QPA_PLATFORM=xcb uv run dijkstra-visualizer
```

Esto selecciona el backend X11 de Qt para esa ejecución, sin cambiar la
configuración del escritorio. Consulta la [documentación de plataformas de Qt](https://doc.qt.io/qt-6/qguiapplication.html#platformName-prop).

El mensaje `WARNING: Glycin running without sandbox` proviene de la biblioteca de
[carga de imágenes Glycin](https://github.com/GNOME/glycin#sandboxing-and-inner-workings).
La aplicación no la usa directamente; el tema del escritorio o el explorador de
archivos podrían generarlo. No se reprodujo durante las pruebas de inicio y
exportación. No se desactivan protecciones del sistema ni se ocultan advertencias.

Posibles mejoras futuras: reproducción automática y un instalador de escritorio.

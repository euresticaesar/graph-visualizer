# Visualizador de Dijkstra

Aplicación de escritorio para editar grafos y revisar Dijkstra paso a paso.
Usa Python 3.12+, uv, PySide6 y NetworkX. Usa pytest para las pruebas y Ruff para
revisar el código.

## Instalación

Instala uv. Abre una terminal en la carpeta del proyecto. Ejecuta:

```sh
uv sync
uv run dijkstra-visualizer
```

Se requiere un escritorio gráfico. Para iniciar desde otra carpeta, usa:

```sh
uv run --project /ruta/al/dijkstra-visualizer dijkstra-visualizer
```

## Uso

1. Abre **Editar grafo**. Agrega nodos o selecciona un nodo para cambiar su ID.
2. Selecciona dos nodos y un peso. Pulsa **Guardar conexión**.
3. Arrastra los nodos para cambiar sus posiciones. Los cambios se guardan al soltar.
4. Abre **Recorrido**. Selecciona el inicio y el destino. Pulsa **Iniciar Dijkstra**.
5. Usa **Anterior** y **Siguiente** para revisar los pasos.
6. Pulsa **Volver a editar** para modificar el grafo.

Los ID deben ser enteros desde 0. No se admiten ID repetidos, negativos ni decimales.
La aplicación no fija un ID máximo. Los pesos deben ser positivos y finitos.
Usa un punto para los decimales: `2.5`.

Eliminar un nodo también elimina sus conexiones. Debe quedar al menos un nodo.
La edición se guarda de forma automática. Deshacer y rehacer también actualizan
los archivos. El historial conserva hasta 100 acciones por sesión.

| Control | Acción |
| --- | --- |
| Enter en **ID nuevo** | Cambiar el ID seleccionado |
| Enter en **Peso** | Guardar la conexión |
| **↶ / ↷** o `Ctrl+Z` / `Ctrl+Y` | Deshacer / rehacer |
| `Ctrl+0` | Ajustar la vista |
| Arrastrar el fondo / rueda del mouse | Desplazar / acercar o alejar |
| **Salir** o `Ctrl+Q` | Cerrar la aplicación |

## Algoritmo

El proyecto implementa Dijkstra. NetworkX almacena el grafo; no calcula las rutas
de la aplicación.

1. Asigna distancia 0 al inicio e infinito a los demás nodos.
2. Selecciona el nodo no visitado con la menor distancia. Resuelve empates por ID.
3. Marca el nodo como visitado. Si es el destino, termina.
4. Actualiza las distancias y los predecesores de sus vecinos no visitados.
5. Repite hasta visitar el destino o agotar los nodos alcanzables.

Cada paso se guarda como un estado inmutable. Avanzar o retroceder no recalcula
el recorrido. La ruta final se obtiene de los predecesores. Si no hay ruta, la
interfaz lo indica.

Cada etiqueta muestra `[distancia, predecesor]`. `∞` indica distancia desconocida;
`null` indica ausencia de predecesor. Gris significa sin alcanzar; amarillo,
tentativo; verde, visitado. El nodo actual es verde oscuro. El destino tiene borde
rojo. La ruta final se marca en turquesa.

## Datos

| Archivo | Contenido |
| --- | --- |
| `data/nodes.csv` | Nodos. Encabezado: `id`. Un ID por fila. |
| `data/edges.csv` | Conexiones. Encabezado: `source,target,weight`. Ejemplo: `0,1,2.5`. |
| `data/layout.json` | Posiciones. Ejemplo: `{"0": {"x": 220, "y": 160}}`. |

El grafo no es dirigido. Registra cada conexión una sola vez. No conectes un nodo
consigo mismo. Las posiciones faltantes se generan de forma automática.
Los archivos no guardan estados de Dijkstra ni selecciones de inicio y destino.
Cierra la aplicación antes de editar los archivos de forma manual.

## Exportaciones

Inicia Dijkstra. Usa los botones debajo del grafo para exportar el paso actual,
los pasos separados, una imagen conjunta o la ruta final.

Cada exportación crea una carpeta con fecha y hora dentro de `output/`.
Las imágenes incluyen el grafo y los datos del paso. Al terminar, aparece un aviso
con la ruta. Pulsa **Abrir carpeta** para ver los archivos. Git ignora `output/`.

## Estructura

```text
src/dijkstra_visualizer/
├── core/       # Validación y algoritmo; sin dependencia de Qt
├── io/         # Lectura y guardado de datos
├── ui/         # Interfaz, editor y escena de Qt
├── export/     # Generación de imágenes
└── paths.py    # Rutas del proyecto
data/           # Grafo y posiciones
tests/          # Pruebas y datos de prueba
output/         # Imágenes exportadas
```

## Verificación

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Para aplicar el formato, ejecuta `uv run ruff format .`.
Las pruebas de interacción usan archivos temporales. No modifican tu grafo.

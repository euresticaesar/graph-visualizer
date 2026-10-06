# Visualizador de Dijkstra

Aplicación de escritorio para editar grafos y explorar el algoritmo de Dijkstra
paso a paso. Está desarrollada con Python 3.12+, uv, PySide6 y NetworkX, y utiliza
pytest para las pruebas y Ruff para revisar el código.

## Instalación

Con uv instalado, abre una terminal en la carpeta del proyecto y ejecuta:

```sh
uv sync
uv run dijkstra-visualizer
```

La aplicación necesita un escritorio gráfico. Si quieres iniciarla desde otra
carpeta, puedes indicar la ruta del proyecto:

```sh
uv run --project /ruta/al/dijkstra-visualizer dijkstra-visualizer
```

## Uso

1. En **Editar grafo**, agrega nodos o selecciona uno existente para cambiar su ID.
2. Arrastra el borde de un nodo hasta otro y escribe el peso para crear una conexión.
3. Arrastra el centro de los nodos para acomodarlos; sus posiciones se guardan al soltar el mouse.
4. En **Recorrido**, elige el inicio y el destino, y pulsa **Iniciar Dijkstra**.
5. Revisa los pasos con **Anterior** y **Siguiente**.
6. Cuando quieras modificar el grafo, pulsa **Volver a editar**.

También puedes crear nodos con doble clic en el fondo; se propone el siguiente
ID disponible. Para cambiar un peso, haz clic en la arista o en su etiqueta.
Puedes cancelar estos diálogos sin guardar cambios.

Se permiten varias conexiones entre dos nodos y cada una aparece como una curva
separada. En **Editar grafo**, elige la conexión para cambiarla o eliminarla;
**Agregar otra conexión** crea una adicional con el peso indicado.

Los ID pueden ser enteros desde 0, sin un máximo definido por la aplicación.
No se permiten valores repetidos, negativos ni decimales. Los pesos, en cambio,
admiten decimales, pero deben ser positivos y finitos. Usa un punto, como en `2.5`.

Al eliminar un nodo también se borran sus conexiones, aunque el grafo debe
conservar al menos un nodo. Los cambios se guardan automáticamente, incluso al
deshacer o rehacer. El historial conserva hasta 100 acciones durante la sesión.

| Control | Acción |
| --- | --- |
| `Esc` al conectar nodos | Cancelar la conexión |
| Enter en **ID nuevo** | Cambiar el ID seleccionado |
| Enter en **Peso** | Guardar la conexión |
| **↶ / ↷** o `Ctrl+Z` / `Ctrl+Y` | Deshacer / rehacer |
| `Ctrl+0` | Ajustar la vista |
| Arrastrar el fondo / rueda del mouse | Desplazar / acercar o alejar |
| **Salir** o `Ctrl+Q` | Cerrar la aplicación |

## Algoritmo

Dijkstra está implementado en el propio proyecto. NetworkX se encarga de almacenar
el grafo, mientras que el cálculo de las rutas sigue estos pasos:

1. Asigna distancia 0 al inicio e infinito a los demás nodos.
2. Selecciona el nodo no visitado con menor distancia; si hay empate, elige el ID menor.
3. Marca ese nodo como visitado y termina si es el destino.
4. Actualiza las distancias y los predecesores de sus vecinos no visitados.
5. Repite hasta visitar el destino o agotar los nodos alcanzables.

Cada paso se guarda como un estado inmutable, por lo que puedes avanzar o
retroceder sin recalcular el recorrido. La ruta final se reconstruye a partir de
los predecesores y las conexiones elegidas, por lo que solo se resalta la arista
usada entre cada par de nodos. Si el destino no es alcanzable, la interfaz lo indica.

Las etiquetas muestran `[distancia, predecesor]`, con `∞` para una distancia aún
desconocida y `null` cuando no hay predecesor. Los nodos sin alcanzar son grises,
los tentativos amarillos y los visitados verdes. El nodo actual se distingue en
verde oscuro, el destino tiene borde rojo y la ruta final se marca en turquesa.

## Datos

Los archivos locales de `data/` se excluyen de Git. En el primer inicio, si no hay
archivos locales, la aplicación copia el grafo de `data/example/`. Ese ejemplo sí
se conserva en Git; tus cambios no lo modifican.

| Archivo | Contenido |
| --- | --- |
| `data/nodes.csv` | Nodos con el encabezado `id` y un ID por fila. |
| `data/edges.csv` | Conexiones con el encabezado `source,target,weight,id`; por ejemplo, `0,1,2.5,0`. |
| `data/layout.json` | Posiciones de los nodos; por ejemplo, `{"0": {"x": 220, "y": 160}}`. |

El ID de conexión distingue las aristas entre el mismo par de nodos. También se
acepta el formato anterior sin `id`; al guardar, se agrega esta columna.

Como el grafo no es dirigido, cada conexión se registra una sola vez. No se
permiten conexiones de un nodo consigo mismo. Si faltan posiciones, la aplicación
las genera automáticamente. Estos archivos no guardan los estados de Dijkstra
ni las selecciones de inicio y destino. Para editarlos a mano, cierra primero
la aplicación.

## Exportaciones

Después de iniciar Dijkstra, los botones debajo del grafo permiten exportar el
paso actual, los pasos por separado, una imagen conjunta o la ruta final.

Las imágenes incluyen el grafo y los datos del paso, y se guardan en una carpeta
con fecha y hora dentro de `output/`. Al terminar, aparece un aviso con la ruta;
puedes pulsar **Abrir carpeta** para ver los archivos. Esta carpeta se excluye de Git.

## Estructura

```text
src/dijkstra_visualizer/
├── core/       # Validación y algoritmo; sin dependencia de Qt
├── io/         # Lectura y guardado de datos
├── ui/         # Interfaz, editor y escena de Qt
├── export/     # Generación de imágenes
└── paths.py    # Rutas del proyecto
data/           # Grafo local y ejemplo versionado en example/
tests/          # Pruebas y datos de prueba
output/         # Imágenes exportadas
```

## Verificación

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Si necesitas aplicar el formato, ejecuta `uv run ruff format .`. Las pruebas de
interacción usan archivos temporales, por lo que no modifican tu grafo.

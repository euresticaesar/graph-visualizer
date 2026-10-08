# Ejecución y navegación

[← Inicio](../README.md) · [Exportaciones](exportaciones.md)

La pestaña **Recorrido** agrupa **Configurar recorrido**, **Explorar pasos** y **Reproducción automática**. Elige el algoritmo y sus opciones, luego **Iniciar**. Durante la ejecución, la explicación, la fase, la iteración y la posición aparecen en una tarjeta encima del grafo. Puedes avanzar, retroceder, ir al inicio/final con **⇤ / ⇥**, escribir un número de paso o saltar a una fase/iteración. **Reproducir / Pausar** utiliza un solo temporizador; el intervalo se expresa en milisegundos por paso.

**⇄** intercambia origen y destino en una sola acción deshacible. Durante Floyd-Warshall también permite invertir la ruta consultada sin recalcular; se deshabilita cuando uno de los selectores está bloqueado. Al escribir un número de paso, la navegación espera a que pulses **Enter** o salgas del campo. Al llegar al final, **Repetir recorrido** reproduce los mismos estados desde el inicio.

La reproducción se detiene al llegar al final, cambiar de algoritmo o detalle, cargar un preset, abrir otra pestaña, exportar o volver a editar. Cambiar de detalle navega sobre los mismos eventos ya calculados y elige una posición equivalente, sin recalcular ni volver obligatoriamente al inicio.

A* muestra las prioridades g, h y f; Bellman-Ford muestra sus tablas y Floyd-Warshall sus matrices en un **panel de resultados** que aparece al iniciar el algoritmo. La distribución predeterminada coloca el panel a la derecha; **Personalizar** permite ponerlo debajo del grafo. Puedes ajustar el ancho arrastrando su separador con el grafo y repartir la altura entre las dos tablas o matrices. El panel se oculta al volver a editar o usar Dijkstra. Las tablas y matrices tienen desplazamiento y encabezados. Con grafos grandes, usa zoom, desplazamiento y los separadores para revisar los detalles.

## Elegir un algoritmo

| Algoritmo | Qué calcula | Pesos negativos |
| --- | --- | --- |
| [A*](algoritmos/astar.md) | Una ruta guiada por una heurística admisible | Se rechazan en todo el grafo |
| [Dijkstra](algoritmos/dijkstra.md) | Una ruta entre origen y destino | Se rechazan en todo el grafo |
| [Bellman-Ford](algoritmos/bellman-ford.md) | Desde un origen a todos los nodos | Se admiten en grafos dirigidos |
| [Floyd-Warshall](algoritmos/floyd-warshall.md) | Todos los pares de nodos | Se admiten en grafos dirigidos |

**Marcar paso** identifica el evento original para exportarlo después mediante **Pasos marcados**. **Copiar imagen** / `Ctrl+Shift+C` usa el paso exacto y las opciones de Exportar. Con foco en el lienzo, las flechas navegan y Espacio reproduce o pausa; `Alt+←/→` navega desde otros controles. **Cancelar operación** permanece disponible durante un cálculo en segundo plano o una exportación.

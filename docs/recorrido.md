# Ejecución y navegación

[← Inicio](../README.md) · [Exportaciones](exportaciones.md)

La pestaña **Recorrido** agrupa **Configurar recorrido**, **Explorar pasos** y **Reproducción automática**. Elige el algoritmo y sus opciones, luego **Iniciar**. Durante la ejecución, la explicación, la fase, la iteración y la posición aparecen en una tarjeta encima del grafo. Puedes avanzar, retroceder, ir al inicio/final con **⇤ / ⇥**, escribir un número de paso o saltar a una fase/iteración. **Reproducir / Pausar** utiliza un solo temporizador; el intervalo se expresa en milisegundos por paso.

Deja el puntero sobre una casilla para consultar su ayuda breve. **Por comparación** muestra cada comparación al activarlo y resume por nodo al desactivarlo; en Floyd-Warshall el resumen corresponde a cada intermedio `k`.

**⇄** intercambia origen y destino en una sola acción deshacible. Durante Floyd-Warshall también permite invertir la ruta consultada sin recalcular; se deshabilita cuando uno de los selectores está bloqueado. Al escribir un número de paso, la navegación espera a que pulses **Enter** o salgas del campo. Al llegar al final, **Repetir recorrido** reproduce los mismos estados desde el inicio.

La reproducción se detiene al llegar al final, cambiar de algoritmo o detalle, cargar un preset, abrir otra pestaña, exportar o volver a editar. Cambiar de detalle navega sobre los mismos eventos ya calculados y elige una posición equivalente, sin recalcular ni volver obligatoriamente al inicio.

A* muestra las prioridades g, h y f; Bellman-Ford muestra sus tablas y Floyd-Warshall sus matrices en un **panel de resultados** que aparece al iniciar el algoritmo. La distribución predeterminada coloca el panel a la derecha; **Personalizar** permite ponerlo debajo del grafo. Puedes ajustar el ancho arrastrando su separador con el grafo y repartir la altura entre las dos tablas o matrices. El panel se oculta al volver a editar o usar Dijkstra. Las tablas y matrices tienen desplazamiento y encabezados. Con grafos grandes, usa zoom, desplazamiento y los separadores para revisar los detalles.

En el layout inferior, una ventana de menos de 820 px de alto activa el modo compacto: oculta hints, reduce mínimos de tablas y reserva espacio al grafo. Al ampliar recupera la densidad normal. Los separadores se ajustan para evitar solapamientos y mantienen las proporciones manuales cuando caben. Las matrices permiten seleccionar una celda y navegar con las flechas; su descripción accesible identifica fila, columna, comparación y mejora. Los cambios de estado, errores y progreso de exportación se anuncian mediante el API de accesibilidad nativo de Qt.

## Elegir un algoritmo

| Algoritmo | Qué calcula | Pesos negativos |
| --- | --- | --- |
| [A*](algoritmos/astar.md) | Una ruta guiada por una heurística admisible | Se rechazan en todo el grafo |
| [Dijkstra](algoritmos/dijkstra.md) | Una ruta entre origen y destino | Se rechazan en todo el grafo |
| [Bellman-Ford](algoritmos/bellman-ford.md) | Desde un origen a todos los nodos | Se admiten en grafos dirigidos y no dirigidos |
| [Floyd-Warshall](algoritmos/floyd-warshall.md) | Todos los pares de nodos | Se admiten en grafos dirigidos y no dirigidos |

El grafo admite pesos negativos al editar, guardar y cargar. Al seleccionar **Dijkstra** o **A*** con algún peso negativo, **Iniciar** queda deshabilitado y una explicación visible recomienda los algoritmos compatibles. Al quitar el último peso negativo, el botón vuelve a estar disponible; también se actualiza al deshacer, rehacer o cargar un preset. En un grafo no dirigido, una conexión negativa genera un ciclo negativo al recorrerla de ida y vuelta: Bellman-Ford y Floyd-Warshall muestran **−∞** en los resultados afectados.

**Marcar paso** guarda el evento original en **Explorar pasos → Marcas (n)**. La lista muestra las marcas en orden del recorrido; elige una para saltar a ese paso y detener la reproducción. La ayuda de cada entrada incluye evento, iteración y explicación. Si una comparación marcada está oculta por el modo resumen, aparece como **Evento … (detalle)** y elegirla activa **Por comparación** para mostrar el evento exacto, sin recalcular. El selector funciona con teclado y se actualiza también con las marcas del visor de presentación. **Quitar marca** retira el paso visible; **Volver a editar** o iniciar otro algoritmo limpia las marcas de esa ejecución. Para exportarlas, selecciona **Pasos marcados** en Exportar.

**Copiar imagen** / `Ctrl+Shift+C` usa el paso exacto y el tema y acento actuales de la interfaz. Conserva las demás opciones de Exportar, como resolución, composición, tipografía, foco, explicación y leyenda. El esquema elegido para los archivos de exportación se mantiene independiente. Con foco en el lienzo, las flechas navegan y Espacio reproduce o pausa; `Alt+←/→` navega desde otros controles. **Cancelar operación** permanece disponible durante un cálculo en segundo plano o una exportación.

## Visor de presentación

**Presentar** / `F11` abre las diapositivas a pantalla completa con la composición, tema y resolución de Exportar. Selecciona avance por **Pasos**, **Fases** o **Marcas**; escribe un paso para saltar directamente. Las marcas identifican el evento original y se comparten con el escritorio. Si no hay marcas, el visor indica cómo crear una.

| Tecla | Acción en el visor |
| --- | --- |
| `←` / `→` | Retroceder / avanzar según el modo seleccionado |
| `Home` / `End` | Primer / último paso del modo |
| `Espacio` | Reproducir / pausar con el intervalo del escritorio |
| `M` | Marcar / quitar marca del paso |
| `H` | Ocultar / mostrar controles |
| `Esc` / `F11` | Salir |

El visor muestra una diapositiva completa por estado, con matrices y arcos íntegros; el foco ampliado es opcional y no reemplaza las tablas. Salir conserva el paso visible, el zoom y las posiciones del escritorio. `Ctrl+1..4` cambia de pestaña en el escritorio y `Ctrl+Alt+P` abre los perfiles visuales.

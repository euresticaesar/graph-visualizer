# A* (A estrella)

[← Inicio](../../README.md) · [Recorridos](../recorrido.md)

Selecciona **A*** en Recorrido, elige origen y destino e inicia. Busca una ruta mínima en grafos dirigidos o no dirigidos, incluidas conexiones paralelas. Rechaza pesos negativos. Origen y destino quedan bloqueados durante la ejecución porque la búsqueda depende de ambos.

La tabla muestra **g**, costo acumulado desde el origen; **h**, estimación del costo restante; **f = g + h**, prioridad de expansión; y el predecesor. Los empates se resuelven por ID de nodo. Puedes revisar cada comparación o un resumen por nodo, exportar ambos niveles y guardar A* en presets.

La heurística automática multiplica el número mínimo de saltos hasta el destino por el menor peso del grafo. Los saltos se calculan con una búsqueda en anchura desde el destino sobre los arcos invertidos. Es una cota inferior consistente: cada conexión cuesta al menos ese peso mínimo y puede reducir como máximo un salto. Las posiciones del dibujo no intervienen. Para nodos sin camino al destino se usa una cota finita común de un salto más que el máximo alcanzable; no afecta la corrección ni produce infinitos en la prioridad.

Con peso mínimo cero, h es cero y el orden equivale a Dijkstra. Esta heurística no garantiza explorar menos nodos en todos los grafos. El destino confirma su ruta al ser seleccionado; si no es alcanzable, se indica que no hay ruta. Se conserva el ID exacto de cada conexión de la ruta, incluso con arcos paralelos.

Las exportaciones didácticas incluyen g, h, f, predecesores, explicación de las comparaciones y ruta final. El estilo simple conserva únicamente el grafo y sus resaltados.

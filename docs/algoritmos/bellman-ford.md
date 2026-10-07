# Bellman-Ford

[← Inicio](../../README.md) · [Recorridos](../recorrido.md)

Calcula desde el origen hacia **todos** los nodos. El destino solo consulta una ruta; puedes cambiarlo durante la ejecución.

Se muestran el grafo, la lista de arcos ordenada por origen/destino/clave y la tabla **V / d / π** (nodo, distancia, predecesor). Cada arco produce un paso, también si su origen está a ∞ o no mejora. Las mejoras son inmediatas y las usa el arco siguiente de esa misma pasada. Los grafos no dirigidos generan dos arcos por conexión, conservando su identidad.

Por defecto completa las `|V|−1` pasadas. Puedes activar **Terminar tras una pasada sin cambios** antes de iniciar. Después aparece una fase separada de verificación, arco por arco. Esta pasada de sondeo permite encontrar un ciclo concreto.

Si hay un ciclo negativo alcanzable, se resalta en rojo y se marcan con **−∞** sus nodos y todos los alcanzables desde él. No tienen costo mínimo finito. Los demás resultados siguen siendo válidos. Un ciclo inaccesible desde el origen no invalida la ejecución. No se presentan cadenas de predecesores cíclicas como rutas mínimas.

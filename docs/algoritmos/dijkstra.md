# Dijkstra

[← Inicio](../../README.md) · [Recorridos](../recorrido.md)

Calcula la ruta entre el origen y el destino y termina al seleccionar el destino. **Por comparación** está activado inicialmente: hay inicialización, selección del nodo y una comparación por conexión hacia un vecino no fijado, incluso si no mejora. Las conexiones paralelas se comparan individualmente. Desmarca la opción para ver el resumen por nodo.

Las comparaciones muestran distancia anterior, candidata, respuesta y distancia/predecesor resultantes. Solo una mejora estricta cambia distancia y recorrido. Los empates conservan la primera ruta encontrada en el orden determinista. El verde identifica nodos fijados; el naranja identifica la conexión comparada; el turquesa, la ruta final.

Si hay **cualquier peso negativo**, Dijkstra se bloquea y recomienda los otros algoritmos, aunque la conexión negativa no sea alcanzable desde el origen.

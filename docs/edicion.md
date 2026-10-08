# Edición del grafo

[← Inicio](../README.md) · [Recorridos](recorrido.md)

En **Editar** puedes agregar, renombrar y eliminar nodos, cambiar pesos y crear conexiones paralelas. Los controles se agrupan en tarjetas de **Tipo de grafo**, **Nodos** y **Conexiones y pesos**. Cada grafo es dirigido o no dirigido; no se mezclan ambos tipos.

- **IDs:** strings no vacíos; se eliminan espacios exteriores y se distinguen mayúsculas (`A` y `a` son nodos diferentes). Letras, nombres, comas, comillas y números escritos como texto son válidos. No existe un atributo numérico adicional de “valor”. Se rechazan duplicados después de normalizar espacios.
- **Orden de selección:** los IDs numéricos se muestran de menor a mayor (`"2"` antes de `"10"`). Si hay nombres y números, primero aparecen los nombres de A a Z, sin distinguir mayúsculas para ordenar, y después los números. Admite negativos, decimales y notación científica; los IDs originales siguen siendo strings distintos, incluidos `"01"` y `"1"`. El orden interno de los algoritmos, matrices y desempates continúa siendo lexicográfico.
- **Pesos:** números finitos, incluido cero. Los negativos solo se permiten en grafos dirigidos. Se rechazan NaN, infinitos y conexiones de un nodo consigo mismo.
- **Identidad:** una conexión se identifica por sus extremos y su clave entera no negativa. En un grafo dirigido `(u,v,id)` es distinto de `(v,u,id)`. Las claves pueden repetirse en pares diferentes. Los dibujos muestran solo el peso inicialmente; activa **IDs de conexiones** encima del lienzo para añadir `#id`. La identidad sigue disponible en el tooltip, el editor y las tablas. Las curvas separan paralelas y sentidos opuestos.
- **Cambio de tipo:** no dirigido → dirigido crea dos arcos por conexión con la misma clave. Dirigido → no dirigido conserva cada arco como una conexión; si las claves del par chocan, asigna la siguiente clave libre. Rechaza la conversión si hay pesos negativos. Nunca fusiona conexiones silenciosamente. Puedes deshacer la conversión.

## Gestos en el lienzo

Doble clic en el fondo agrega un nodo; arrastrar su centro lo mueve; arrastrar el borde hasta otro nodo crea una conexión; clic en una conexión o su peso permite editarla. La rueda cambia el zoom, arrastrar el fondo desplaza la vista y **Ajustar vista** / `Ctrl+0` encuadra el grafo.

## Etiquetas y ayuda

**Gestos y ayuda** despliega las instrucciones sobre el lienzo; **Colores y notación** abre la leyenda en la barra izquierda. Ambas comienzan plegadas para dejar más espacio al grafo. Los toggles de etiquetas de estado e IDs de conexiones guardan su selección entre sesiones, incluidos cambios de algoritmo, edición, deshacer/rehacer y cargas de presets; no modifican los datos del grafo ni el preset.

## Autoguardado e historial

Los cambios se guardan automáticamente. **↶ / ↷**, `Ctrl+Z` y `Ctrl+Y` conservan hasta 100 acciones, incluidos movimientos, cambios de tipo y cargas de presets. Durante cálculos y exportaciones se bloquean también los atajos de edición; **Volver a editar** detiene la reproducción y conserva el historial.

**Datos del grafo** (`Ctrl+D`) permite revisar los IDs completos y editar coordenadas con teclado. Selecciona filas para alinear o distribuir nodos y pulsa **Aplicar**: todo el acomodo se guarda como una sola acción deshacible. Los IDs largos se abrevian visualmente sin modificar su identidad ni su zona de conexión.

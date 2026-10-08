# Personalización del espacio de trabajo

[← Inicio](../README.md) · [Exportaciones](exportaciones.md)

Pulsa **Personalizar** o `Ctrl+,` para cambiar el esquema **Claro, Oscuro, Sepia, Alto contraste o Impresión**. Puedes elegir un acento propio, texto de interfaz de 11 a 18 px y escala del texto del grafo de 0.8 a 1.5. **Restaurar valores predeterminados** recupera los ajustes visuales iniciales.

Las distribuciones disponibles son controles a la izquierda, controles a la derecha, tablas debajo del grafo y lienzo amplio. Los separadores permiten ajustar el espacio de controles y resultados. **Ampliar lienzo** / `Ctrl+Shift+F` oculta los controles; **Mostrar controles** recupera la distribución anterior. La interfaz mantiene colores semánticos comunes en el grafo, las tablas y la leyenda.

El encuadre automático se adapta al tamaño de la ventana y al movimiento de los separadores. Usar la rueda conserva el zoom manual; **Ajustar vista** / `Ctrl+0` vuelve al encuadre automático. Cambiar un tema conserva las posiciones del grafo.

Las preferencias se guardan en `preferences.json`, dentro del directorio de trabajo. Incluyen apariencia, tamaño de ventana, separadores, etiquetas, IDs de conexiones y opciones de exportación. Son independientes de los presets: cargar un grafo no cambia el tema del usuario. Los valores inválidos se sustituyen por los predeterminados.

**Datos del grafo** / `Ctrl+D` ofrece tablas navegables con teclado para revisar IDs completos, coordenadas, conexiones, distancias y estados. En edición puedes escribir X/Y o seleccionar varias filas para alinear o distribuir los nodos. **Aplicar** guarda una acción deshacible. La distribución conserva los extremos de la selección; la alineación utiliza la coordenada media.

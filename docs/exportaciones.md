# Exportaciones PNG y PDF

[← Inicio](../README.md) · [Recorridos](recorrido.md)

En **Exportar**, elige **Imágenes PNG** o **Documento PDF**, el estilo y el nivel de detalle. Ambos formatos usan diapositivas horizontales de **1920 × 1080**, independientes del tamaño de la ventana. El PDF contiene una imagen por página, sin márgenes ni recortes, en proporción 16:9 (1440 × 810 puntos a 96 ppp). No genera PNG intermedios ni requiere dependencias adicionales.

Puedes exportar el **paso actual**, **pasos separados**, **conjuntas** o **resultado final**. En PDF, “pasos separados” significa una página por estado dentro de un único documento. Las conjuntas agrupan hasta cuatro estados en una cuadrícula de dos columnas; el contenido se reduce para caber en la diapositiva. Usa pasos separados para la mayor legibilidad.

**Mostrar vista previa antes de exportar** está activado por defecto. Al pulsar cualquier modalidad de exportación aparece una muestra de hasta dos imágenes o páginas con la configuración elegida. Pulsa **Exportar PDF** o **Exportar imágenes** para crear los archivos; **Cancelar**, Escape o cerrar la ventana vuelve sin exportar. Desmarca la casilla para exportar directamente. La muestra respeta estilo, detalle, etiquetas, IDs y posiciones actuales, sin cambiar el paso visible.

Los botones indican el número de imágenes o páginas según el formato. El detalle visible es el predeterminado; Dijkstra, A* y Floyd-Warshall permiten elegir resumen o subpasos sin modificar la navegación. Bellman-Ford conserva un paso por arco.

**Didáctico:** algoritmo, fase, numeración, grafo, explicación y leyenda. A* incluye g, h, f y predecesor; Bellman-Ford incluye distancias y la lista completa de arcos; Floyd-Warshall incluye ambas matrices. Las tablas de A* y Bellman-Ford se dividen en bloques horizontales con encabezados repetidos y rangos de filas, conservando el resaltado del arco actual. La cantidad de filas se adapta al volumen de datos. Los resultados finales muestran ruta y costo o explican la ausencia de ruta/ciclo negativo.

**Simple:** solo el grafo, IDs de nodos, pesos, flechas y resaltados. No incluye títulos, etiquetas de distancia/predecesor, leyendas ni tablas. Ambos estilos respetan la opción **IDs de conexiones**; las tablas didácticas conservan siempre los IDs de los arcos.

Cada operación crea una carpeta con fecha y hora. El PDF se llama `diapositivas.pdf`; PNG conserva los nombres por paso, resultado o conjunta. El aviso de éxito permite abrir la carpeta. El render intermedio tiene un límite de 100 megapíxeles para evitar asignaciones excesivas. En grafos muy densos las tablas se reducen para entrar en una página; revisa la muestra antes de exportar.

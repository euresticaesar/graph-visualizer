# Exportaciones PNG

[← Inicio](../README.md) · [Recorridos](recorrido.md)

La pestaña **Exportar** reúne el formato, los pasos que se exportan y la carpeta de salida. Exporta el **paso actual**, **todos los pasos separados**, **imágenes conjuntas** o el **resultado final**. Por defecto se usa el detalle visible; para Dijkstra y Floyd-Warshall puedes elegir resumen o subpasos sin modificar la navegación en pantalla.

Debajo de cada botón aparece la cantidad de PNG que se generarán con las opciones elegidas. Paso actual y resultado final producen una imagen; pasos separados produce una por estado exportado. Las conjuntas se cuentan con los tamaños y límites reales de la exportación, incluidos cambios de tamaño entre pasos. El cálculo se realiza por partes mientras la pestaña está abierta, sin crear PNG y sin bloquear la interfaz; sus resultados se reutilizan al volver a las mismas opciones.

**Didáctico:** algoritmo, fase, numeración, grafo, explicación y leyenda. Bellman-Ford incluye lista completa de arcos y tabla; Floyd-Warshall incluye ambas matrices. Los resultados finales incluyen la ruta consultada y su costo cuando son válidos, o la explicación de ausencia de ruta/ciclo negativo.

**Simple:** únicamente el grafo, con IDs de nodos, pesos, flechas y resaltados. No incluye títulos, etiquetas de distancia/predecesor, leyendas, tablas ni matrices. En Floyd-Warshall conserva la ruta consultada cuando existe; para compartir las matrices usa el estilo didáctico.

Ambos estilos respetan **IDs de conexiones**: con el toggle desactivado las aristas muestran solo el peso; activado, añaden `#id`. Las tablas didácticas conservan los IDs para identificar cada arco.

Cada operación crea una carpeta con fecha y hora. Las composiciones conservan el tamaño legible de sus imágenes, sin reducirlas a miniaturas: se dividen en archivos `conjunta_0001.png`, etc., con hasta cuatro pasos por página y un presupuesto de 24 megapíxeles/12 000 píxeles de alto. Una imagen individual más grande ocupa su propia página. El máximo individual es 100 megapíxeles; si un layout extremadamente extendido lo excede, se solicita reducirlo. El aviso de exportación permite abrir su carpeta.

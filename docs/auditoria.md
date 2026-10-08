# Auditoría y mejoras de calidad

[← Inicio](../README.md) · [Exportaciones](exportaciones.md) · [Personalización](personalizacion.md)

El análisis priorizó la fidelidad y legibilidad de las imágenes y documentos finales. Se revisaron los cuatro algoritmos existentes, historial, edición, presets, cálculo en segundo plano, render, persistencia y flujos de exportación. Se reprodujeron casos con 30 nodos, IDs largos, pesos pequeños y ciclos negativos. No se añadieron algoritmos de caminos.

## Hallazgos corregidos

| Prioridad | Evidencia anterior | Corrección |
| --- | --- | --- |
| Alta | Un estado grande podía requerir varias imágenes, incompatibles con un slideshow de un paso por diapositiva | Una sola diapositiva 16:9 con grafo, matrices completas o listas en columnas, explicación, ruta y leyenda; composición y escala adaptativas |
| Alta | Las esquinas superiores y el espacio vacío de los encabezados mostraban cuadrados negros en el tema claro | Fondo explícito para `QHeaderView`, `QTableCornerButton` y esquina del área desplazable, comprobado en los cinco temas |
| Alta | Exportar un paso detallado con la opción Resumen podía cambiar del evento 2 al 4 | El paso actual conserva el evento exacto; el manifiesto registra evento, explicación y página |
| Alta | Una escritura de PDF rechazada podía terminar con aviso de éxito | Se comprueban apertura, finalización y commit; publicación de carpeta completa y limpieza de resultados parciales |
| Alta | Ctrl+Y durante un worker podía modificar el grafo y provocar un error de índices | Bloqueo de acciones y guardas durante operaciones, copia del grafo y revisión asociada al resultado |
| Alta | Floyd-Warshall trataba pares de índices afectados como IDs de nodo | El estado negativo del nodo corresponde a la distancia desde el origen consultado; `−∞` y `∞` se distinguen |
| Media | Pesos `±1e-7` se mostraban como cero | Formato adaptativo con notación científica, conservando signo y precisión útil |
| Media | IDs largos ocupaban las aristas y no coincidían con la geometría gestual | Elisión con etiquetas únicas, geometría compartida y referencia de IDs completos |
| Media | Deshacer una carga de preset recuperaba el grafo pero no sus ajustes | Historial de algoritmo, detalle, parada temprana y asociación al preset, incluso con grafos idénticos |
| Media | Mostrar el aviso de exportación cambiaba el zoom mediante autoencuadre | El autoencuadre responde a ventana/separadores; exportar conserva la transformación de la vista |
| Media | Las conjuntas reducían la resolución efectiva de cada estado | Montajes de mayor tamaño que conservan los píxeles de cada página individual |

## Funciones incorporadas

- PNG con resolución configurable; PDF y SVG vectoriales, con render compartido con la vista previa.
- Navegación completa de la vista previa, zoom al 100 %, título, tipografía, leyenda y composición configurables.
- Filtros por rango inclusivo, mejoras y eventos marcados; copia de imagen al portapapeles.
- Cinco esquemas de color, acento personalizado, cuatro distribuciones de interfaz y preferencias independientes de los presets.
- Cancelación cooperativa de cálculos y cancelación entre páginas de exportación.
- Datos accesibles mediante tablas de nodos/conexiones, edición de coordenadas y alineación/distribución manual deshacible.
- Exportación desde preset por terminal, sin modificar el trabajo abierto.
- Grafo reproducible y manifiesto con explicaciones completas, rutas, dimensiones y eventos originales junto a cada exportación.

La verificación incluye pruebas de algoritmos contra NetworkX, integridad de todas las celdas y resaltados de matrices completas, geometría sin solapamientos, una página/archivo por estado en PNG/PDF/SVG, explicación íntegra en PDF, errores de escritura, cancelación, conservación de vista y estados, historial, preferencias, contraste y texto vectorial. La inspección visual cubrió los cinco esquemas, cuatro distribuciones, ventanas grandes y pequeñas, tipografía ampliada, 30 nodos e IDs largos.

El preset de 30 nodos conserva las **1 800 celdas de Floyd-Warshall** o los **126 arcos ordenados de Bellman-Ford** junto al grafo en una imagen. La densidad impone un límite de lectura: en la muestra de Floyd-Warshall el texto base efectivo es aproximadamente **8.9 px en HD** y **17.8 px en 4K**, antes de ajustes individuales de celdas. El tamaño solicitado puede reducirse para cumplir la integridad de la diapositiva. Aumentar los píxeles facilita la inspección y el zoom, pero al proyectar la imagen completa sobre una pantalla de igual tamaño siguen presentes los mismos datos. No se promete letra grande para matrices arbitrariamente densas.

## Backlog para otro agente

Estas oportunidades quedan separadas de las correcciones implementadas. Mantener los cuatro algoritmos actuales.

### P1 — Diagnóstico de legibilidad antes de exportar

La integridad está cubierta; la letra puede resultar demasiado pequeña en matrices grandes, rutas largas o explicaciones extensas. Añadir un diagnóstico que mida el tamaño efectivo mínimo del texto y muestre sus causas en la vista previa, con acciones para cambiar resolución, escala o distribución. Mantener una sola diapositiva 16:9 por estado y todos sus datos; evitar soluciones de continuación. Para proyección, proponer una ampliación opcional de la celda/comparación activa dentro de la misma diapositiva, conservando ambas matrices completas. Criterios: el diagnóstico coincide con el render real y PNG/PDF/SVG conservan idéntica composición.

### P1 — Presets de presentación reutilizables

Permitir guardar, nombrar, importar y exportar combinaciones de tema, acento, tipografía, resolución, leyenda y composición, además de las cuatro distribuciones de UI existentes. Conservar su independencia del preset del grafo y mantener compatibilidad de preferencias. Añadir esquemas específicos para daltonismo y codificación redundante mediante trazos o símbolos; verificar contraste de cada estado y celda resaltada. Criterios: ida y vuelta del perfil sin cambios de grafo, preferencias antiguas compatibles y vista previa fiel.

### P2 — Conexiones con etiquetas densas

Una geometría cargada todavía puede solapar pesos y anotaciones. Añadir offsets de etiquetas editables manualmente y opción de atenuar conexiones ajenas a la ruta consultada para la exportación. Persistir estos ajustes de presentación, conservar la identidad `(origen, destino, id)` y comprobar paralelas, sentidos opuestos y enlaces cruzados. Criterios: edición deshacible, guardado reproducible y mismos offsets en pantalla y exportación; conservar las conexiones y sus tablas.

### P2 — Modo presentación y composición ajustable

Añadir un visor a pantalla completa con teclado, favoritos, pausa y avance por evento o fase. Permitir ajustar la proporción grafo/tablas y elegir una composición lateral o superior, además de la selección adaptativa actual. Mantener el lienzo 16:9 y validar los límites al mover separadores para evitar recortes. Criterios: la vista previa reproduce la exportación, cada paso contiene toda la información y salir del visor conserva navegación, zoom y posiciones.

### P2 — Regresión visual mantenible

Convertir las muestras verificadas en fixtures visuales de render con fuentes y backend Qt controlados. Cubrir temas, tipografía 1.5, negativos, IDs largos, ambas matrices completas y esquinas de tablas. Evitar comparar capturas completas de escritorio entre sistemas distintos; verificar geometría y zonas relevantes con tolerancias documentadas. Criterios: un cambio que pierda una celda, un arco o el final de una explicación debe fallar; los cambios legítimos requieren actualizar muestras revisables.

### P2 — Accesibilidad y operación por teclado

Auditar el flujo completo de foco, edición tabular, vista previa y personalización con teclado y lector de pantalla. El diálogo de datos ya permite consultar valores y modificar coordenadas; mejorar nombres de conexiones paralelas, anuncio del estado actual y del progreso de exportación. Criterios: crear/editar un grafo, recorrerlo y exportarlo sin ratón, con indicadores de foco visibles en los cinco temas.

### P3 — Compatibilidad interna del exportador

`image_exporter.py` conserva helpers de medición antiguos para compatibilidad; no intervienen en el render actual. Migrar sus consumidores y pruebas al compositor de diapositivas y retirarlos con una política explícita de compatibilidad. Mantener una sola fuente de dimensiones, bloques, colores y resaltados. Criterios: vista previa y archivos usan exclusivamente `SlideRenderer`, sin pérdida de integridad ni cambios de recuento.

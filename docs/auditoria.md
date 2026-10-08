# Auditoría y mejoras de calidad

[← Inicio](../README.md) · [Exportaciones](exportaciones.md) · [Personalización](personalizacion.md)

El análisis priorizó la fidelidad y legibilidad de las imágenes y documentos finales. Se revisaron los cuatro algoritmos existentes, historial, edición, presets, cálculo en segundo plano, render, persistencia y flujos de exportación. Se reprodujeron casos con 30 nodos, IDs largos, pesos pequeños y ciclos negativos. No se añadieron algoritmos de caminos.

## Hallazgos corregidos

| Prioridad | Evidencia anterior | Corrección |
| --- | --- | --- |
| Alta | Un estado grande podía requerir varias imágenes, incompatibles con un slideshow de un paso por diapositiva | Una sola diapositiva 16:9 con grafo, matrices completas o listas en columnas, explicación, ruta y leyenda; composición y escala adaptativas |
| Alta | Las esquinas superiores y el espacio vacío de los encabezados mostraban cuadrados negros en el tema claro | Fondo explícito para `QHeaderView`, `QTableCornerButton` y esquina del área desplazable, comprobado en los seis temas |
| Alta | La vista previa comprimía la altura del QLabel y recortaba título, explicación, tablas y leyenda | Cada QLabel tiene el tamaño completo de su pixmap, centrado horizontalmente; el desplazamiento permite consultar ambos extremos y Encajar reserva un ancho estable para la scrollbar |
| Alta | El layout inferior compacto conservaba posiciones de splitter incompatibles con los mínimos nuevos | Activación de layouts, mínimos efectivos y reajuste del splitter sin recursión; los tamaños manuales válidos se conservan al reducir, ampliar y cambiar de algoritmo |
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
- Seis esquemas de color, acento personalizado, cuatro distribuciones de interfaz y preferencias independientes de los presets.
- Cancelación cooperativa de cálculos y cancelación entre páginas de exportación.
- Datos accesibles mediante tablas de nodos/conexiones, edición de coordenadas y alineación/distribución manual deshacible.
- Exportación desde preset por terminal, sin modificar el trabajo abierto.
- Grafo reproducible y manifiesto con explicaciones completas, rutas, dimensiones y eventos originales junto a cada exportación.

La verificación incluye pruebas de algoritmos contra NetworkX, integridad de todas las celdas y resaltados de matrices completas, geometría sin solapamientos, una página/archivo por estado en PNG/PDF/SVG, explicación íntegra en PDF, errores de escritura, cancelación, conservación de vista y estados, historial, preferencias, contraste y texto vectorial. Las regresiones de vista previa comprueban ancho, altura, centrado, acceso a ambos extremos y estabilidad tras redimensionar en Encajar, 50 % y 100 %, con temas claro y oscuro. El layout inferior se comprueba al pasar de 940 × 680 a 940 × 940 y volver, cambiar de layout y alternar Bellman-Ford, A* y Floyd-Warshall. Las pruebas nativas comprueban las esquinas y zonas vacías en los seis temas.

El preset de 30 nodos conserva sus **63 conexiones no dirigidas**, las **1 800 celdas de Floyd-Warshall** o los **126 arcos ordenados de Bellman-Ford** junto al grafo en una imagen. Las muestras finales consultan `1 → 666` y conservan la ruta **1 → 10 → 27 → 666, costo 10**. La densidad impone un límite de lectura: con Qt 6.11.2 y Noto Sans, la muestra actual de Floyd-Warshall tiene un mínimo real de tablas de aproximadamente **15.1 px en 4K** y texto del grafo de **11.1 px**, incluyendo los ajustes individuales. Estas medidas dependen de la fuente y la composición; el diagnóstico de cada exportación es la referencia. Aumentar los píxeles facilita la inspección y el zoom, pero al proyectar la imagen completa sobre una pantalla de igual tamaño siguen presentes los mismos datos. No se promete letra grande para matrices arbitrariamente densas.

## Estado de las siete tareas de la auditoría

Las siete tareas están implementadas. Se conservan exclusivamente los cuatro algoritmos originales.

### P1 — Diagnóstico de legibilidad antes de exportar

Implementada. La vista previa mide las fuentes realmente ajustadas y las transformaciones del renderer, por categoría: grafo, tablas, título, explicación, leyenda y foco. Avisa por debajo de 12 px y ofrece **Usar 4K** y **Ajustar composición**. El foco amplía la comparación o una celda mejorada dentro de la misma diapositiva, sin sustituir ninguna tabla. Los píxeles medidos no garantizan lectura a distancia en proyección.

### P1 — Presets de presentación reutilizables

Implementada. **Perfiles** guarda, aplica, renombra, elimina, importa y exporta tema, acento, tipografía, opciones de exportación y layout de UI. No altera el grafo ni el evento visible y no incluye dimensiones del equipo. El sexto tema es **Daltónico (azul y naranja)**; comparación y ciclo negativo tienen trazos redundantes y las mejoras usan negritas. Se validan archivos antes de modificar preferencias y se mantiene la compatibilidad con perfiles antiguos.

### P2 — Conexiones con etiquetas densas

Implementada. Los offsets X/Y se editan en **Datos del grafo**, se restablecen por selección y son persistentes y deshacibles por `(origen, destino, id)`, incluidas paralelas y sentidos opuestos. La exportación puede atenuar conexiones ajenas a la ruta sin eliminarlas ni modificar las tablas. La colocación sigue siendo manual: una geometría arbitrariamente densa puede requerir ajustar posiciones y etiquetas.

### P2 — Modo presentación y composición ajustable

Implementada. **Presentar / F11** abre el visor de las mismas diapositivas, con pasos, fases, marcas, reproducción y teclado. Salir conserva el paso, zoom y posiciones del escritorio; las marcas son compartidas. Exportar admite composición adaptativa, grafo a la izquierda o arriba y una proporción manual de 20–65 %. Cada estado completo sigue siendo 16:9. El escritorio adapta mínimos y hints en el layout inferior compacto; otros layouts o tipografías mayores pueden exigir una ventana más alta para conservar el panel visible.

### P2 — Regresión visual mantenible

Implementada. Las referencias cubren matrices y resaltados, ciclo negativo, IDs largos con escala 1.5 y tema oscuro, y foco daltónico. Comparan regiones y celdas con diferencia media RGBA ≤ 2 bajo Qt y métricas de fuente coincidentes. Las pruebas de integridad, texto y geometría cubren además las matrices de 30 × 30, todos los arcos y esquinas nativas. El renderer de referencias selecciona DejaVu Sans, instalado en CI; allí `GV_REQUIRE_RENDER_REFERENCES=1` convierte una discrepancia de entorno en fallo, evitando omisiones sistemáticas. La regeneración requiere inspección visual; las capturas nativas son evidencia revisable, no goldens portables entre sistemas.

### P2 — Accesibilidad y operación por teclado

Implementada y verificada por teclado y pruebas del API accesible de Qt. Se añadieron nombres y descripciones, identidad explícita de conexiones, selección de matrices, foco visible, anuncios de estados, errores y progreso, y atajos de pestañas, perfiles y presentación. Las pruebas recorren creación de nodo, navegación y apertura de exportación sin ratón. Queda como validación manual de plataforma la escucha con lectores de pantalla reales; las pruebas de anuncios nativos no sustituyen esa comprobación.

### P3 — Compatibilidad interna del exportador

Implementada. Se retiraron los helpers internos antiguos de medición, tablas y leyenda de `image_exporter.py`; sus consumidores y pruebas usan el compositor actual. `SlideRenderer` es la única fuente de composición para PNG/PDF/SVG, vista previa, portapapeles y visor. Las funciones de exportación vigentes y los formatos de preset/perfil se conservan; las importaciones directas de helpers internos retirados deben migrarse al renderer en la versión 0.3.0.

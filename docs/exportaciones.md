# Exportaciones PNG, PDF y SVG

[← Inicio](../README.md) · [Recorridos](recorrido.md) · [Personalización](personalizacion.md)

En **Exportar** elige PNG, PDF vectorial o SVG vectorial. Los tres formatos comparten la composición de la vista previa y son independientes del tamaño de la ventana. PDF conserva texto seleccionable; SVG permite editar los elementos en otras herramientas. No se generan PNG intermedios para los documentos vectoriales.

## Composición y legibilidad

**Cada paso ocupa una sola imagen horizontal 16:9**, preparada para un slideshow. Puedes elegir **1920 × 1080**, **2560 × 1440** o **3840 × 2160**, esquema de color independiente o **Como la interfaz**, y escala tipográfica de 0.8 a 1.5. PDF conserva una página horizontal por paso; PNG y SVG conservan un archivo por paso.

**Didáctico** incluye algoritmo, fase, iteración, número de paso y evento original, origen/destino, grafo, tablas, explicación, ruta y leyenda. **Composición y tipografía** permite añadir un título, ocultar explicación o leyenda y elegir **Grafo y tablas**, **Grafo destacado** o **Tablas destacadas**. Las tres distribuciones conservan el grafo y las tablas relevantes en la misma diapositiva. Dijkstra añade su tabla de distancias al elegir **Tablas destacadas**; en las otras distribuciones las distancias aparecen sobre el grafo.

Las listas se redistribuyen en columnas con encabezados y rangos de filas **dentro de la misma imagen**. Floyd-Warshall conserva completas sus matrices de distancias y recorridos, con todos los índices y resaltados originales. Bellman-Ford conserva todos los arcos ordenados, incluidos los dos sentidos de una conexión no dirigida. El compositor elige una distribución horizontal o vertical de los paneles y ajusta la escala para evitar solapamientos. La cámara del grafo y la composición permanecen fijas entre los pasos de una misma ejecución.

Los IDs largos reciben etiquetas abreviadas distintas entre sí. Las tablas usan las mismas etiquetas y una referencia en la misma diapositiva conserva los IDs completos. El título, la explicación, la ruta y los valores de las celdas ajustan su tipografía para conservar el texto completo sin puntos suspensivos adicionales. El manifiesto también registra la explicación original y los IDs completos.

La escala solicitada es una preferencia: al aumentar la cantidad de datos, el texto debe reducirse para mantener el paso completo en una imagen. No se garantiza un tamaño mínimo de letra para grafos arbitrariamente grandes. Para matrices densas, usa **4K**, revisa la vista previa al **100 %** y conserva el PDF/SVG vectorial para ampliar los detalles.

**Simple** muestra solo el grafo, pesos, flechas, IDs y resaltados, sin tablas ni explicaciones. Los dos estilos respetan **IDs de conexiones**; las tablas didácticas siempre conservan la identidad de los arcos. Los valores pequeños usan notación científica para conservar su signo. `∞` significa sin ruta, `−∞` sin mínimo finito y `—` sin predecesor.

![Una diapositiva completa de Floyd-Warshall: grafo y dos matrices de 30 por 30](images/floyd-30-matriz.png)

![Una diapositiva completa de Bellman-Ford: grafo, distancias y 126 arcos ordenados](images/bellman-30-tablas.png)

[Ejemplo PDF vectorial de Floyd-Warshall, con todos los datos en una página horizontal](images/floyd-30-diapositiva.pdf).

## Pasos y vista previa

- **Paso actual** exporta el evento exacto visible, incluso si se ha seleccionado resumen para el resto de la exportación.
- **Pasos separados** genera una diapositiva completa por cada estado seleccionado. PDF las reúne en un único documento.
- **Conjuntas** agrupa hasta dos o cuatro diapositivas completas en un lienzo horizontal mayor. Cada paso conserva su resolución: una conjunta de varias diapositivas HD mide **3840 × 2160**. La última puede contener menos pasos. Para presentar un paso por imagen, usa **Pasos separados**.
- **Resultado final** conserva el último estado de la ejecución completa, independientemente de los filtros de pasos.

Para pasos separados o conjuntas puedes seleccionar todos, un rango inclusivo, solo mejoras o pasos marcados. El rango corresponde al detalle elegido para exportar; las marcas identifican el evento original y sobreviven al cambio de detalle en la navegación. Los botones indican la cantidad real de archivos o páginas; cada estado tiene una sola diapositiva.

La vista previa está activada por defecto. Permite saltar a cualquier página, ir a la última y revisar a **50 %** o **100 %**, además de encajar al ancho. Renderiza hasta dos páginas cercanas a la posición elegida, sin generar toda la ejecución ni alterar el lienzo. Cancelar o cerrar la vista previa vuelve sin crear archivos. **Copiar imagen** copia la diapositiva completa del paso visible usando las opciones de exportación actuales.

## Archivos y cancelación

Cada operación publica una carpeta con fecha y hora. PDF se llama `diapositivas.pdf`; PNG y SVG usan nombres por paso, resultado o conjunta. No se generan archivos de continuación para un estado. En todos los formatos se incluyen:

| Archivo | Contenido |
| --- | --- |
| `manifest.json` | Opciones visuales, dimensiones, archivos/páginas, eventos originales, explicaciones completas y rutas consultadas |
| `grafo.json` | Preset con grafo, posiciones y ajustes de la ejecución para reproducirla |

Los archivos se preparan en una carpeta temporal y se publican al finalizar todas las escrituras. **Cancelar operación** elimina el trabajo parcial. Un fallo de escritura o de finalización del PDF/SVG se informa como error. El aviso de éxito permite abrir el destino real.

Las imágenes tienen un límite de 100 megapíxeles y las conjuntas un máximo de 12 000 px por lado. La cancelación se procesa entre páginas; una página en curso debe terminar de renderizarse. La ejecución detallada de Floyd-Warshall sigue generando muchos eventos: usa resumen, selección de pasos o resultado final cuando prepares material de grafos grandes.

## Exportar desde la terminal

```bash
uv run graph-visualizer \
  --export-preset src/graph_visualizer/examples/bellman_ford.json \
  --format pdf --kind final --theme print --resolution 3840 \
  --output-dir /tmp/material-grafo
```

Este modo no abre la ventana ni modifica los datos de trabajo. Usa el algoritmo y ajustes del preset; `--detail summary` o `--detail detailed` modifica el detalle de exportación. También admite `--kind all|combined|final`, `--format png|pdf|svg`, `--layout balanced|graph|tables`, `--font-scale` y `--simple`. Imprime la ruta resultante y devuelve un código distinto de cero si falla.

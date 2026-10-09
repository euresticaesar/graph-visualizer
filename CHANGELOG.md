# Cambios

## Sin publicar

- Pesos negativos en grafos no dirigidos al editar, guardar, cargar presets y convertir el tipo. Dijkstra y A* comparten su validación con la interfaz: Iniciar se deshabilita con una explicación visible; Bellman-Ford y Floyd-Warshall detectan los ciclos negativos y conservan los resultados no afectados.
- Corrección del desbordamiento horizontal de Exportar con DejaVu Sans a 18 px que fallaba en CI: etiquetas Diseño y texto / Vista previa y regresiones ejecutadas con la fuente del sistema y la de CI, conservando las comprobaciones de geometría.
- Composición adaptativa basada en la ocupación real de tablas: recupera el espacio sobrante para ampliar el grafo y respeta la prioridad de Grafo/Tablas destacadas. Las matrices inferiores aprovechan el ancho completo sin deformar letras ni cambiar las proporciones manuales; nuevas muestras y regresiones de A* y Floyd 30×30.
- Exportar reúne Detalle y Filtro en Seleccionar pasos, muestra Desde/Hasta solo para rangos y ajusta formularios y acciones al ancho del panel sin desplazamiento horizontal.
- Ayudas breves en todas las casillas, incluidas explicación, leyenda, atenuación, foco y vista previa; etiquetas más cortas para las opciones avanzadas.
- Lista de pasos marcados en Recorrido, con contador, navegación por teclado y acceso al evento exacto cuando una marca está oculta en resumen.
- Copiar imagen respeta el tema y acento actuales de la interfaz, conservando composición y resolución y el esquema independiente de los archivos exportados.
- Las diapositivas omiten por defecto los IDs de conexiones en grafo, tabla de arcos y explicación; conservan todos los arcos y su resaltado exacto. La opción de IDs permite mostrarlos en grafo y tabla.
- Explicaciones y foco con negritas y colores de contraste comprobado para contexto, cálculo, decisión y ruta; el tema Impresión conserva el énfasis en monocromo y el PDF sigue ofreciendo texto seleccionable.

## 0.3.0 — 2026-10-08

- Una diapositiva completa 16:9 por estado en PNG, PDF y SVG, con matrices y arcos íntegros, exportación atómica y cancelable, manifiesto y grafo reproducible.
- Composición adaptativa o manual, proporción del grafo, atenuación de conexiones, foco ampliado y diagnóstico de tamaños reales de fuente; opciones equivalentes en CLI.
- Vista previa íntegra con zoom y desplazamiento, visor a pantalla completa con pasos/fases/marcas, reproducción y teclado.
- Seis temas, incluido daltónico azul/naranja, cuatro layouts, perfiles visuales portables y offsets de etiquetas persistentes y deshacibles.
- Accesibilidad nativa, navegación de matrices, nuevos atajos y correcciones de esquinas de tablas y geometría del layout compacto.
- Pruebas de integridad y referencias visuales por regiones/celdas, CI con referencias obligatorias y muestras reproducibles actualizadas.
- Retirada de helpers internos antiguos del exportador; los consumidores usan `SlideRenderer`. Se mantienen los cuatro algoritmos existentes y la compatibilidad de presets y perfiles.

En diapositivas densas la letra se reduce para conservar todos los datos. 4K permite inspeccionar más píxeles, pero no garantiza lectura a distancia al proyectar la imagen completa. La validación automatizada de accesibilidad queda complementada por revisión manual con lectores de pantalla reales en cada plataforma.

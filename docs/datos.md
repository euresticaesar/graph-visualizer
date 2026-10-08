# Persistencia y compatibilidad

[← Inicio](../README.md) · [Configuración de rutas](instalacion.md) · [Presets](presets.md)

El trabajo sigue utilizando archivos UTF-8:

| Archivo | Contenido |
| --- | --- |
| `nodes.csv` | Encabezado `id`, una fila por nodo |
| `edges.csv` | `source,target,weight,id`; lectores aceptan también el formato antiguo sin `id` |
| `layout.json` | Objeto `{ "ID": { "x": número, "y": número } }` |
| `graph.json` | `{ "version": 1, "directed": false }` |
| `preferences.json` | Apariencia, distribución de paneles y opciones de exportación; independiente del grafo y los presets |

Sin `graph.json`, el grafo se interpreta como **no dirigido**. Los IDs numéricos antiguos se leen como strings sin pérdida; pesos, claves y coordenadas se conservan. No hace falta convertir manualmente los archivos: al editar se escribe el formato actual, con metadatos de tipo y escape CSV estándar para comas/comillas/saltos de línea. Las distancias se calculan con la precisión de los números Python; el formato visual usa hasta doce decimales sin ceros finales, o notación científica para magnitudes menores a `1e-6` o mayores o iguales a `1e9`. No interviene en comparaciones. Se detecta desbordamiento de sumas finitas y se informa como error.

Las escrituras del conjunto de archivos preparan copias anteriores y restauran los originales si falla un reemplazo. Si también falla la recuperación, el error indica dónde quedó la copia anterior. No es una base de datos transaccional frente a una interrupción abrupta del sistema; para respaldos duraderos exporta un preset.

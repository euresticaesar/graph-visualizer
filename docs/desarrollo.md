# Desarrollo y validación

[← Inicio](../README.md) · [Arquitectura](arquitectura.md)

Desde la raíz del repositorio, instala las dependencias de desarrollo:

```bash
uv sync --frozen --group dev
```

## Archivos del repositorio

Se versionan los archivos necesarios para ejecutar, validar y documentar la aplicación:

| Archivos | Motivo |
| --- | --- |
| `src/`, incluidos los cuatro presets JSON de `examples/` | Código y ejemplos incluidos en la distribución |
| `tests/` y `tests/fixtures/` | Pruebas, datos de entrada y referencias visuales revisadas |
| `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock` y `.python-version` | CI, configuración y dependencias reproducibles |
| `scripts/` | Regeneración reproducible de referencias y muestras |
| `README.md`, `CHANGELOG.md`, `docs/` y `demo_screenshot.png` | Documentación y evidencias visuales; los PNG/PDF son deliberados |
| `data/example/` | CSV y layout del ejemplo de arranque de 12 nodos usado en el checkout |
| `.gitignore` | Exclusión de archivos locales y generados |

`.gitignore` excluye el resto de `data/`, incluidos preferencias, presets personales, perfiles de presentación y temporales de escritura; también `output/`, entornos virtuales, paquetes de `dist/`, cachés, cobertura, configuración local de editores y metadatos del sistema. Los archivos `.env` locales se excluyen; las plantillas `.env.example` y `.env.sample` pueden versionarse si se añaden. La aplicación toma sus rutas de argumentos y variables de entorno; no carga archivos `.env` automáticamente.

Ignorar un archivo conserva su copia local y no retira archivos ya rastreados. Los JSON, CSV, PNG y PDF útiles no se excluyen globalmente: los ejemplos, fixtures y muestras deben seguir disponibles al clonar. Al usar un `--data-dir` o `--output-dir` distinto dentro del checkout, añade su ruta a `.git/info/exclude` para mantener esa configuración personal fuera de Git.

Antes de subir cambios, revisa:

```bash
git status --short --branch
git diff --check
git diff --cached --check
git ls-files --others --exclude-standard
git ls-files --cached --ignored --exclude-standard
```

La última orden detecta archivos rastreados que ahora coinciden con `.gitignore`. Debe quedar vacía en el estado actual. Ejecuta las comprobaciones siguientes cuando cambien código, dependencias o referencias; revisa los archivos de cada commit y conserva las muestras necesarias. Un árbol limpio indica que todos los cambios elegidos ya están committed; los archivos ignorados permanecen solo en el equipo. Hacer commit y hacer push son pasos independientes.

## Comprobaciones

```bash
QT_QPA_PLATFORM=offscreen uv run pytest -q
uv run ruff check .
uv run ruff format --check .
git diff --check
uv build
```

Las pruebas usan directorios temporales y cubren algoritmos frente a NetworkX, comparaciones, conexiones exactas, empates, estados inmutables, matrices, ciclos negativos, navegación, reproducción, edición, migración, recuperación de escrituras, presets e historial de ajustes, PNG/PDF/SVG, texto vectorial, cancelación, limpieza de exportaciones parciales, preferencias y contraste. Las exportaciones se verifican como una sola diapositiva horizontal por estado, con ambas matrices completas, todos los arcos, bloques sin solapamientos, explicación íntegra y resaltados en los índices originales. Los encabezados vacíos y las esquinas de tablas nativas y de matrices se comprueban en los seis temas. Las pruebas de presentación verifican el tamaño completo del pixmap, acceso al principio/final con zoom y redimensionamiento, ausencia de bucles de ajuste y separación de paneles en coordenadas comunes tras cambiar tamaño, algoritmo y layout.

La composición adaptativa de A* con 30 nodos se compara con un reparto lateral fijo para comprobar una ampliación efectiva del grafo, la conservación de todas las filas, la ausencia de franjas reservadas vacías y la estabilidad del plan entre estados. Floyd 30×30 comprueba las dos matrices completas, el ancho de la franja inferior y las proporciones manuales con escalas 0.8/1/1.5 y reservas 20/48/65 %; las composiciones con foco mantienen separación y proporción en ambos ejes.

Las marcas se prueban en los cuatro algoritmos, incluidas comparaciones tardías ocultas en resumen, acceso por teclado y sincronización con el visor. El portapapeles se comprueba con su imagen real en los seis temas y con acento personalizado. Las explicaciones de diapositivas se verifican por operandos, negritas, contraste mínimo 4.5:1, texto literal y tamaño real de fuente; se comprueba el PDF seleccionable y el resaltado exacto de arcos paralelos con IDs visibles u ocultos.

Los controles de Exportar se prueban con paneles de 310–520 px, fuente de 13 y 18 px, temas claro/oscuro y controles a izquierda/derecha o tablas inferiores. Estas combinaciones se ejecutan con la fuente del sistema y con **DejaVu Sans** explícita para cubrir las métricas de CI también en equipos que usan Noto Sans. Las opciones avanzadas y los rangos deben caber sin desplazamiento horizontal ni recorte de controles y mantener accesible el destino mediante desplazamiento vertical. Las ayudas nativas de todas las casillas se comprueban desde el arranque; los filtros preservan los eventos de Paso actual y Resultado final.

## Referencias visuales y CI

[`tests/render_reference.py`](../tests/render_reference.py) define cinco renders: A* de 30 nodos con composición adaptativa, matrices con resaltados, ciclo negativo, IDs largos con tema oscuro y escala 1.5, y tema daltónico con foco. Usa estilo **Fusion** y una sustitución de fuente **DejaVu Sans** solo durante estas comparaciones; restaura la fuente habitual al terminar. El manifiesto de [`tests/fixtures/render/`](../tests/fixtures/render/) registra Qt, familia, altura y ancho de una cadena de referencia. Actualmente corresponde a Qt **6.11.2** y DejaVu Sans, con altura **20.9375** y ancho **182.265625** a 18 px.

Las comparaciones exigen la misma geometría de regiones y celdas y una diferencia media absoluta de canales **RGBA ≤ 2** en cada región. Ante un fallo, guardan el render actual en el directorio temporal indicado por pytest. No se comparan capturas completas del escritorio entre sistemas. Las pruebas de integridad de matrices, arcos, texto PDF y geometría se ejecutan siempre.

En un equipo con otra versión de Qt o métricas de fuente, las cinco comparaciones de píxeles se omiten con el entorno esperado y el actual en el motivo. `.github/workflows/ci.yml` instala `fonts-dejavu-core`, usa el lock congelado y establece **`GV_REQUIRE_RENDER_REFERENCES=1`**: una discrepancia de entorno falla en CI en lugar de omitir las referencias. El workflow ejecuta sincronización, Ruff, pytest y build en Ubuntu/Python 3.12. Puedes ejecutar la misma exigencia localmente:

```bash
GV_REQUIRE_RENDER_REFERENCES=1 QT_QPA_PLATFORM=offscreen uv run pytest -q tests/test_render_regressions.py
```

Regenera referencias únicamente después de revisar un cambio legítimo del renderer o del entorno:

```bash
uv run python scripts/update_render_fixtures.py
```

Inspecciona las cinco imágenes, sus regiones y el diff del manifiesto antes de hacer commit. Actualizar referencias sin examinar un fallo puede ocultar una regresión; las tolerancias no se amplían para hacer pasar un cambio desconocido.

## Muestras de documentación

```bash
uv run python scripts/update_documentation_samples.py
```

El script usa directorios temporales y el preset de 30 nodos. Regenera tres diapositivas PNG 4K (Floyd adaptativo, Floyd con matrices inferiores y Bellman-Ford), el PDF horizontal de una página, A* inicial de 30 nodos en HD, la captura de Dijkstra del README y las capturas de vista previa y layout inferior compacto. Incluye una comparación del preset de Bellman-Ford de cinco vértices para ilustrar el énfasis de la explicación. Comprueba los 30 nodos, 63 conexiones, 126 arcos y ruta `1 → 10 → 27 → 666`, costo 10, y muestra tamaños efectivos de fuente. Las muestras de documentación utilizan la fuente del sistema y se revisan visualmente; no son referencias de píxeles entre entornos. No modifican el trabajo del usuario.

Para revisar candidatos antes de sustituir las muestras versionadas, usa `uv run python scripts/update_documentation_samples.py --output-dir /tmp/gv-muestras`. Mantiene los archivos existentes del repositorio y escribe las imágenes bajo `docs/images/` y la captura de escritorio en ese destino.

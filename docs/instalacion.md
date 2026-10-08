# Instalación y ejecución

[← Inicio](../README.md) · [Datos y rutas](datos.md)

Requiere **Python 3.12+**, **uv** y un entorno gráfico. Desde la raíz del repositorio:

```bash
uv sync --frozen
uv run graph-visualizer
```

También puedes usar `uv run python -m graph_visualizer`. El proyecto y comando se llaman `graph-visualizer`; el paquete importable es `graph_visualizer`.

Para trabajar con datos aislados:

```bash
uv run graph-visualizer --data-dir /tmp/mi-grafo --output-dir /tmp/mis-imagenes
```

El primer arranque de un directorio vacío crea el ejemplo de 12 nodos. Desde un checkout se conserva `data/` como directorio predeterminado de trabajo y `output/` para PNG/PDF/SVG. Una instalación de la distribución usa `$XDG_DATA_HOME/graph-visualizer` o `~/.local/share/graph-visualizer`. Las variables `GRAPH_VISUALIZER_DATA_DIR` y `GRAPH_VISUALIZER_OUTPUT_DIR` también permiten elegir las rutas, independientemente del directorio desde el que se lance el comando.

`uv.lock` y `.python-version` se incluyen en el repositorio; `--frozen` instala las versiones fijadas sin actualizar el lock. En el checkout, `data/example/` conserva los CSV y posiciones del ejemplo de arranque. El resto de `data/`, las exportaciones de `output/`, `.venv/` y los paquetes generados en `dist/` son archivos locales excluidos de Git.

PySide6 necesita un entorno gráfico. Para pruebas sin pantalla se utiliza `QT_QPA_PLATFORM=offscreen`; consulta la [guía de desarrollo](desarrollo.md).

La [exportación desde presets por terminal](exportaciones.md#exportar-desde-la-terminal) configura el modo offscreen automáticamente si no se ha elegido otro backend de Qt; no necesita abrir el espacio de trabajo.

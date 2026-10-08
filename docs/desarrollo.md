# Desarrollo y validación

[← Inicio](../README.md) · [Arquitectura](arquitectura.md)

Desde la raíz del repositorio, instala las dependencias de desarrollo:

```bash
uv sync --group dev
```

## Comprobaciones

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

Las pruebas usan directorios temporales y cubren algoritmos frente a NetworkX, comparaciones, conexiones exactas, empates, estados inmutables, matrices, ciclos negativos, navegación, reproducción, edición, migración, recuperación de escrituras, presets e historial de ajustes, PNG/PDF/SVG, texto vectorial, cancelación, limpieza de exportaciones parciales, preferencias y contraste. Las exportaciones se verifican como una sola diapositiva horizontal por estado, con ambas matrices completas, todos los arcos, bloques sin solapamientos, explicación íntegra y resaltados en los índices originales. Los encabezados vacíos y las esquinas de tablas nativas y de matrices se comprueban en los cinco temas. La revisión visual debe complementar estas pruebas, especialmente al cambiar estilos o distribuciones de paneles.

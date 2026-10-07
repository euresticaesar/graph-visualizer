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

Las pruebas usan directorios temporales y cubren algoritmos frente a NetworkX, comparaciones, conexiones exactas, empates, estados inmutables, matrices, ciclos negativos, navegación, reproducción, edición, migración, recuperación de escrituras, presets, PNG y división de composiciones. La revisión visual debe complementar estas pruebas, especialmente al cambiar estilos o distribuciones de paneles.

import os
import tempfile
from pathlib import Path


def atomic_write_files(contents: dict[Path, str]) -> None:
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path | None] = {}
    replaced: list[Path] = []
    recovery_files: set[Path] = set()

    def stage(path: Path, data: bytes) -> Path:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(data)
        except OSError:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            raise
        return temporary

    try:
        # Prepara todos los archivos antes de reemplazar cualquiera de los originales.
        for path, content in contents.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            backups[path] = stage(path, path.read_bytes()) if path.exists() else None
            staged[path] = stage(path, content.encode("utf-8"))
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
    except OSError as error:
        # Si falla un reemplazo, recupera los archivos que ya se habían cambiado.
        failures = []
        for path in reversed(replaced):
            backup = backups[path]
            try:
                if backup is None:
                    path.unlink(missing_ok=True)
                else:
                    os.replace(backup, path)
            except OSError:
                if backup is not None:
                    recovery_files.add(backup)
                failures.append(f"{path}. Copia anterior: {backup or 'archivo nuevo'}")
        if failures:
            raise OSError(
                "No se pudieron restaurar estos archivos:\n" + "\n".join(failures)
            ) from error
        raise
    finally:
        for temporary in [*staged.values(), *backups.values()]:
            if temporary is not None and temporary not in recovery_files:
                temporary.unlink(missing_ok=True)

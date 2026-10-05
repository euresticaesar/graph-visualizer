import os
import tempfile
from pathlib import Path


def atomic_write_files(contents: dict[Path, str]) -> None:
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path | None] = {}
    replaced: list[Path] = []

    def stage(path: Path, data: bytes) -> Path:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(data)
            except OSError:
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
    except OSError:
        # Si falla un reemplazo, recupera los archivos que ya se habían cambiado.
        for path in reversed(replaced):
            if backups[path] is None:
                path.unlink(missing_ok=True)
            else:
                os.replace(backups[path], path)
        raise
    finally:
        for temporary in [*staged.values(), *backups.values()]:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

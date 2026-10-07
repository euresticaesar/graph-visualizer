import math
from collections.abc import Iterable
from itertools import chain

from PySide6.QtGui import QColor, QImage, QPainter


def combine_phases(images: Iterable[QImage], count: int) -> QImage:
    if count < 1:
        raise ValueError("La imagen conjunta necesita al menos un paso.")
    iterator = iter(images)
    first = next(iterator, None)
    if first is None or first.isNull():
        raise ValueError("La imagen conjunta necesita al menos una imagen de un paso válido.")
    columns = min(3, math.ceil(math.sqrt(count)))
    rows = math.ceil(count / columns)
    gap = 20
    width = columns * first.width() + (columns + 1) * gap
    height = rows * first.height() + (rows + 1) * gap
    if width * height > 100_000_000:
        raise ValueError("Hay demasiados pasos para una sola imagen. Expórtalos por separado.")
    combined = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    if combined.isNull():
        raise ValueError("No hay memoria suficiente para generar la imagen conjunta.")
    combined.fill(QColor("#dce3ed"))
    painter = QPainter(combined)
    try:
        actual_count = 0
        for index, image in enumerate(chain([first], iterator)):
            if index >= count or image.size() != first.size():
                raise ValueError("Los pasos deben tener el mismo tamaño y la cantidad esperada.")
            x = gap + (index % columns) * (first.width() + gap)
            y = gap + (index // columns) * (first.height() + gap)
            painter.drawImage(x, y, image)
            actual_count += 1
        if actual_count != count:
            raise ValueError("La cantidad de pasos generados no coincide con la esperada.")
    finally:
        painter.end()
    return combined

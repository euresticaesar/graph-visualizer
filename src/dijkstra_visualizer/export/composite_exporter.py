import math
from collections.abc import Iterable
from itertools import chain

from PySide6.QtGui import QColor, QImage, QPainter


def combine_phases(images: Iterable[QImage], count: int) -> QImage:
    if count < 1:
        raise ValueError("A combined image needs at least one phase.")
    iterator = iter(images)
    first = next(iterator)
    columns = min(3, math.ceil(math.sqrt(count)))
    rows = math.ceil(count / columns)
    gap = 20
    width = columns * first.width() + (columns + 1) * gap
    height = rows * first.height() + (rows + 1) * gap
    if width * height > 100_000_000:
        raise ValueError("Too many phases for one image. Export individual phases instead.")
    combined = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    if combined.isNull():
        raise ValueError("The combined image is too large to allocate.")
    combined.fill(QColor("#dce3ed"))
    painter = QPainter(combined)
    try:
        actual_count = 0
        for index, image in enumerate(chain([first], iterator)):
            if index >= count or image.size() != first.size():
                raise ValueError("Combined phases must have the same size and expected count.")
            x = gap + (index % columns) * (first.width() + gap)
            y = gap + (index // columns) * (first.height() + gap)
            painter.drawImage(x, y, image)
            actual_count += 1
        if actual_count != count:
            raise ValueError("The number of rendered phases does not match the expected count.")
    finally:
        painter.end()
    return combined

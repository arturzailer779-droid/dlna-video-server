import sys
from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtGui import QColor, QImage, QPainter

src = QImage(sys.argv).convertToFormat(QImage.Format.Format_ARGB32)

def encode_png(size):
    im = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    im.save(buf, "PNG")
    return bytes(buf.data())

def encode_jpg(size):
    im = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    bg = QImage(size, size, QImage.Format.Format_RGB888)
    bg.fill(QColor(24, 24, 27))
    p = QPainter(bg)
    p.drawImage((size - im.width()) // 2, (size - im.height()) // 2, im)
    p.end()
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    bg.save(buf, "JPG", 92)
    return bytes(buf.data())

items = [
    ("png_sm", encode_png(48)),
    ("png_lrg", encode_png(120)),
    ("jpeg_sm", encode_jpg(48)),
    ("jpeg_lrg", encode_jpg(120)),
]

for name, data in items:
    arr = ", ".join(f"0x{b:02x}" for b in data)
    print(f"unsigned char {name}[] = {{{arr}}};")

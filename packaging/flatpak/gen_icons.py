import sys
from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtGui import QColor, QImage, QPainter

src = QImage(sys.argv[1])

def encode(size, fmt):
    im = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    if fmt == "JPG":
        bg = QImage(size, size, QImage.Format.Format_RGB32)
        bg.fill(QColor(255, 255, 255))
        p = QPainter(bg)
        p.drawImage(0, 0, im)
        p.end()
        im = bg
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    im.save(buf, fmt, 90)
    return bytes(buf.data())

items = [
    ("png_sm", encode(48, "PNG")),
    ("png_lrg", encode(120, "PNG")),
    ("jpeg_sm", encode(48, "JPG")),
    ("jpeg_lrg", encode(120, "JPG")),
]

for name, data in items:
    arr = ", ".join(f"0x{b:02x}" for b in data)
    print(f"unsigned char {name}[] = {{{arr}}};")

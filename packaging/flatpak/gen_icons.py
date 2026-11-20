import sys
from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtGui import QColor, QImage, QPainter

src = QImage(sys.argv[1])

def encode_opaque(size, fmt):
    im = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    bg = QImage(size, size, QImage.Format.Format_RGB32)
    bg.fill(QColor(30, 41, 59))
    p = QPainter(bg)
    p.drawImage((size - im.width()) // 2, (size - im.height()) // 2, im)
    p.end()
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    bg.save(buf, fmt, 95)
    return bytes(buf.data())

for sz in (512, 64):
    p = f"data/icons/{sz}x{sz}/io.github.arturzailer779_droid.dlna-video-server.png"
    src.scaled(sz, sz, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation).save(p, "PNG")

items = [
    ("png_sm", encode_opaque(48, "PNG")),
    ("png_lrg", encode_opaque(120, "PNG")),
    ("jpeg_sm", encode_opaque(48, "JPG")),
    ("jpeg_lrg", encode_opaque(120, "JPG")),
]

for name, data in items:
    arr = ", ".join(f"0x{b:02x}" for b in data)
    print(f"unsigned char {name}[] = {{{arr}}};")

# D:\Documents\test_period.py
import sys, os
from PyQt6.QtWidgets import QApplication, QDialog, QWidget
from PyQt6.uic import loadUi

from client.core.themes import T, apply_theme_to_widget
from client.core.themes.manager import _PLACEHOLDER_RE


app = QApplication(sys.argv)
print("App stylesheet BEFORE:", repr(app.styleSheet()))

d = QDialog()
loadUi("client/ui/period_dialog.ui", d)
print("\n=== BEFORE apply ===")
print("dialog SS:", repr(d.styleSheet()[:200]))

apply_theme_to_widget(d)

print("\n=== AFTER apply ===")
print("dialog SS:", repr(d.styleSheet()[:200]))
print("applyButton SS:", repr(d.findChild(QWidget, 'applyButton').styleSheet()[:200]))
print("startDateEdit SS:", repr(d.findChild(QWidget, 'startDateEdit').styleSheet()[:200]))

# Ищем остатки плейсхолдеров:
rest = _PLACEHOLDER_RE.findall(d.styleSheet())
print("\nОстатки плейсхолдеров в dialog SS:", rest)

# Ищем внутри .ui вообще всё, что похоже на {XXX}
import re
with open("client/ui/period_dialog.ui", encoding="utf-8") as f:
    content = f.read()
all_braces = re.findall(r"\{[^}]*\}", content)
print("\nВсе {…} в .ui (первые 20):")
for b in all_braces[:20]:
    print("  ", b)

print("\nApp stylesheet AFTER:", repr(app.styleSheet()))
print("app.styleSheet() пустой?", app.styleSheet() == "")

d.show()
app.exec()
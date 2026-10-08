"""
Заменяет зашитые цвета полос прокрутки в styleSheet виджета scrollArea на токены темы.

Почему это нужно: собственный styleSheet у scrollArea перекрывает стили самого диалога,
поэтому полосы прокрутки остаются светлыми в тёмной теме. Для стандартной темы значения
токенов совпадают с прежними цветами, так что светлая тема выглядит как раньше.

Запуск:  python fix_ui_scrollbar_tokens.py client/ui/system/employees/employee_dialog.ui [ещё.ui ...]
Рядом с каждым файлом создаётся резервная копия .bak.
"""

import re
import shutil
import sys

REPLACEMENTS = {
    "#F5F5F5": "{SCROLLBAR_BG}",
    "#C1C1C1": "{SCROLLBAR_HANDLE}",
    "#A0A0A0": "{SCROLLBAR_HANDLE_HOVER}",
    "#888888": "{SCROLLBAR_HANDLE_PRESSED}",
}

# styleSheet именно виджета scrollArea: от его <widget ...> до закрывающего </string> первого styleSheet
BLOCK_RE = re.compile(
    r'(<widget class="QScrollArea" name="scrollArea">\s*<property name="styleSheet">\s*<string[^>]*>)(.*?)(</string>)',
    re.DOTALL,
)


def fix_text(text: str) -> tuple[str, int]:
    count = 0

    def repl(match):
        nonlocal count
        head, body, tail = match.groups()
        for old, new in REPLACEMENTS.items():
            body, n = re.subn(re.escape(old), new, body, flags=re.IGNORECASE)
            count += n
        return head + body + tail

    return BLOCK_RE.sub(repl, text, count=1), count


def main(paths):
    for path in paths:
        with open(path, "rb") as f:
            raw = f.read().decode("utf-8")
        fixed, count = fix_text(raw)
        if count == 0:
            print(f"{path}: зашитых цветов в scrollArea не найдено — без изменений")
            continue
        shutil.copyfile(path, path + ".bak")
        with open(path, "wb") as f:
            f.write(fixed.encode("utf-8"))
        print(f"{path}: заменено цветов — {count} (копия: {path}.bak)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])

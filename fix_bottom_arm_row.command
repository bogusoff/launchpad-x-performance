#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_DIR="$PROJECT_DIR/src/Launchpad_X_performance"
INIT_FILE="$SCRIPT_DIR/__init__.py"
BACKUP_DIR="$PROJECT_DIR/backups/arm_bottom_row_$(date +%Y%m%d_%H%M%S)"

echo
echo "Launchpad X Performance — restore bottom Arm row"
echo "================================================"
echo

if [ ! -f "$INIT_FILE" ] || [ ! -f "$PROJECT_DIR/install.command" ]; then
    echo "Ошибка: положи этот файл в корень проекта:"
    echo "$HOME/projects/Launchpad_X_performance"
    exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$INIT_FILE" "$BACKUP_DIR/__init__.py"

python3 - "$INIT_FILE" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

old = (
    "    # Нижние два физических ряда исходной Session-матрицы.\n"
    "    fixed_length_matrix = clip_matrix.submatrix[\n"
    "        slice(None),\n"
    "        slice(6, 8),\n"
    "    ]\n"
)

new = (
    "    # Физические ряды 6 и 7 используются для Fixed Length.\n"
    "    # Нижний физический ряд 8 остаётся штатным Arm дорожек.\n"
    "    fixed_length_matrix = clip_matrix.submatrix[\n"
    "        slice(None),\n"
    "        slice(5, 7),\n"
    "    ]\n"
)

if old not in text:
    raise SystemExit(
        "Ошибка: ожидаемый блок fixed_length_matrix не найден. "
        "Файл не изменён."
    )

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
PY

python3 -m py_compile "$INIT_FILE"
rm -rf "$SCRIPT_DIR/__pycache__"

echo "Матрица исправлена:"
echo "  физический ряд 6 — Fixed Length 1–8"
echo "  физический ряд 7 — Fixed Length 9–16"
echo "  физический ряд 8 — штатный Arm"
echo
echo "Запускаю штатный install.command..."
echo

chmod +x "$PROJECT_DIR/install.command"
"$PROJECT_DIR/install.command"

echo
echo "Готово. Полностью закрой Ableton через Cmd+Q и открой снова."
echo
read -r -p "Нажми Enter, чтобы закрыть окно..."

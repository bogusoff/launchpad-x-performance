#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_DIR="$PROJECT_DIR/src/Launchpad_X_performance"
COMPONENT="$SCRIPT_DIR/fixed_length_component.py"
MANAGER="$SCRIPT_DIR/fixed_length_manager.py"
BACKUP_DIR="$PROJECT_DIR/backups/arm_mode_$(date +%Y%m%d_%H%M%S)"

echo
echo "Launchpad X Performance — Fixed Length in Arm"
echo "============================================="
echo

for file in "$COMPONENT" "$MANAGER" "$PROJECT_DIR/install.command"; do
    if [ ! -f "$file" ]; then
        echo "Ошибка: не найден файл:"
        echo "$file"
        echo
        echo "Положи установщик в корень проекта:"
        echo "$HOME/projects/Launchpad_X_performance"
        exit 1
    fi
done

if ! command -v python3 >/dev/null 2>&1; then
    echo "Ошибка: команда python3 не найдена."
    exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$COMPONENT" "$BACKUP_DIR/fixed_length_component.py"
cp "$MANAGER" "$BACKUP_DIR/fixed_length_manager.py"

echo "Резервная копия:"
echo "$BACKUP_DIR"
echo

python3 - "$COMPONENT" "$MANAGER" <<'PY'
from pathlib import Path
import sys

component_path = Path(sys.argv[1])
manager_path = Path(sys.argv[2])

component = component_path.read_text(encoding="utf-8")
manager = manager_path.read_text(encoding="utf-8")

old_doc = """    Физический порядок:
    - нижний ряд: 1–8;
    - ряд над ним: 9–16.
"""
new_doc = """    Физический порядок:
    - верхний ряд: 1–8;
    - ряд под ним: 9–16;
    - нижний ряд Launchpad: штатный Arm дорожек.
"""

old_mapping = """    def _bars_for_button_index(self, index):
        # submatrix перечисляет сначала ряд 6, затем ряд 7.
        # Нам нужен обратный музыкальный порядок:
        # ряд 7 = 1–8, ряд 6 = 9–16.
        if index < 8:
            return index + 9

        return index - 7
"""

new_mapping = """    def _bars_for_button_index(self, index):
        # submatrix перечисляет сначала верхний ряд,
        # затем расположенный под ним ряд:
        # верхний ряд = 1–8;
        # следующий ряд = 9–16.
        return index + 1
"""

old_manager_doc = """    Overlay включён только при:
    Main Mode = Session
    Session Mode = Mixer
    Mixer Mode = Pan

    Штатные Pan-фейдеры при этом отключаются.
"""

new_manager_doc = """    Fixed Length включён только при:
    Main Mode = Session
    Session Mode = Mixer
    Mixer Mode = Arm

    Два ряда используются для выбора длины записи.
    Нижний ряд продолжает управлять Arm дорожек.
"""

old_refresh = """    def _refresh(self):
        overlay_enabled = self._overlay_should_be_enabled()
        if overlay_enabled:
            # Режим Pan уже успел захватить фейдеры.
            # Освобождаем их, чтобы нажатия не меняли панораму.
            self._surface._mixer.set_pan_controls(None)
            self._surface._mixer.set_track_color_controls(None)

            # Возвращаем сетку из Faders layout в Session layout.
            self._surface._session_layout_mode()

        self._component.set_enabled(overlay_enabled)
"""

new_refresh = """    def _refresh(self):
        overlay_enabled = self._overlay_should_be_enabled()

        if overlay_enabled:
            # Возвращаем сетку из возможного Faders layout
            # в обычный Session layout.
            self._surface._session_layout_mode()

        self._component.set_enabled(overlay_enabled)
"""

replacements = [
    ("описание раскладки", old_doc, new_doc, component_path),
    ("порядок значений 1–16", old_mapping, new_mapping, component_path),
    ("описание режима Arm", old_manager_doc, new_manager_doc, manager_path),
]

for label, old, new, path in replacements:
    text = component if path == component_path else manager
    if old not in text:
        raise SystemExit(
            f"Ошибка: не найден ожидаемый участок «{label}» в {path.name}. "
            "Файлы не изменены полностью; восстанови их из резервной копии."
        )
    text = text.replace(old, new, 1)
    if path == component_path:
        component = text
    else:
        manager = text

if 'selected_mode == "pan"' not in manager:
    raise SystemExit(
        'Ошибка: в fixed_length_manager.py не найден режим "pan".'
    )

manager = manager.replace(
    'self._surface._mixer_modes.selected_mode == "pan"',
    'self._surface._mixer_modes.selected_mode == "arm"',
    1,
)

if old_refresh not in manager:
    raise SystemExit(
        "Ошибка: не найден ожидаемый блок _refresh()."
    )

manager = manager.replace(old_refresh, new_refresh, 1)

component_path.write_text(component, encoding="utf-8")
manager_path.write_text(manager, encoding="utf-8")
PY

python3 -m py_compile "$COMPONENT" "$MANAGER"
rm -rf "$SCRIPT_DIR/__pycache__"

echo "Изменения внесены и синтаксис проверен."
echo
echo "Раскладка Mixer → Arm:"
echo "  верхний ряд    — 1–8 тактов"
echo "  следующий ряд  — 9–16 тактов"
echo "  нижний ряд     — штатный Arm"
echo
echo "Запускаю штатный install.command..."
echo

chmod +x "$PROJECT_DIR/install.command"
"$PROJECT_DIR/install.command"

echo
echo "Готово. Полностью закрой Ableton через Cmd+Q и открой снова."
echo
read -r -p "Нажми Enter, чтобы закрыть окно..."

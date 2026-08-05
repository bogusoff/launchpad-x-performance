#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_DIR="$PROJECT_DIR/src/Launchpad_X_performance"
COMPONENT="$SCRIPT_DIR/fixed_length_component.py"
MANAGER="$SCRIPT_DIR/fixed_length_manager.py"
BACKUP_DIR="$PROJECT_DIR/backups/arm_mode_$(date +%Y%m%d_%H%M%S)"

echo
echo "Launchpad X Performance — Fixed Length in Arm v2"
echo "================================================"
echo

for file in "$COMPONENT" "$MANAGER" "$PROJECT_DIR/install.command"; do
    if [ ! -f "$file" ]; then
        echo "Ошибка: не найден файл:"
        echo "$file"
        exit 1
    fi
done

mkdir -p "$BACKUP_DIR"
cp "$COMPONENT" "$BACKUP_DIR/fixed_length_component.py"
cp "$MANAGER" "$BACKUP_DIR/fixed_length_manager.py"

echo "Резервная копия:"
echo "$BACKUP_DIR"
echo

python3 - "$COMPONENT" "$MANAGER" <<'PY'
from pathlib import Path
import re
import sys

component_path = Path(sys.argv[1])
manager_path = Path(sys.argv[2])

component = component_path.read_text(encoding="utf-8")
manager = manager_path.read_text(encoding="utf-8")

mapping_pattern = re.compile(
    r"    def _bars_for_button_index\(self, index\):\n"
    r"(?:        .*\n)+?"
    r"        if index < 8:\n"
    r"            return index \+ 9\n"
    r"\n"
    r"        return index - 7\n"
)

new_mapping = (
    "    def _bars_for_button_index(self, index):\n"
    "        # submatrix перечисляет сначала верхний ряд,\n"
    "        # затем расположенный под ним ряд:\n"
    "        # верхний ряд = 1–8;\n"
    "        # следующий ряд = 9–16.\n"
    "        return index + 1\n"
)

component, count = mapping_pattern.subn(new_mapping, component, count=1)

if count != 1:
    raise SystemExit(
        "Ошибка: не удалось найти функцию _bars_for_button_index()."
    )

component = component.replace(
    "    Физический порядок:\n"
    "    - нижний ряд: 1–8;\n"
    "    - ряд над ним: 9–16.\n",
    "    Физический порядок:\n"
    "    - верхний ряд: 1–8;\n"
    "    - ряд под ним: 9–16;\n"
    "    - нижний ряд Launchpad: штатный Arm дорожек.\n",
    1,
)

if 'self._surface._mixer_modes.selected_mode == "pan"' not in manager:
    raise SystemExit('Ошибка: режим "pan" не найден.')

manager = manager.replace(
    'self._surface._mixer_modes.selected_mode == "pan"',
    'self._surface._mixer_modes.selected_mode == "arm"',
    1,
)

manager = manager.replace(
    "    Overlay включён только при:\n"
    "    Main Mode = Session\n"
    "    Session Mode = Mixer\n"
    "    Mixer Mode = Pan\n"
    "\n"
    "    Штатные Pan-фейдеры при этом отключаются.\n",
    "    Fixed Length включён только при:\n"
    "    Main Mode = Session\n"
    "    Session Mode = Mixer\n"
    "    Mixer Mode = Arm\n"
    "\n"
    "    Два ряда используются для выбора длины записи.\n"
    "    Нижний ряд продолжает управлять Arm дорожек.\n",
    1,
)

old_pan_block = (
    "        if overlay_enabled:\n"
    "            # Режим Pan уже успел захватить фейдеры.\n"
    "            # Освобождаем их, чтобы нажатия не меняли панораму.\n"
    "            self._surface._mixer.set_pan_controls(None)\n"
    "            self._surface._mixer.set_track_color_controls(None)\n"
    "\n"
    "            # Возвращаем сетку из Faders layout в Session layout.\n"
    "            self._surface._session_layout_mode()\n"
)

new_arm_block = (
    "        if overlay_enabled:\n"
    "            # Возвращаем сетку из возможного Faders layout\n"
    "            # в обычный Session layout.\n"
    "            self._surface._session_layout_mode()\n"
)

if old_pan_block not in manager:
    raise SystemExit("Ошибка: не найден Pan-блок в _refresh().")

manager = manager.replace(old_pan_block, new_arm_block, 1)

if 'selected_mode == "arm"' not in manager:
    raise SystemExit("Ошибка проверки: режим Arm не установлен.")

if "return index + 1" not in component:
    raise SystemExit("Ошибка проверки: порядок 1–16 не изменён.")

if "set_pan_controls(None)" in manager:
    raise SystemExit("Ошибка проверки: Pan-контролы всё ещё отключаются.")

component_path.write_text(component, encoding="utf-8")
manager_path.write_text(manager, encoding="utf-8")
PY

python3 -m py_compile "$COMPONENT" "$MANAGER"
rm -rf "$SCRIPT_DIR/__pycache__"

echo "Патч успешно применён."
echo
echo "Mixer → Arm:"
echo "  верхний ряд    — 1–8 тактов"
echo "  следующий ряд  — 9–16 тактов"
echo "  нижний ряд     — штатный Arm"
echo
echo "Запускаю штатный install.command..."
echo

chmod +x "$PROJECT_DIR/install.command"
"$PROJECT_DIR/install.command"

echo
echo "Готово. Закрой Ableton через Cmd+Q и открой снова."
echo
read -r -p "Нажми Enter, чтобы закрыть окно..."

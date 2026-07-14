# Launchpad X Performance

Performance-oriented Remote Script for **Novation Launchpad X** and **Ableton Live 12**.

---

## 🇷🇺 О проекте

**Launchpad X Performance** — альтернативный Remote Script для живых выступлений и Live Looping в Ableton Live.

Проект сохраняет привычную логику оригинального Launchpad X и добавляет несколько функций, которых мне не хватало во время выступлений:

- квантованная остановка клипа повторным нажатием;
- остановка сцены удержанием;
- запись клипов фиксированной длины;
- безопасное удаление клипа удержанием.

Скрипт не заменяет оригинальный Launchpad X и не изменяет его файлы. Все дополнительные функции работают только тогда, когда в Ableton Live выбран Control Surface `Launchpad_X_performance`.

В любой момент можно вернуться к штатному `Launchpad X`.

## 🇬🇧 About

**Launchpad X Performance** is an alternative Remote Script for live performance and live looping in Ableton Live.

The project preserves the familiar workflow of the original Launchpad X while adding several features that I needed during live performance:

- quantized clip stop with a second press;
- scene stop by holding the Scene button;
- fixed-length clip recording;
- safe clip deletion by holding the clip button.

The script does not replace or modify the original Launchpad X files. All additional features are active only when `Launchpad_X_performance` is selected as the Control Surface in Ableton Live.

You can switch back to the official `Launchpad X` script at any time.

---

## 🎥 Демонстрация / Demo

https://youtu.be/iwC-g0I7ADQ?si=ZVzq5mLxWfpZIt2y

---

# Возможности / Features

## Quantized Clip Stop

### 🇷🇺

Повторное нажатие на играющий клип ставит его в очередь на остановку.

Остановка выполняется по **Global Quantization** Ableton Live. Во время ожидания кнопка клипа получает красную индикацию.

Это позволяет заранее подготовить переход и не пытаться попасть в нужный момент вручную.

![Quantized Clip Stop](docs/gifs/quantized_clip_stop.gif)

### 🇬🇧

Pressing a playing clip a second time queues it for stopping.

The clip stops according to Ableton Live's **Global Quantization**. While the stop is pending, the clip button shows a red indication.

This makes it possible to prepare transitions in advance without trying to press the button at the exact musical boundary.

---

## Scene Hold Stop

### 🇷🇺

Удержание кнопки сцены ставит на остановку играющие клипы соответствующей строки.

Остановка выполняется по **Global Quantization** Ableton Live.

Короткое нажатие продолжает работать штатно и запускает сцену. Поэтому привычная логика Launchpad X не меняется.

![Scene Hold Stop](docs/gifs/scene_hold_stop.gif)

### 🇬🇧

Holding a Scene Launch button queues the playing clips in that scene for stopping.

The clips stop according to Ableton Live's **Global Quantization**.

A short press keeps the original behavior and launches the scene. The familiar Launchpad X workflow therefore remains unchanged.

---

## Fixed Length Recording

### 🇷🇺

Перед записью можно выбрать фиксированную длину нового клипа.

Доступные значения от 1 до 16 тактов

Выбранная длина сохраняется между входами в режим. Режим также показывает, включена ли фиксированная длина и какое значение выбрано в данный момент.

После запуска записи в пустом слоте на вооружённой дорожке Ableton автоматически завершает запись по достижении выбранной длины.

![Fixed Length Recording](docs/gifs/fixed_length_recording.gif)

### 🇬🇧

A fixed length can be selected before recording a new clip.

Available values 1 - 16 bars

The selected length is preserved between mode changes. The mode also shows whether fixed-length recording is enabled and which length is currently selected.

When recording is launched in an empty slot on an armed track, Ableton automatically finishes the recording after the selected length.

---

## Long Press Clip Delete

### 🇷🇺

Клип можно удалить удержанием его кнопки на вооружённой дорожке.

Короткое нажатие сохраняет обычное поведение клипа. Удаление выполняется только после удержания, что снижает вероятность случайно удалить материал во время выступления.

После удаления кнопка кратко показывает красную индикацию.

![Long Press Clip Delete](docs/gifs/long_press_delete.gif)

### 🇬🇧

A clip can be deleted by holding its button on an armed track.

A short press keeps the normal clip behavior. Deletion occurs only after the button has been held, reducing the risk of accidentally deleting material during a performance.

After deletion, the button briefly shows a red indication.

---

## Fixed Length: управление / Fixed Length: controls

### 🇷🇺

Чтобы открыть режим фиксированной длины:

```text
Mixer
↓
Pan
↓
Fixed Length
```

Повторное нажатие `Pan` закрывает режим и возвращает обычный Session View.

После выбора длины режим остаётся открытым. Это позволяет проверить текущее состояние, изменить длину или выключить Fixed Length перед возвращением в Session View.

Фейдеры панорамы в этом режиме отключены, чтобы случайное нажатие не изменило микс во время выступления.

### 🇬🇧

To open Fixed Length mode:

```text
Mixer
↓
Pan
↓
Fixed Length
```

Press `Pan` again to close the mode and return to the regular Session View.

The mode remains open after selecting a length. This makes it possible to confirm the current state, change the selected length, or disable Fixed Length before returning to Session View.

The Pan faders are disabled in this mode so accidental presses cannot change the mix during a performance.

---

## Настройка времени удержания / Hold-time configuration

### 🇷🇺

Время удержания для остановки сцены и удаления клипа можно изменить в файле:

```text
src/Launchpad_X_performance/__init__.py
```

Настройки находятся в начале файла:

```python
SCENE_HOLD_SECONDS = 0.7
CLIP_DELETE_HOLD_SECONDS = 0.7
```

Увеличьте значения, если функции срабатывают слишком легко.

Уменьшите значения, если требуется более быстрое управление во время выступления.

Комфортный диапазон обычно находится между:

```text
0.5–2.0 секунды
```

### 🇬🇧

The hold time for Scene Stop and Clip Delete can be changed in:

```text
src/Launchpad_X_performance/__init__.py
```

The settings are located near the beginning of the file:

```python
SCENE_HOLD_SECONDS = 0.7
CLIP_DELETE_HOLD_SECONDS = 0.7
```

Increase the values if the functions trigger too easily.

Decrease the values if faster access is preferred during performance.

A comfortable range is usually:

```text
0.5–2.0 seconds
```

---

## Совместимость / Compatibility

| Платформа / Platform | Статус / Status |
|---|---|
| Novation Launchpad X | ✅ |
| Ableton Live 12 | ✅ |
| macOS | ✅ |
| Windows 11 | ✅ |

### 🇷🇺

Версия `v1.1.0` протестирована на:

- Ableton Live 12.4.2 — macOS;
- Ableton Live 12.4.1 — Windows 11 25H2.

### 🇬🇧

Version `v1.1.0` has been tested with:

- Ableton Live 12.4.2 on macOS;
- Ableton Live 12.4.1 on Windows 11 25H2.

---

# Установка / Installation

## macOS

### 🇷🇺

Запустите:

```text
install.command
```

При необходимости разрешите выполнение файла в настройках безопасности macOS.

После установки полностью перезапустите Ableton Live.

### 🇬🇧

Run:

```text
install.command
```

If necessary, allow the file to run in the macOS security settings.

Restart Ableton Live completely after installation.

---

## Windows

### 🇷🇺

Запустите:

```text
install_windows.bat
```

Установщик предложит стандартное расположение Ableton User Library или позволит указать другой путь.

После установки полностью перезапустите Ableton Live.

### 🇬🇧

Run:

```text
install_windows.bat
```

The installer will offer the standard Ableton User Library location or allow you to enter another path.

Restart Ableton Live completely after installation.

---

## Настройка Ableton Live / Ableton Live setup

### 🇷🇺

После установки откройте:

```text
Settings
→ Link, Tempo & MIDI
```

Выберите:

```text
Control Surface:
Launchpad_X_performance

Input:
Launchpad X DAW In

Output:
Launchpad X DAW Out
```

Названия MIDI-портов могут немного отличаться в зависимости от операционной системы.

### 🇬🇧

After installation, open:

```text
Settings
→ Link, Tempo & MIDI
```

Select:

```text
Control Surface:
Launchpad_X_performance

Input:
Launchpad X DAW In

Output:
Launchpad X DAW Out
```

The MIDI port names may vary slightly depending on the operating system.

---

## Возврат к штатному скрипту / Returning to the official script

### 🇷🇺

Чтобы вернуться к оригинальному поведению Launchpad X, выберите в Ableton Live:

```text
Control Surface:
Launchpad X
```

Удалять Launchpad X Performance для этого не требуется.

### 🇬🇧

To return to the original Launchpad X behavior, select:

```text
Control Surface:
Launchpad X
```

There is no need to uninstall Launchpad X Performance.

---

## Удаление / Uninstallation

### macOS

```text
uninstall.command
```

### Windows

```text
uninstall_windows.bat
```

---

## Статус проекта / Project status

### 🇷🇺

Launchpad X Performance создавался для решения конкретных задач моего собственного рабочего процесса.

Проект считается функционально завершённым для моего использования.

Новые версии будут выпускаться при необходимости:

- исправления реальных ошибок;
- поддержки новых версий Ableton Live;
- практических улучшений, которые потребуются во время выступлений.

Постоянное добавление новых функций не является целью проекта.

### 🇬🇧

Launchpad X Performance was created to solve specific problems in my own live-performance workflow.

The project is considered feature-complete for my use.

Future releases will be made when required for:

- fixing real issues;
- supporting new Ableton Live versions;
- practical improvements needed during performance.

Continuously adding new features is not a goal of the project.

---

## Лицензия / License

### 🇷🇺

Проект распространяется по лицензии MIT.

Вы можете свободно использовать, изменять и адаптировать его под свои задачи.

### 🇬🇧

The project is released under the MIT License.

You are free to use, modify, and adapt it for your own needs.

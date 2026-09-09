# Launchpad X Performance

Performance-oriented Remote Script for **Novation Launchpad X** and **Ableton Live 12**, built for live looping and hands-on performance.

> Unofficial community project. Not affiliated with or endorsed by Ableton or Novation.

---

## 🇷🇺 О проекте

**Launchpad X Performance** сохраняет привычную логику штатного Launchpad X и добавляет функции, ориентированные на живой лайв-лупинг: квантованные переходы, фиксированную запись, последовательную запись двух частей, безопасное удаление клипов и расширенное управление сценами.

Скрипт не заменяет и не изменяет оригинальные файлы Launchpad X. Дополнительные функции работают только когда в Ableton Live выбран Control Surface `Launchpad_X_performance`. В любой момент можно вернуться к штатному `Launchpad X`.

## 🇬🇧 About

**Launchpad X Performance** preserves the familiar Launchpad X workflow while adding performance-focused tools for live looping: quantized transitions, fixed-length recording, sequential two-part recording, safe clip deletion, and extended scene control.

The script does not replace or modify the original Launchpad X files. The extra functionality is active only when `Launchpad_X_performance` is selected as the Control Surface in Ableton Live. You can switch back to the official `Launchpad X` script at any time.

---

## 🎥 Демонстрация / Demo

https://youtu.be/iwC-g0I7ADQ?si=ZVzq5mLxWfpZIt2y

---

# Возможности / Features

## Quantized Clip Stop

**🇷🇺** Повторное нажатие на играющий клип ставит его в очередь на остановку по **Global Quantization** Ableton Live. Пока остановка ожидает музыкальной границы, кнопка клипа показывает состояние очереди.

**🇬🇧** Pressing a playing clip a second time queues it for stopping according to Ableton Live's **Global Quantization**, with pending-state LED feedback.

![Quantized Clip Stop](docs/gifs/quantized_clip_stop.gif)

## Scene Launch & Scene Hold Stop

**🇷🇺** Короткое нажатие запускает сцену с поведением, близким к штатному Ableton Scene Launch. Запуск применяется ко **всем обычным дорожкам проекта**, а не только к восьми дорожкам внутри текущего Session Ring. Пустой Clip Slot со Stop Button останавливает предыдущий клип; если Stop Button удалён, предыдущий клип продолжает играть.

Удержание кнопки сцены ставит соответствующую сцену на остановку по **Global Quantization**. Обычный короткий Scene Launch при этом сохраняется.

**🇬🇧** A short press launches the scene across **all regular project tracks**, not only the eight tracks currently visible in the Session Ring. An empty Clip Slot with a Stop Button stops the previously playing clip; removing the Stop Button allows it to continue.

Holding a Scene Launch button queues the scene for stopping according to **Global Quantization**, while a short press keeps normal scene-launch behavior.

![Scene Hold Stop](docs/gifs/scene_hold_stop.gif)

## Fixed Length Recording

**🇷🇺** Перед записью можно выбрать фиксированную длину нового клипа от **1 до 16 тактов**. Выбранное значение сохраняется между переключениями режимов и используется при записи новых клипов.

**🇬🇧** Select a fixed recording length from **1 to 16 bars** before recording. The selected value is preserved between mode changes and is used for new clip recordings.

![Fixed Length Recording](docs/gifs/fixed_length_recording.gif)

## Sequential Record

**🇷🇺** В режиме **Solo** нажатие Clip Pad запускает последовательную запись двух частей на одной дорожке.

- Если исходный слот пуст: записывается первый клип выбранной Fixed Length, затем автоматически записывается следующий слот, после чего воспроизведение возвращается к первому клипу.
- Если исходный клип уже существует: он запускается с обычной квантованием, проигрывается один полный цикл, затем начинается запись следующего слота, после чего воспроизведение возвращается к исходному клипу.
- Запись всегда идёт в **следующую сцену той же дорожки**.
- Если следующего слота нет или он уже занят, последовательность безопасно отменяется.
- Solo и Arm используют одну общую настройку Fixed Length.

Это позволяет во время выступления быстро записать, например, лёгкую и тяжёлую версии партии, куплет и припев или две вариации одного инструмента, а затем свободно переключать сцены.

**🇬🇧** In **Solo mode**, pressing a Clip Pad starts a two-part sequential recording workflow on the same track.

- Empty source slot: record the first fixed-length clip, automatically record the next scene slot, then return playback to the first clip.
- Existing source clip: launch it with normal quantization, wait for one complete source loop, record the next scene slot, then return to the source clip.
- Recording always targets the **next scene on the same track**.
- If the destination does not exist or is already occupied, the sequence aborts safely.
- Solo and Arm share the same Fixed Length setting.

This is designed for quickly building two related performance sections — for example verse/chorus, light/heavy, or alternate instrument parts — without leaving the Launchpad workflow.

## Long Press Clip Delete

**🇷🇺** На вооружённой дорожке клип можно удалить удержанием его кнопки. Короткое нажатие сохраняет обычное поведение, поэтому риск случайного удаления материала во время выступления ниже.

**🇬🇧** On an armed track, a clip can be deleted by holding its pad. A short press keeps normal clip behavior, reducing the risk of accidental deletion during performance.

![Long Press Clip Delete](docs/gifs/long_press_delete.gif)

## Dynamic Track Mapping / Drum Mode

**🇷🇺** Кастомная логика Drum Mode отслеживает изменения структуры проекта. Добавление или удаление дорожек не должно оставлять Arm, clip controls, drum routing и LED/playhead привязанными к устаревшему индексу дорожки.

**🇬🇧** Custom Drum Mode track mapping follows changes to the Live Set. Adding or removing tracks keeps Arm, clip controls, drum routing, LEDs, and playhead state synchronized with the intended Live track instead of a stale track index.

---

# Управление / Controls

## Fixed Length

```text
Mixer
↓
Pan
↓
Fixed Length
```

Повторное нажатие `Pan` закрывает режим и возвращает Session View. Фейдеры Pan в этом режиме отключены, чтобы случайное касание не изменило микс.

Press `Pan` again to leave Fixed Length mode and return to Session View. Pan faders are disabled while this mode is active to avoid accidental mix changes.

## Sequential Record

```text
Mixer
↓
Solo
↓
Press a Clip Pad
```

Sequential Record использует ту же выбранную Fixed Length, что и обычная запись в Arm mode.

Sequential Record uses the same selected Fixed Length value as normal recording in Arm mode.

## Hold-time configuration

Время удержания для Scene Stop и Clip Delete можно изменить в:

The hold time for Scene Stop and Clip Delete can be changed in:

```text
src/Launchpad_X_performance/__init__.py
```

```python
SCENE_HOLD_SECONDS = 0.7
CLIP_DELETE_HOLD_SECONDS = 0.7
```

---

# Совместимость / Compatibility

| Platform | Status |
|---|---|
| Novation Launchpad X | ✅ |
| Ableton Live 12 | ✅ |
| macOS | ✅ |
| Windows 11 | ✅ |

Текущая development-версия протестирована вручную в Ableton Live 12.4.x. Основной рабочий тест выполняется на macOS; Windows также поддерживается установочными скриптами проекта.

The current development version has been manually tested with Ableton Live 12.4.x. The primary development/test environment is macOS; Windows is also supported by the project's installation scripts.

---

# Установка / Installation

## macOS

Запустите / Run:

```text
install.command
```

После установки полностью перезапустите Ableton Live.

Restart Ableton Live completely after installation.

## Windows

Запустите / Run:

```text
install_windows.bat
```

Установщик предложит стандартное расположение Ableton User Library или позволит указать другой путь.

The installer will offer the standard Ableton User Library location or allow you to enter another path.

После установки полностью перезапустите Ableton Live.

Restart Ableton Live completely after installation.

## Ableton Live setup

```text
Settings
→ Link, Tempo & MIDI

Control Surface:
Launchpad_X_performance

Input:
Launchpad X DAW In

Output:
Launchpad X DAW Out
```

Названия MIDI-портов могут немного отличаться в зависимости от операционной системы.

MIDI port names may vary slightly depending on the operating system.

## Возврат к штатному скрипту / Returning to the official script

Выберите / Select:

```text
Control Surface:
Launchpad X
```

Удалять Launchpad X Performance не требуется.

There is no need to uninstall Launchpad X Performance.

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

# Текущий статус / Current status

Ветка `feature/drum-pad-v2` содержит текущую протестированную performance-версию, включая Sequential Record, синхронизацию track mapping и обновлённое Scene Launch behavior. Перед публикацией релиза эта версия проходит ручную проверку в реальном Live Set.

The `feature/drum-pad-v2` branch contains the current tested performance build, including Sequential Record, dynamic track mapping synchronization, and updated Scene Launch behavior. The build is manually verified in a real Live Set before release.

## Recent changes

- Sequential fixed-length recording workflow.
- Shared Fixed Length setting between Arm and Solo workflows.
- Dynamic track mapping after adding/removing Live tracks.
- Scene Launch across all regular `song.tracks`, including tracks outside the visible Session Ring.
- Native-like empty-slot Stop Button semantics.
- Absolute scene indexing when the Session Ring is vertically offset.

---

# License

Проект распространяется по лицензии MIT.

The project is released under the MIT License.

You are free to use, modify, and adapt it for your own needs.

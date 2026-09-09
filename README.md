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

# Возможности / Features

## Quantized Clip Stop

**🇷🇺** Повторное нажатие на играющий клип ставит его в очередь на остановку по **Global Quantization** Ableton Live. Пока остановка ожидает музыкальной границы, кнопка клипа показывает состояние очереди.

**🇬🇧** Pressing a playing clip a second time queues it for stopping according to Ableton Live's **Global Quantization**, with pending-state LED feedback.

## Scene START/STOP

**🇷🇺** Нажатие Scene button управляет текущей сценой через **Global Quantization** Ableton Live. Если в сцене нет играющих клипов, нажатие ставит сцену на START. Если в сцене уже есть играющие клипы, нажатие ставит сцену на STOP. Повторное нажатие той же Scene button до границы квантования переключает pending действие между START и STOP.

Scene Launch применяется ко **всем обычным дорожкам проекта**, а не только к восьми дорожкам внутри текущего Session Ring. Пустой Clip Slot со Stop Button останавливает предыдущий клип; если Stop Button удалён, предыдущий клип продолжает играть.

**🇬🇧** Pressing a Scene button controls the current scene using Ableton Live's **Global Quantization**. If the scene has no playing clips, the press queues/starts Scene START. If the scene has playing clips, the press queues Scene STOP. Pressing the same Scene button again before the quantization boundary toggles the pending action between START and STOP.

Scene Launch applies across **all regular project tracks**, not only the eight tracks currently visible in the Session Ring. An empty Clip Slot with a Stop Button stops the previously playing clip; removing the Stop Button allows it to continue.

## Fixed Length Recording

**🇷🇺** Перед записью можно выбрать фиксированную длину нового клипа от **1 до 16 тактов**. Выбранное значение сохраняется между переключениями режимов и используется при записи новых клипов.

**🇬🇧** Select a fixed recording length from **1 to 16 bars** before recording. The selected value is preserved between mode changes and is used for new clip recordings.

## Sequential Record

**🇷🇺** В режиме **Solo** нажатие Clip Pad запускает последовательную запись двух частей на одной дорожке.

- Если исходный слот пуст: записывается первый клип выбранной Fixed Length, затем автоматически записывается следующий слот, после чего воспроизведение возвращается к первому клипу.
- Если исходный клип уже существует: он запускается с обычным квантованием, проигрывается один полный цикл, затем начинается запись следующего слота, после чего воспроизведение возвращается к исходному клипу.
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

## Dynamic Track Mapping / Drum Mode

**🇷🇺** Кастомная логика Drum Mode отслеживает изменения структуры проекта. Добавление или удаление дорожек не должно оставлять Arm, clip controls, drum routing и LED/playhead привязанными к устаревшему индексу дорожки.

**🇬🇧** Custom Drum Mode track mapping follows changes to the Live Set. Adding or removing tracks keeps Arm, clip controls, drum routing, LEDs, and playhead state synchronized with the intended Live track instead of a stale track index.

---

# Управление / Controls

## Fixed Length

```text
Mixer
↓
Arm
↓
Fixed Length selection
```

```text
Mixer
↓
Solo
↓
Fixed Length selection + Sequential Record
```

Arm и Solo используют одну общую настройку Fixed Length. В режиме `Arm` она применяется для обычной Fixed Length записи, а в режиме `Solo` та же выбранная длина используется вместе с Sequential Record. `Pan` не является режимом Fixed Length.

Arm and Solo use the same shared Fixed Length value. In `Arm` mode it is used for normal Fixed Length recording, while in `Solo` mode the same selection is used together with Sequential Record. `Pan` is not a Fixed Length mode.

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

Arm и Solo используют одну общую настройку Fixed Length: изменение длины в любом из этих режимов обновляет общее значение.

Arm and Solo share one Fixed Length setting: changing the length in either mode updates the same shared value.

## Hold-time configuration

Этот раздел относится только ко времени удержания для Clip Delete.

This section documents only the hold time for Clip Delete.

Время удержания для Clip Delete можно изменить в:

The hold time for Clip Delete can be changed in:

```text
src/Launchpad_X_performance/clip_delete.py
```

```python
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

Версия **v1.2.0** протестирована вручную в Ableton Live 12.4.x. Основной рабочий тест выполнялся на macOS; Windows также поддерживается установочными скриптами проекта.

Version **v1.2.0** has been manually tested with Ableton Live 12.4.x. The primary development/test environment is macOS; Windows is also supported by the project's installation scripts.

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

# v1.2.0

## 🇷🇺

Крупное обновление performance-логики Launchpad X Performance.

### Добавлено

- **Sequential Record** в режиме Solo: последовательная запись двух связанных частей на одной дорожке.
- Общая настройка Fixed Length для Arm и Solo workflows.
- Расширенная логика Scene Launch по всем обычным дорожкам Live Set, включая дорожки вне видимого Session Ring.
- Динамическая синхронизация track mapping при добавлении и удалении дорожек.

### Исправлено и улучшено

- Scene Launch теперь сохраняет семантику Stop Button в пустых слотах: Stop Button останавливает предыдущий клип, удалённый Stop Button позволяет ему продолжать играть.
- Используется абсолютный индекс сцены при вертикальном смещении Session Ring.
- Drum Mode сохраняет правильную привязку к Live Track после изменения структуры проекта.
- Scene buttons теперь используют press-based квантованную START/STOP state machine без отдельного hold-жеста для остановки сцены.
- Сохранены квантованные queued launch/stop, Long Press Clip Delete, Mixer side long-press stop и Drum Mode clear long-press.

## 🇬🇧

Major update to the Launchpad X Performance live-performance workflow.

### Added

- **Sequential Record** in Solo mode for recording two related sections on the same track.
- Shared Fixed Length setting between Arm and Solo workflows.
- Extended Scene Launch across all regular Live Set tracks, including tracks outside the visible Session Ring.
- Dynamic track-mapping synchronization when tracks are added or removed.

### Fixed and improved

- Scene Launch now preserves empty-slot Stop Button semantics: a Stop Button stops the previous clip, while a removed Stop Button allows it to continue.
- Absolute scene indexing is used when the Session Ring is vertically offset.
- Drum Mode stays attached to the correct Live Track after project structure changes.
- Scene buttons now use a press-based quantized START/STOP state machine with no separate hold gesture for scene stopping.
- Quantized queued launch/stop, Long Press Clip Delete, Mixer side long-press stop, and Drum Mode clear long-press remain preserved.

---

# License

Проект распространяется по лицензии MIT.

The project is released under the MIT License.

You are free to use, modify, and adapt it for your own needs.

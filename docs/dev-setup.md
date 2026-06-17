# Dev setup (Windows + Cursor + FR955)

## Connect IQ SDK

- SDK: `connectiq-sdk-win-9.1.0` в `%APPDATA%\Garmin\ConnectIQ\Sdks\`
- SDK Manager: `Downloads\connectiq-sdk-manager-windows\sdkmanager.exe`
- Устройство **fr955** скачано в `%APPDATA%\Garmin\ConnectIQ\Devices\fr955`

### Кириллица в пути пользователя

Java-инструменты Garmin не читают SDK из `C:\Users\Смирнов Николай\...`.

**Решение:**

1. `connect-iq\setup-sdk-path.bat` — монтирует SDK на **`X:\`**
2. `%APPDATA%\Garmin\ConnectIQ\current-sdk.cfg` содержит одну строку: `X:\`

Запускать bat после каждой перезагрузки Windows (или перед сборкой — task делает это сам).

## Cursor / Monkey C

- Расширение: **Garmin Monkey C** (в Cursor через VSIX, не из marketplace)
- `.vscode/settings.json`:
  - `monkeyC.developerKeyPath`: `connect-iq/developer_key.der` (**без** `${workspaceFolder}`!)
  - `monkeyC.jungleFiles`: `connect-iq/monkey.jungle`
- Ключ: `connect-iq/developer_key.der` (генерировали через OpenSSL)

### Выход сборки

Физически одна папка: **`connect-iq/bin/`**. В корне репозитория **`bin/`** — junction (ссылка) на неё, чтобы F5 и расширение Garmin по умолчанию писали туда же, куда скрипты.

Артефакт приложения: **`connect-iq/bin/SB_Toksovo.prg`** (тот же файл доступен как `bin/SB_Toksovo.prg`).  
Как сменить маршрут / имя приложения: **`docs/new-route-and-app.md`**.

После клонирования или если `bin/` пропала: `scripts\setup-build-link.bat` (или `build-and-run.bat` создаст ссылку сам).

### Сборка и отладка

**Рекомендуется (обходит ошибку Tasks «r is not iterable»):**

1. Открыть папку **SwimBuoy** в Cursor (не «Проект Рогейн»).
2. Терминал:
   ```bat
   scripts\build-and-run.bat
   ```
   Или **Ctrl+Shift+B** — одна задача «SwimBuoy: Build and Run».

**Альтернатива — расширение Monkey C (без списка Tasks):**

- `Ctrl+Shift+P` → **Monkey C: Build Current Project**
- `F5` → **Run App (fr955)** (если launch.json срабатывает)

**Не использовать**, если падает с `r is not iterable`:

- `Tasks: Run Task` / «Выбрать задачу…» — баг Cursor/расширений при сборе всех task providers.

После перезагрузки Windows: `connect-iq\setup-sdk-path.bat` (или `build-and-run.bat` делает это сам).

## Симулятор: GPS

Пункта **Simulation → Position** нет. Нужно два шага:

1. **Settings → Set Position** — стартовые lat/lon (опционально)
2. **Simulation → Activity Data → ▶ Play** — без Play координаты не идут в приложение

Для реального трека:

- Activity Data → **Data Source: FIT/GPX Playable File** → Load → Play

## FIT с часов

- На FR955: Open Water Swim, GPS ready, **Activity Recording → Каждую секунду** (на тестовый заплыв)
- Garmin Connect → шестерёнка → **Экспортировать файл** = оригинальный **`.fit`**
- TCX/GPX — запасные форматы, для симулятора предпочтителен FIT

## Обновление маршрута

Редактировать **`connect-iq/resources/jsonData/lake_demo.buoy_route.json`**, затем пересобрать.

Формат-эталон: `routes/example.buoy_route.json` (в сборку не попадает — только черновик/документация).

Полная инструкция (новое место, OSM, отдельное имя на часах): **`docs/new-route-and-app.md`**.

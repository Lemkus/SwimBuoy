# Саммари сессии (контекст для продолжения)

Обновлено: 2026-06-02. Этот файл — выжимка длинного чата в Cursor (стартовали из «Проект Рогейн», код живёт здесь, в **SwimBuoy**).

**С чего начать в новом чате:** «Прочитай `docs/SESSION_SUMMARY.md` и `docs/status.md`, продолжаем SwimBuoy.»

---

## 1. Идея продукта

**SwimBuoy** — тренировки на открытой воде с **виртуальными буями** (без физических меток).

| Принцип | Смысл |
|--------|--------|
| Точки на озере | Фиксированные координаты с ID (P1, P2…) — запоминаешь **где** на воде |
| Порядок | Может меняться (`session.order`) — запоминать последовательность не обязательно |
| В заплыве | Плывёшь в основном **по памяти**, редко смотришь часы |
| На часах | Крупно **метры до текущей точки** + **стрелка** (bearing), не «отклонение от линии» |
| Следующая точка | Показывается после взятия текущей (радиус + dwell) |
| Bluetooth в воде | Не нужен в заплыве; GPS на часах — основной канал |

**Не путать:** навигация к **точке** (`point_proximity`), а не штраф за уход с polyline Garmin Course.

**Garmin Course (GPX `rte`)** — опционально для карты/импорта в Connect; **ядро MVP** — своё Connect IQ приложение + JSON с буями.

**Связь с «Проект Рогейн»:** оттуда теоретически можно переиспользовать Overpass/гео-утилиты для *автогенерации* точек позже. Сейчас MVP — **ручные/полевые координаты**, не тащить весь старый UI.

---

## 2. Что решили по Garmin FR955

- Целевое устройство: **Forerunner 955** (Connect IQ watch-app).
- Профиль **Open Water Swim** часто **без** встроенного меню Courses → навигация через **своё CIQ-приложение**, не только штатный курс.
- Публикация в магазине **не обязательна** на старте: sideload / beta / `monkeydo`.
- **Monkey C** пишет агент; пользователь **тестирует на воде** и в симуляторе.
- Вибрация по зонам дистанции — **backlog**, не MVP.
- **Connect IQ позже** может дать полную логику «буй → буй» (JSON на часах, `routeTo`, arrival); штатный Course координаты буев из CIQ **надёжно не читает**.

Подробный план (англ. артефакты, геймификация, миссии X-WATERS, ghost):  
`C:\Users\Смирнов Николай\.cursor\plans\garmin-mvp-bootstrap_66023642.plan.md`

---

## 3. Что уже сделано в репозитории

### Код Connect IQ (`connect-iq/`)

- Watch-app: **метры**, **стрелка**, **dwell** (4 с в радиусе 20 м).
- `RouteEngine.mc` — загрузка JSON, `fixed` / `random` / `shuffle_each_lap`.
- `SwimBuoyView.mc` — GPS poll 1 с, без Play в симуляторе будет «Waiting GPS».

### Данные маршрута

- **В сборке (вшито в .prg):** `connect-iq/resources/jsonData/lake_demo.buoy_route.json`
- **Эталон формата:** `routes/example.buoy_route.json`
- **Полевой круг ~890 m** (ходьба 24.05.2026): 5 точек P1–P5 из TCX, см. `routes/field_walk_2026-05-24.md`

### Инфраструктура Windows

- SDK: `%APPDATA%\Garmin\ConnectIQ\Sdks\connectiq-sdk-win-9.1.0-...`
- Кириллица в пути пользователя → `connect-iq/setup-sdk-path.bat` монтирует SDK на **`X:\`**
- `developer_key.der` локально (в git не коммитить)
- Скрипты: `scripts/build-and-run.bat`, `scripts/run-debug.ps1`, `scripts/analyze_tcx.py`

### Документация / память для AI

| Файл | Роль |
|------|------|
| `.cursorrules` | Краткие правила |
| `docs/decisions.md` | Продуктовые решения |
| `docs/dev-setup.md` | SDK, симулятор, сборка |
| `docs/status.md` | Чеклист сделано / дальше |
| **Этот файл** | Полный контекст чата |

**Memory Bank:** `memory-bank/` + slash-команды `/mb-*` (см. `docs/status.md`). Длинный handoff по-прежнему в `docs/`.

---

## 4. Полевой трек и точки (24.05.2026)

**Источник:** `Downloads\activity_22998898995 (1).tcx` (FR955, ~890 m, ~21 min).  
**Копия для симулятора:** `C:\Temp\field_walk.tcx`

Точки = **остановки** на треке (скорость &lt; 0.35 m/s, пауза ≥ 4 s):

| ID | Имя | lat | lon |
|----|-----|-----|-----|
| P1 | Старт | 60.1200133 | 30.2590315 |
| P2 | Буй 2 | 60.1201816 | 30.2550228 |
| P3 | Буй 3 | 60.1210397 | 30.2571027 |
| P4 | Буй 4 | 60.1199086 | 30.2577355 |
| P5 | Финиш | 60.1200667 | 30.2588867 |

Порядок в JSON: **P1 → P2 → P3 → P4 → P5** (`orderMode: fixed`).

---

## 5. Как собирать и отлаживать (важно)

### Открыть правильную папку

**File → Open Folder →** `C:\Users\Смирнов Николай\Desktop\SwimBuoy`  
(не «Проект Рогейн» — там нет `scripts\build-and-run.bat`).

### Сборка + симулятор (рекомендуется)

```powershell
cd "C:\Users\Смирнов Николай\Desktop\SwimBuoy"
.\scripts\build-and-run.bat
```

Или **Ctrl+Shift+B** (задача «SwimBuoy: Build and Run»).

После перезагрузки Windows bat сам вызывает `setup-sdk-path.bat` (диск `X:\`).

### В симуляторе (обязательно)

1. Открыть приложение **SwimBuoy** на виртуальных часах.
2. **Settings → Set Position** (опционально): lat `60.1200133`, lon `30.2590315`.
3. **Simulation → Activity Data** → FIT/GPX Playable File → Load `C:\Temp\field_walk.tcx` → **▶ Play**.  
   Без Play — «Waiting GPS», метры не меняются.

### Альтернатива

- `Ctrl+Shift+P` → **Monkey C: Build Current Project**
- **F5** → Run App (fr955)

### Не использовать (если падает)

- **Tasks: Run Task** — ошибка Cursor `r is not iterable` (баг task providers расширений, не проекта).

### PowerShell

Запуск bat только так: `.\scripts\build-and-run.bat` (с `.\` и из папки SwimBuoy).

---

## 6. Договорённости «по рукам»

- **Агент:** код, Connect IQ, JSON, инструкции, подготовка к публикации.
- **Ты:** SDK на ПК, FR955, тесты на воде/в симуляторе, обратная связь (цифры врут / стрелка ок / читаемость на гребке).
- **Первый вау:** стабильные метры + стрелка после одного просмотра карты точек; генератор/OSM/миссии — потом.

---

## 7. Следующие шаги (чеклист)

- [ ] Открыть папку **SwimBuoy** в Cursor.
- [ ] `.\scripts\build-and-run.bat` → симулятор FR955.
- [ ] SwimBuoy + Play `field_walk.tcx` → проверить переходы P1…P5, dwell, стрелку.
- [ ] Полевой заплыв → FIT с Connect (**«Экспортировать файл»**, запись GPS **каждую секунду**).
- [ ] При необходимости подправить координаты в `lake_demo.buoy_route.json` и пересобрать.
- [ ] Позже: телефонная карта точек, order modes в UI, ghost, миссии (см. plan.md).

---

## 8. Известные проблемы

| Проблема | Решение |
|----------|---------|
| `r is not iterable` в Tasks | `build-and-run.bat` или F5, не Run Task |
| `scripts\build-and-run.bat` — модуль scripts | Не та папка или нет `.\` в PowerShell |
| `X:\` не найден | `connect-iq\setup-sdk-path.bat` |
| Waiting GPS в app | Activity Data → **Play** |
| Java/SDK и кириллица в `Users\Смирнов Николай\` | SDK только через `X:\` |
| `monkeydo` долго висит | 1–2 мин норма; один симулятор, без диалогов |

---

## 9. Структура проекта (кратко)

```
SwimBuoy/
  connect-iq/          # Monkey C, manifest, jungle
    source/            # SwimBuoyView, RouteEngine, GeoUtils
    resources/jsonData/lake_demo.buoy_route.json  # ← править точки
    setup-sdk-path.bat
    developer_key.der  # локально
  routes/              # эталоны и описание полевого круга
  scripts/             # build-and-run.bat, analyze_tcx.py
  docs/                # decisions, dev-setup, status, этот файл
```

---

## 10. Backlog (из обсуждения, не в MVP)

- Геймификация: призрачный соперник, миссии (патруль, маяки, коридор), drill из X-WATERS.
- Режимы порядка: `nearest_next`, `blind_next` на часах.
- Вибро по дистанции до буя (опционально).
- FIT Course export для превью в Garmin Connect.
- Connect IQ: полная навигация буй→буй с синком JSON с телефона.
- Coros/Suunto, плавательные очки — вне MVP.

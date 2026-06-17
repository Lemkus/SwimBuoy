# Новый маршрут и отдельное приложение на часах

Инструкция: как добавить буи на новом водоёме и собрать watch-app с своим именем (например **SB_Toksovo**).  
Пример, по которому всё сделано: залив **Аунеланлахти**, озеро **Хепоярви**, Токсово (2026-06-07).

См. также: `routes/README.md`, `docs/dev-setup.md`, эталон формата `routes/example.buoy_route.json`.

---

## Два способа расставить буи

### A. Полевой обход (точнее всего)

Подходит, когда есть реальный трек с остановками у буёв.

1. Пройти/проплыть круг с остановками ≥4 с на каждой точке.
2. Экспорт **FIT** или **TCX** с часов.
3. Разобрать трек:
   ```bat
   python scripts\analyze_tcx.py путь\к\файлу.tcx
   ```
4. Координаты остановок → `points` в JSON (P1…P5).
5. Описание в `routes/<имя>.md`, архив JSON в `routes/<имя>.buoy_route.json`, GPX в `routes/<имя>_buoys.gpx` (см. `lake_demo_buoys.gpx`).

**Примеры в репозитории:** `field_walk_2026-05-24`, `tohkolodskoye_yukki`.

### B. По карте OSM (без полевого трека)

Подходит для первого черновика, когда известен залив/озеро на [OpenStreetMap](https://www.openstreetmap.org).

**Идея:** скачать полигон водоёма, проверить что все буи лежат **внутри** полигона, подобрать пятиугольник ~1 км.

**Шаги (как для Аунеланлахти):**

1. Найти озеро в Nominatim, например:
   ```text
   https://nominatim.openstreetmap.org/search?q=Hepojärvi&countrycodes=ru&format=json
   ```
   Для Хепоярви: relation **1445795**, bbox lat 60.154–60.184, lon 30.553–30.612.

2. Скачать геометрию relation (временный файл, в git не коммитить):
   ```bat
   curl.exe -s "https://www.openstreetmap.org/api/0.6/relation/1445795/full" -o scripts\_hepo.osm
   ```

3. Запустить скрипт расстановки:
   ```bat
   python scripts\_place_buoys_aunelan.py
   ```
   Создаётся `routes/toksovo_aunelanlahti.buoy_route.json`.

4. Проверить вывод скрипта:
   - периметр P1→…→P5→P1 близок к **~1000 m**;
   - все точки `in_lake=True` (внутри полигона).

5. При необходимости править в скрипте:
   - `center_lat`, `center_lon` — центр круга в нужном заливе;
   - `beach = (lat, lon)` — ориентир на берегу (P1 станет ближайшим к пляжу);
   - `TARGET_M` — целевая длина круга.

6. Дописать человекочитаемое описание: `routes/toksovo_aunelanlahti.md`.

**Ограничение:** OSM не размечает заливы по имени (Аунеланлахти нет отдельным полигоном) — берётся западная часть озера + ручной центр в заливе. После заплыва лучше уточнить координаты способом A.

---

## Формат JSON маршрута

В сборку попадает **один** файл:

`connect-iq/resources/jsonData/lake_demo.buoy_route.json`

Архивы маршрутов лежат в `routes/*.buoy_route.json`.

Обязательные поля:

| Поле | Значение MVP |
|------|----------------|
| `guidanceMode` | `point_proximity` |
| `arrivalRadiusM` | `20` |
| `dwellSec` | `4` |
| `session.orderMode` | `fixed` |
| `session.order` | `["P1","P2","P3","P4","P5"]` |

Каждая точка: `lat`, `lon`, `name` (Старт / Буй N / Финиш).

---

## Отдельное приложение с именем (SB_Toksovo)

Чтобы на часах было **другое имя** и приложение не конфликтовало со старым SwimBuoy, меняются три места:

### 1. Имя на экране часов

`connect-iq/resources/strings/strings.xml`:

```xml
<string id="AppName">SB_Toksovo</string>
```

### 2. Уникальный id приложения

`connect-iq/manifest.xml` — атрибут `id` у `<iq:application>`:

- **ровно 32 hex-символа** (0–9, a–f);
- при смене id Garmin считает это **новым** приложением (можно держать SwimBuoy и SB_Toksovo одновременно).

Пример id для SB_Toksovo: `c8f1a3b25e7d4096a1c2d3e4f5b6a7c8`.

### 3. Имя файла сборки

`scripts/build-and-run.bat` — параметр `-o` и копия в `C:\Temp\`:

```bat
-o connect-iq\bin\SB_Toksovo.prg
copy /Y connect-iq\bin\SB_Toksovo.prg C:\Temp\SB_Toksovo.prg
monkeydo.bat C:\Temp\SB_Toksovo.prg fr955
```

Для другого водоёма: заменить `SB_Toksovo` на своё имя (например `SB_Yukki`) везде согласованно.

---

## Сборка и проверка

### Подставить маршрут в сборку

PowerShell из корня проекта:

```powershell
Copy-Item routes\toksovo_aunelanlahti.buoy_route.json connect-iq\resources\jsonData\lake_demo.buoy_route.json
.\scripts\build-and-run.bat
```

### Сборка

```bat
scripts\build-and-run.bat
```

Скрипт сам: монтирует SDK на `X:\`, собирает fr955, копирует `.prg` в `C:\Temp`, деплоит в симулятор.

Артефакт: `connect-iq/bin/SB_Toksovo.prg`.

### Симулятор

1. **Settings → Set Position** — координаты у первого буя (для Аунеланлахти: **60.159, 30.558**).
2. Запустить приложение **SB_Toksovo** на виртуальных FR955.
3. **Simulation → Activity Data → Play** — без Play GPS в приложение не идёт.

С реальным треком: Activity Data → FIT/GPX → Load → Play.

---

## Чеклист для нового места

- [ ] JSON в `routes/<место>.buoy_route.json`
- [ ] Описание в `routes/<место>.md` и GPX `routes/<место>_buoys.gpx`
- [ ] Строка в таблице `routes/README.md`
- [ ] Копия JSON → `connect-iq/resources/jsonData/lake_demo.buoy_route.json`
- [ ] (опционально) своё имя: `strings.xml`, `manifest.xml` id, `build-and-run.bat` → `*.prg`
- [ ] `scripts\build-and-run.bat` — BUILD SUCCESSFUL
- [ ] Симулятор: метры и стрелка на P1
- [ ] (позже) полевой FIT → уточнить координаты способом A

---

## Что сделано для SB_Toksovo (2026-06-07)

| Что | Файл |
|-----|------|
| Маршрут ~650 м, 5 буёв | `routes/toksovo_aunelanlahti.buoy_route.json` |
| GPX для карт | `routes/toksovo_aunelanlahti_buoys.gpx` |
| Описание точек | `routes/toksovo_aunelanlahti.md` |
| Скрипт OSM-расстановки | `scripts/_place_buoys_aunelan.py` |
| Маршрут в сборке | `connect-iq/resources/jsonData/lake_demo.buoy_route.json` |
| Имя приложения | `connect-iq/resources/strings/strings.xml` → `SB_Toksovo` |
| Отдельный app id | `connect-iq/manifest.xml` |
| Сборка | `scripts/build-and-run.bat` → `SB_Toksovo.prg` |

**Буи (круг ~655 m, P1 задан вручную у входа в залив):**

| ID | lat | lon |
|----|-----|-----|
| P1 | 60.15627 | 30.55362 |
| P2 | 60.15507 | 30.55642 |
| P3 | 60.15427 | 30.55642 |
| P4 | 60.15497 | 30.55642 |
| P5 | 60.15627 | 30.55612 |

---

## Вернуть общее имя SwimBuoy

1. `strings.xml` → `SwimBuoy`
2. `manifest.xml` → старый id `b4e7c2a19f3d4e6b8c0d1e2f3a4b5c6d` (или свой)
3. `build-and-run.bat` → `SwimBuoy.prg`
4. Подставить нужный JSON из `routes/` и пересобрать.

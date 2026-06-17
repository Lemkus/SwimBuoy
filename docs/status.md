# Статус проекта (handoff)

Обновлено: 2026-06-08

## Где «память» проекта

| Файл / папка | Зачем |
|--------------|--------|
| **`memory-bank/`** | **Активные задачи** — tasks, progress, archive (slash-команды `/mb-*`) |
| **`docs/SESSION_SUMMARY.md`** | **Полный контекст чата** — идея, Garmin, точки, отладка, чеклист |
| `.cursorrules` | Короткие правила для AI (продукт + техника) |
| `docs/decisions.md` | Продуктовые решения MVP |
| `docs/dev-setup.md` | Среда разработки, симулятор, FIT |
| `docs/new-route-and-app.md` | Новый маршрут, OSM, отдельное имя приложения |
| `docs/status.md` | Этот файл — что сделано и что дальше |

### Slash-команды Memory Bank

В чате Cursor наберите `/` и выберите:

| Команда | Назначение |
|---------|------------|
| `/mb-init` | Проверить / создать структуру `memory-bank/` |
| `/mb-task` | Новая или обновление активной задачи |
| `/mb-progress` | Записать прогресс сессии |
| `/mb-reflect` | Рефлексия по задаче |
| `/mb-archive` | Архив завершённой задачи |

Файлы команд: `.cursor/commands/mb-*.md`

## Сделано

- [x] Каркас Connect IQ watch-app для **FR955** (`connect-iq/`)
- [x] Маршрут из JSON (`lake_demo.buoy_route.json`)
- [x] Экран: метры + стрелка + dwell-счётчик
- [x] Логика `radius + dwell`, режимы порядка `fixed` / `random` / `shuffle_each_lap`
- [x] Сборка под fr955, симулятор: метры и стрелка работают с Activity Data
- [x] Обход кириллицы в пути Windows (диск `X:` + `setup-sdk-path.bat`)
- [x] Настройки Cursor/VS Code (Monkey C, tasks, launch)
- [x] Маршрут **Аунеланлахти** (Токсово) + приложение **SB_Toksovo** (`routes/toksovo_aunelanlahti.*`)
- [x] **ActivityRecording** Open Water Swim — приложение не должно закрываться при погружении (см. архив `water-activity-recording`)

## В процессе / следующий шаг

- [x] Полевой обход пешком → TCX `activity_22998898995` (~890 m)
- [x] Буи по остановкам на треке → `lake_demo.buoy_route.json` (P1–P5, см. `routes/field_walk_2026-05-24.md`)
- [x] Сборка `SB_Toksovo.prg`, деплой в симулятор
- [ ] Переустановить .prg на часы и проверить устойчивость в воде
- [ ] Прогон TCX/FIT по Аунеланлахти в симуляторе (Activity Data → Play)
- [ ] Полевой тест на воде с FR955 (уточнить буи по FIT)

## Ключевые файлы кода

```
connect-iq/source/SwimBuoyView.mc   — UI, GPS polling
connect-iq/source/RouteEngine.mc    — маршрут, dwell, смена точек
connect-iq/source/GeoUtils.mc       — distance, bearing
connect-iq/resources/jsonData/      — маршрут, вшит в .prg
routes/example.buoy_route.json      — эталон формата (не в сборке)
```

## Известные ограничения

- В сборке: Аунеланлахти ~1 km (OSM-черновик); полевой круг ~890 m — в `routes/field_walk_2026-05-24`
- `developer_key.der` локальный, в git не коммитится
- После перезагрузки Windows нужен `connect-iq\setup-sdk-path.bat` (диск `X:`)
- На воде: запускать **только SB_Toksovo**, не параллельно штатный Open Water Swim
- Полевая проверка фикса ActivityRecording ещё не пройдена

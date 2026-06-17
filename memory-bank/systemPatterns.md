# System Patterns — SwimBuoy

Обновлено: 2026-06-08

## Архитектура (MVP)

```
connect-iq/source/
  SwimBuoyView.mc   — UI, GPS polling (1 с)
  RouteEngine.mc    — JSON, dwell, смена точек, order modes
  GeoUtils.mc       — distance, bearing
connect-iq/resources/jsonData/
  lake_demo.buoy_route.json  — маршрут, вшит в .prg
```

## Логика засчитывания

- `distance < arrivalRadiusM` (дефолт 20 m)
- удержание `dwellSec` (дефолт 4 s) внутри радиуса

## Сборка и деплой

- `scripts/build-and-run.bat` или Ctrl+Shift+B
- Артефакт: `connect-iq/bin/SB_Toksovo.prg`
- Симулятор: Activity Data → Load TCX/FIT → **Play** (без Play — «Waiting GPS»)

## Ограничения инженерии

- Минимальный diff, без лишней архитектуры.
- Отдельный проект от «Проект Рогейн».
- `developer_key.der` локально, не в git.
